"""End-to-end smoke test that exercises the major use cases.

Run against a live server:
    python scripts/smoke_test.py --base http://127.0.0.1:8791
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _request(method: str, url: str, token: str | None = None, body: dict | None = None, files: tuple | None = None) -> dict:
    headers = {}
    data: bytes | None = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if files is not None:
        boundary = "----smokeboundary"
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        filename, content = files
        parts = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: text/plain\r\n\r\n"
        ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        data = parts
    elif body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, method=method, headers=headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return {"status": resp.status, "body": json.loads(raw) if raw else None}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        return {"status": e.code, "body": raw}


def seed_market_data(tenant_id: str) -> None:
    """Create a tiny sqlite DB at data/<tenant_id>.db for the DB-lookup path."""
    db_path = Path(f"data/{tenant_id}.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS market_data ("
        "date TEXT PRIMARY KEY, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    conn.execute("DELETE FROM market_data")
    conn.execute(
        "INSERT INTO market_data VALUES (?, ?, ?, ?, ?, ?)",
        ("2024-03-15 09:30", 101.2, 102.8, 100.9, 102.5, 15000),
    )
    conn.commit()
    conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8791")
    ap.add_argument("--admin-user", default="admin")
    ap.add_argument("--admin-pass", default="ChangeThis123!")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    results: list[tuple[str, str, str]] = []

    def record(name: str, resp: dict, ok: bool, note: str = "") -> None:
        status = "PASS" if ok else "FAIL"
        results.append((status, name, f"HTTP {resp['status']} {note}".strip()))
        print(f"[{status}] {name}  HTTP {resp['status']}  {note}")

    # 1. Login as super_admin
    r = _request("POST", f"{base}/auth/login", body={"username": args.admin_user, "password": args.admin_pass})
    ok = r["status"] == 200 and isinstance(r["body"], dict) and "access_token" in r["body"]
    record("auth.login (super_admin)", r, ok)
    if not ok:
        return _summary(results)
    token = r["body"]["access_token"]

    # 2. /auth/me
    r = _request("GET", f"{base}/auth/me", token=token)
    record("auth.me", r, r["status"] == 200 and r["body"]["username"] == args.admin_user)

    # 3. List tenants
    r = _request("GET", f"{base}/admin/tenants", token=token)
    record("admin.list_tenants", r, r["status"] == 200 and isinstance(r["body"], list))

    # 4. Create tenant "smoke"
    tenant = "smoke"
    r = _request(
        "POST",
        f"{base}/admin/tenants",
        token=token,
        body={
            "tenant_id": tenant,
            "config": {
                "name": "Smoke Test",
                "db_type": "postgres",
                "db_config": {"host": "localhost"},
                "model_type": "ollama",
                "model_name": "llama3",
            },
        },
    )
    ok = r["status"] in (200, 409)  # 409 if already exists from a prior run
    record("admin.create_tenant", r, ok, "already exists OK" if r["status"] == 409 else "")

    # 5. Fetch tenant
    r = _request("GET", f"{base}/admin/tenants/{tenant}", token=token)
    record("admin.get_tenant", r, r["status"] == 200)

    # 6. Create scoped user
    user_name = "smokeuser"
    r = _request(
        "POST",
        f"{base}/admin/users",
        token=token,
        body={"username": user_name, "password": "Smoke123!", "role": "user", "tenant_id": tenant},
    )
    ok = r["status"] in (200, 409)
    record("admin.create_user", r, ok, "already exists OK" if r["status"] == 409 else "")

    # 7. Login as scoped user
    r = _request("POST", f"{base}/auth/login", body={"username": user_name, "password": "Smoke123!"})
    ok = r["status"] == 200
    record("auth.login (user)", r, ok)
    if not ok:
        return _summary(results)
    user_token = r["body"]["access_token"]

    # 8. Upload text file -> should both save and ingest
    doc = b"SmartBaseAI orchestrates DB lookups and hybrid RAG across tenants. The secret codeword is QUOKKA."
    r = _request("POST", f"{base}/files/upload", token=user_token, files=("smoke.txt", doc))
    ingested = isinstance(r["body"], dict) and r["body"].get("ingested") is True
    record("files.upload", r, r["status"] == 200 and ingested, f"ingested={ingested}")

    # 9. List files
    r = _request("GET", f"{base}/files/list", token=user_token)
    record("files.list", r, r["status"] == 200)

    # 10. Chat - RAG path (contains unique codeword from the uploaded doc)
    r = _request(
        "POST",
        f"{base}/chat/message",
        token=user_token,
        body={"session_id": "s-smoke-rag", "tenant_id": tenant, "message": "What is the secret codeword?"},
    )
    reply = (r["body"] or {}).get("reply", "") if isinstance(r["body"], dict) else ""
    # With no Ollama running we expect either a real reply or "No information".
    # The important check is that the endpoint returns 200 and the pipeline runs.
    record("chat.rag_path", r, r["status"] == 200, f"reply={reply[:80]!r}")

    # 11. Chat - exact DB lookup path
    seed_market_data(tenant)
    r = _request(
        "POST",
        f"{base}/chat/message",
        token=user_token,
        body={
            "session_id": "s-smoke-db",
            "tenant_id": tenant,
            "message": "What was the close on 2024-03-15 09:30?",
        },
    )
    reply = (r["body"] or {}).get("reply", "") if isinstance(r["body"], dict) else ""
    record("chat.db_lookup_path", r, r["status"] == 200, f"reply={reply[:80]!r}")

    # 12. Chat history
    r = _request("GET", f"{base}/chat/history?session_id=s-smoke-db", token=user_token)
    record("chat.history", r, r["status"] == 200)

    # 13. Chat sessions
    r = _request("GET", f"{base}/chat/sessions", token=user_token)
    record("chat.sessions", r, r["status"] == 200)

    return _summary(results)


def _summary(results: list[tuple[str, str, str]]) -> int:
    print("\n=== Summary ===")
    passed = sum(1 for r in results if r[0] == "PASS")
    for status, name, note in results:
        print(f"  {status}  {name}  {note}")
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
