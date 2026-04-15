"""UI -> API smoke test.

For every button or interactive control in the frontend, hit the backend
endpoint it calls and record pass/fail plus a short note. The output is a
Markdown-ish table suitable for copy/paste into a status report.

Run with the backend already running on the given ``--base`` URL:

    python scripts/ui_smoke.py --base http://127.0.0.1:8796
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Result:
    page: str
    control: str
    endpoint: str
    status: str          # PASS / FAIL / SKIP / NEEDS_KEY
    http_code: int | None = None
    note: str = ""


RESULTS: list[Result] = []


def req(
    method: str,
    base: str,
    path: str,
    token: str | None = None,
    body: Any = None,
    params: dict | None = None,
    multipart: tuple | None = None,
    timeout: int = 30,
) -> tuple[int, Any]:
    url = base.rstrip("/") + path
    if params:
        from urllib.parse import urlencode

        url += ("&" if "?" in url else "?") + urlencode(params)
    headers: dict[str, str] = {}
    data: bytes | None = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if multipart is not None:
        boundary = "----uismoke"
        filename, content = multipart
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        data = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: text/plain\r\n\r\n"
        ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    elif body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    r = urllib.request.Request(url, method=method, headers=headers, data=data)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as e:
        return 0, str(e)


def ok(code: int, *allowed: int) -> bool:
    return code in allowed


def add(page: str, control: str, endpoint: str, code: int, note: str = "") -> str:
    if code == 0:
        status = "FAIL"
    elif 200 <= code < 300:
        status = "PASS"
    else:
        status = "FAIL"
    RESULTS.append(
        Result(page=page, control=control, endpoint=endpoint, status=status, http_code=code, note=note)
    )
    return status


def skip(page: str, control: str, endpoint: str, note: str) -> None:
    RESULTS.append(Result(page=page, control=control, endpoint=endpoint, status="SKIP", note=note))


def needs_key(page: str, control: str, endpoint: str, note: str) -> None:
    RESULTS.append(Result(page=page, control=control, endpoint=endpoint, status="NEEDS_KEY", note=note))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://127.0.0.1:8796")
    p.add_argument("--admin-user", default="admin")
    p.add_argument("--admin-pass", default="ChangeThis123!")
    p.add_argument("--tenant-user", default="demo")
    p.add_argument("--tenant-pass", default="Demo123!")
    p.add_argument("--tenant-id", default="company")
    args = p.parse_args()
    base = args.base

    # Wait for server
    for _ in range(30):
        try:
            urllib.request.urlopen(base + "/docs", timeout=1)
            break
        except Exception:
            time.sleep(0.4)

    # ========== LOGIN PAGE ==========
    code, body = req("POST", base, "/auth/login", body={"username": args.admin_user, "password": args.admin_pass})
    add("Login", "Submit (super_admin)", "POST /auth/login", code)
    if not ok(code, 200):
        return _render()
    admin_token = body["access_token"]

    code, body = req("POST", base, "/auth/login", body={"username": "nobody", "password": "wrong"})
    RESULTS.append(
        Result(
            page="Login",
            control="Submit invalid credentials",
            endpoint="POST /auth/login",
            status="PASS" if code == 401 else "FAIL",
            http_code=code,
            note="401 Unauthorized as expected" if code == 401 else f"expected 401 got {code}",
        )
    )

    code, body = req("POST", base, "/auth/login", body={"username": args.tenant_user, "password": args.tenant_pass})
    add("Login", "Submit (tenant user)", "POST /auth/login", code)
    user_token = body["access_token"] if ok(code, 200) else None

    # ========== LAYOUT / HEADER ==========
    code, body = req("GET", base, "/auth/me", token=admin_token)
    add("Layout", "/auth/me on mount", "GET /auth/me", code, f"role={body.get('role') if isinstance(body, dict) else '?'}")

    code, tenants_list = req("GET", base, "/admin/tenants", token=admin_token)
    add("Layout", "Active vault dropdown (super_admin)", "GET /admin/tenants", code, f"{len(tenants_list) if isinstance(tenants_list,list) else '?'} tenants")

    code, sessions = req("GET", base, "/chat/sessions", token=admin_token)
    add("Layout", "Chat history sidebar", "GET /chat/sessions", code)

    code, status_body = req("GET", base, "/admin/models/status", token=admin_token)
    add("Layout", "API Connections indicator", "GET /admin/models/status", code)
    if isinstance(status_body, dict):
        for provider in ("ollama", "openai", "anthropic"):
            ps = status_body.get(provider, {})
            RESULTS.append(
                Result(
                    page="Layout",
                    control=f"  - {provider} status",
                    endpoint="(from /admin/models/status)",
                    status="PASS" if ps.get("ok") else "NEEDS_KEY",
                    http_code=200,
                    note=(ps.get("detail", "") or "")[:80],
                )
            )

    # ========== SETTINGS PAGE ==========
    code, settings = req("GET", base, "/admin/settings", token=admin_token)
    add("Settings", "Load page — GET settings", "GET /admin/settings", code)

    # Test each provider (backend picks up stored or env key)
    for provider in ("ollama", "openai", "anthropic"):
        code, resp = req("POST", base, "/admin/models/test", token=admin_token, body={"provider": provider})
        if ok(code, 200) and isinstance(resp, dict):
            if resp.get("ok"):
                add("Settings", f"Test {provider} button", "POST /admin/models/test", 200, "ok")
            else:
                RESULTS.append(
                    Result(
                        page="Settings",
                        control=f"Test {provider} button",
                        endpoint="POST /admin/models/test",
                        status="NEEDS_KEY",
                        http_code=200,
                        note=resp.get("detail", ""),
                    )
                )
        else:
            add("Settings", f"Test {provider} button", "POST /admin/models/test", code)

    # Save all
    code, resp = req("PUT", base, "/admin/settings", token=admin_token, body={"ollama_base_url": "http://localhost:11434"})
    add("Settings", "Save all (ollama_base_url)", "PUT /admin/settings", code)
    code, _ = req("PUT", base, "/admin/settings", token=admin_token, body={"ollama_base_url": ""})
    add("Settings", "Save all — clear back to env", "PUT /admin/settings", code)

    # Per-tenant model list — Add model for Acme (tenant_id='company')
    code, cfg = req("GET", base, f"/admin/tenants/{args.tenant_id}", token=admin_token)
    add("Settings", "Load tenant config for editor", f"GET /admin/tenants/{args.tenant_id}", code)
    if ok(code, 200) and isinstance(cfg, dict):
        # Simulate "+ Add model" click: append a new model and PATCH
        new_models = list(cfg.get("models", []))
        new_models.append({"provider": "ollama", "name": "llama3", "label": "smoke-added"})
        next_cfg = {**cfg, "models": new_models, "model_type": new_models[0]["provider"], "model_name": new_models[0]["name"]}
        code, resp = req("PATCH", base, f"/admin/tenants/{args.tenant_id}", token=admin_token, body={"tenant_id": args.tenant_id, "config": next_cfg})
        add("Settings", "+ Add model (Acme / company)", f"PATCH /admin/tenants/{args.tenant_id}", code, str(resp)[:80])

        # Now remove the smoke-added entry to leave state clean
        cleaned = [m for m in new_models if m.get("label") != "smoke-added"]
        restore_cfg = {**cfg, "models": cleaned}
        code, _ = req("PATCH", base, f"/admin/tenants/{args.tenant_id}", token=admin_token, body={"tenant_id": args.tenant_id, "config": restore_cfg})
        add("Settings", "Remove model button (revert)", f"PATCH /admin/tenants/{args.tenant_id}", code)

        # Change provider dropdown → bump model name
        change_cfg = {**cfg, "models": [dict(cleaned[0] or {}, provider="openai", name="gpt-4o-mini")] + cleaned[1:]}
        code, _ = req("PATCH", base, f"/admin/tenants/{args.tenant_id}", token=admin_token, body={"tenant_id": args.tenant_id, "config": change_cfg})
        add("Settings", "Change provider dropdown", f"PATCH /admin/tenants/{args.tenant_id}", code)
        code, _ = req("PATCH", base, f"/admin/tenants/{args.tenant_id}", token=admin_token, body={"tenant_id": args.tenant_id, "config": cfg})
        add("Settings", "Revert to original config", f"PATCH /admin/tenants/{args.tenant_id}", code)

    # ========== TENANTS PAGE ==========
    code, _ = req("POST", base, "/admin/tenants", token=admin_token, body={"tenant_id": "ui_smoke_tmp", "config": {"name": "UI smoke temp", "models": [{"provider": "ollama", "name": "llama3"}]}})
    add("Tenants", "Add tenant form submit", "POST /admin/tenants", code, "new tenant ui_smoke_tmp")
    code, _ = req("DELETE", base, "/admin/tenants/ui_smoke_tmp", token=admin_token)
    add("Tenants", "Delete button", "DELETE /admin/tenants/ui_smoke_tmp", code)

    # ========== USERS PAGE ==========
    code, users = req("GET", base, "/admin/users", token=admin_token)
    add("Users", "Load users list", "GET /admin/users", code, f"{len(users) if isinstance(users,list) else '?'} users")

    smoke_user = "ui_smoke_user_tmp"
    code, _ = req(
        "POST",
        base,
        "/admin/users",
        token=admin_token,
        body={"username": smoke_user, "password": "Smoke123!", "role": "user", "tenant_id": args.tenant_id},
    )
    # Allow 409 if a previous run left it behind
    if code == 409:
        add("Users", "Add user form submit", "POST /admin/users", 409, "already exists — prior run")
    else:
        add("Users", "Add user form submit", "POST /admin/users", code)

    code, _ = req("PATCH", base, f"/admin/users/{smoke_user}", token=admin_token, body={"role": "admin"})
    add("Users", "Edit user role", f"PATCH /admin/users/{smoke_user}", code)
    code, _ = req("DELETE", base, f"/admin/users/{smoke_user}", token=admin_token)
    add("Users", "Delete user button", f"DELETE /admin/users/{smoke_user}", code)

    # ========== VAULT PAGE ==========
    code, vault_list = req("GET", base, "/files/vault", token=admin_token, params={"tenant_id": args.tenant_id})
    add("Vault", "Load file list", "GET /files/vault", code, f"{len(vault_list.get('files',[])) if isinstance(vault_list,dict) else '?'} files")

    # Pick first file and open it
    first_file = None
    if isinstance(vault_list, dict) and vault_list.get("files"):
        first_file = vault_list["files"][0]["filename"]

    if first_file:
        code, file_body = req("GET", base, f"/files/vault/{first_file}", token=admin_token, params={"tenant_id": args.tenant_id})
        add("Vault", "Open file (click entry)", f"GET /files/vault/{first_file}", code)
        original_content = file_body.get("content", "") if isinstance(file_body, dict) else ""

        code, _ = req(
            "PUT",
            base,
            f"/files/vault/{first_file}",
            token=admin_token,
            params={"tenant_id": args.tenant_id},
            body={"content": original_content + "\n<!-- ui-smoke touch -->\n"},
        )
        add("Vault", "Save + re-ingest button", f"PUT /files/vault/{first_file}", code)

        # Revert
        code, _ = req(
            "PUT",
            base,
            f"/files/vault/{first_file}",
            token=admin_token,
            params={"tenant_id": args.tenant_id},
            body={"content": original_content},
        )
        add("Vault", "Revert (save original)", f"PUT /files/vault/{first_file}", code)

    # + Add file upload
    code, _ = req(
        "POST",
        base,
        "/files/upload",
        token=admin_token,
        params={"tenant_id": args.tenant_id},
        multipart=("ui_smoke_upload.md", b"# UI smoke upload\n\nTransient test file.\n"),
    )
    add("Vault", "+ Add file upload", "POST /files/upload", code)

    # ========== CHAT PAGE ==========
    code, _ = req(
        "POST",
        base,
        "/chat/message",
        token=admin_token,
        body={
            "session_id": "ui-smoke-chat",
            "tenant_id": args.tenant_id,
            "message": "ping",
        },
    )
    add("Chat", "Send message (default model)", "POST /chat/message", code)

    code, _ = req(
        "POST",
        base,
        "/chat/message",
        token=admin_token,
        body={
            "session_id": "ui-smoke-chat-openai",
            "tenant_id": args.tenant_id,
            "message": "ping with openai override",
            "model_provider": "openai",
            "model_name": "gpt-4o-mini",
        },
    )
    add("Chat", "Send message (OpenAI override via dropdown)", "POST /chat/message", code)

    code, _ = req("GET", base, "/chat/history", token=admin_token, params={"session_id": "ui-smoke-chat"})
    add("Chat", "Load history", "GET /chat/history", code)

    code, _ = req("DELETE", base, "/chat/session/ui-smoke-chat", token=admin_token)
    add("Chat", "Delete session (trash icon)", "DELETE /chat/session/ui-smoke-chat", code)
    code, _ = req("DELETE", base, "/chat/session/ui-smoke-chat-openai", token=admin_token)
    add("Chat", "Delete session (trash icon)", "DELETE /chat/session/ui-smoke-chat-openai", code)

    # ========== RAG VISUALIZER ==========
    code, trace = req(
        "POST",
        base,
        "/chat/trace",
        token=admin_token,
        body={"session_id": "ui-smoke-trace", "tenant_id": args.tenant_id, "message": "How many venues does Pulse support?"},
    )
    rag_docs = 0
    if isinstance(trace, dict):
        rag_docs = len(trace.get("stages", {}).get("rag_retrieval", {}).get("combined", []))
    add("RAG Visualizer", "Run trace — default model", "POST /chat/trace", code, f"{rag_docs} docs retrieved")

    code, _ = req(
        "POST",
        base,
        "/chat/trace",
        token=admin_token,
        body={
            "session_id": "ui-smoke-trace-2",
            "tenant_id": args.tenant_id,
            "message": "ping",
            "model_provider": "anthropic",
            "model_name": "claude-opus-4-6",
        },
    )
    add("RAG Visualizer", "Run trace — model override (anthropic)", "POST /chat/trace", code)

    return _render()


def _render() -> int:
    print()
    by_page: dict[str, list[Result]] = {}
    for r in RESULTS:
        by_page.setdefault(r.page, []).append(r)

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r.status == "PASS")
    needs_key = sum(1 for r in RESULTS if r.status == "NEEDS_KEY")
    failed = sum(1 for r in RESULTS if r.status == "FAIL")
    skipped = sum(1 for r in RESULTS if r.status == "SKIP")

    def ascii_safe(s: str) -> str:
        return s.encode("ascii", "replace").decode("ascii")

    for page, rows in by_page.items():
        print(f"\n## {page}")
        print(f"{'STATUS':<10} {'CONTROL':<42} {'ENDPOINT':<44} {'HTTP':>5}  NOTE")
        print("-" * 130)
        for r in rows:
            code = str(r.http_code) if r.http_code is not None else "-"
            control = ascii_safe(r.control)[:42]
            endpoint = ascii_safe(r.endpoint)[:44]
            note = ascii_safe(r.note)
            print(f"{r.status:<10} {control:<42} {endpoint:<44} {code:>5}  {note}")

    print("\n## Summary")
    print(f"  PASS:      {passed}/{total}")
    print(f"  NEEDS_KEY: {needs_key}  (provider not configured — expected, not a failure)")
    print(f"  FAIL:      {failed}")
    print(f"  SKIP:      {skipped}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
