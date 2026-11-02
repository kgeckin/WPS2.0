"""Standalone local management CLI; no recipient messaging or remote scanning."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from . import __version__, storage, tokens
from .settings import data_directory, initialize_secret, secret_for


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wps", description="Local consent-based awareness lab")
    parser.add_argument("--version", action="version", version=f"wps-awareness-lab {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create a private local key and synthetic SQLite demo")
    serve = sub.add_parser("serve", help="Open a browser dashboard on loopback only")
    serve.add_argument("--port", type=int, default=5000)
    sub.add_parser("status", help="Show synthetic lab totals")
    link = sub.add_parser("link", help="Issue an expiring link for a consented demo alias")
    link.add_argument("--campaign", type=int, default=1)
    link.add_argument("--participant", type=int, default=1)
    link.add_argument("--port", type=int, default=5000)
    sub.add_parser("report", help="Write anonymized CSV to standard output")
    sub.add_parser("desktop", help="Launch optional local Tkinter dashboard")
    add_campaign = sub.add_parser("campaign-add", help="Create a local draft training scenario")
    add_campaign.add_argument("--name", required=True)
    state = sub.add_parser("campaign-state", help="Change a synthetic campaign state")
    state.add_argument("--campaign", required=True, type=int)
    state.add_argument("--state", required=True, choices=("draft", "active", "closed"))
    alias = sub.add_parser("alias-add", help="Add a fictional, non-contact TRAIN code")
    alias.add_argument("--campaign", required=True, type=int)
    alias.add_argument("--alias", required=True)
    alias.add_argument("--consent", action="store_true", help="Explicitly allow local practice for this code")
    consent = sub.add_parser("alias-consent", help="Grant or revoke a demo alias's consent")
    consent.add_argument("--campaign", required=True, type=int)
    consent.add_argument("--alias", required=True)
    choice = consent.add_mutually_exclusive_group(required=True)
    choice.add_argument("--grant", action="store_true")
    choice.add_argument("--revoke", action="store_true")
    args = parser.parse_args(argv)
    folder = data_directory()
    db_path = folder / "lab.sqlite3"

    try:
        if args.command == "init":
            initialize_secret(folder)
            storage.initialize(db_path)
            print("Local lab initialized with synthetic data. No real recipients are imported.")
            print("Private key stored in the ignored local data directory.")
            return 0
        secret = secret_for(folder)
        if not db_path.is_file():
            raise RuntimeError("Run 'python main.py init' before using the lab.")
        if args.command == "serve":
            if not 1024 <= args.port <= 65535:
                parser.error("Port must be between 1024 and 65535")
            from .app import create_app
            print(f"Local dashboard: http://127.0.0.1:{args.port}")
            print("This service has no remote login. It must remain on localhost.")
            create_app().run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)
        elif args.command == "status":
            totals = storage.overview(db_path)
            print("WPS / SYNTHETIC TRAINING LAB")
            for key, value in totals.items():
                print(f"{key}: {value}")
        elif args.command == "link":
            if not 1024 <= args.port <= 65535:
                parser.error("Port must be between 1024 and 65535")
            if not storage.eligible(db_path, args.campaign, args.participant):
                raise RuntimeError("Selected demo alias is not eligible for this active campaign.")
            token = tokens.create(secret, args.campaign, args.participant)
            print(f"http://127.0.0.1:{args.port}/practice/{token}")
            print("Local test only. Do not send links to real recipients.", file=sys.stderr)
        elif args.command == "report":
            sys.stdout.write(storage.export_csv(db_path))
        elif args.command == "desktop":
            from .desktop import run
            run(db_path)
        elif args.command == "campaign-add":
            new_id = storage.create_campaign(db_path, args.name)
            print(f"Created local draft campaign #{new_id}")
        elif args.command == "campaign-state":
            if not storage.change_campaign_state(db_path, args.campaign, args.state):
                raise RuntimeError("Unknown campaign")
            print(f"Campaign #{args.campaign}: {args.state}")
        elif args.command == "alias-add":
            alias_id = storage.create_alias(db_path, args.campaign, args.alias, consent=args.consent)
            print(f"Synthetic alias #{alias_id} added. Consented: {args.consent}")
        elif args.command == "alias-consent":
            if not storage.set_alias_consent(db_path, args.campaign, args.alias, consent=args.grant):
                raise RuntimeError("Synthetic alias not found")
            print(f"Consent {'granted' if args.grant else 'revoked'} for {args.alias}")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"WPS: {exc}", file=sys.stderr)
        return 1
    return 0
