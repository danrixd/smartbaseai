#!/usr/bin/env python3
"""Launch the SmartBase API server."""

from __future__ import annotations

import argparse

import uvicorn

from api.app import app


def main() -> None:
    """Parse CLI arguments and run the FastAPI application."""
    parser = argparse.ArgumentParser(description="Run SmartBase API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
