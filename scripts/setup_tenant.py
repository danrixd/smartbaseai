#!/usr/bin/env python3
"""Register a new tenant configuration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on the path when executed directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tenants.tenant_manager import TenantManager


def main() -> None:
    """Create a tenant with database configuration."""
    parser = argparse.ArgumentParser(description="Create a tenant")
    parser.add_argument("tenant_id", help="Unique tenant identifier")
    parser.add_argument("--name", help="Readable tenant name")
    parser.add_argument(
        "--db-type", default="postgres", help="Database backend type"
    )
    parser.add_argument(
        "--db-config",
        default="{}",
        help="JSON string containing DB connector configuration",
    )
    args = parser.parse_args()

    manager = TenantManager()
    try:
        db_config = json.loads(args.db_config)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON for --db-config: {exc}")

    config = {
        "name": args.name or args.tenant_id,
        "db_type": args.db_type,
        "db_config": db_config,
    }
    manager.create(args.tenant_id, config)
    print(f"Tenant '{args.tenant_id}' created")


if __name__ == "__main__":
    main()
