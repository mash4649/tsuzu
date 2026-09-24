from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .capability import CapabilityRegistry
from .claude_adapter import ClaudeHostAdapter, ClaudeMcpServer, serve_stdio, verify_claude_capability, verify_codex_capability, verify_cursor_capability
from .clip_digest import AppleNotesClipBridge, ChatGPTNotesAdapter, ClipDigestAdapter, SelectedNoteBridge, SelectedNoteLinkAdapter
from .context import ContextBundleBuilder
from .desktop_ingress import DesktopDraftIngress
from .historical_import import AppleNotesAdapter, HistoricalImporter
from .index import IndexCapabilityError, IndexManager
from .retrieval import RetrievalService
from .vault import ActiveVaultLocator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tsuzu")
    subparsers = parser.add_subparsers(dest="command", required=True)
    mcp = subparsers.add_parser("mcp")
    mcp_subparsers = mcp.add_subparsers(dest="mcp_command", required=True)
    serve = mcp_subparsers.add_parser("serve")
    serve.add_argument("--host", choices=("claude-code", "codex", "cursor", "chatgpt"), required=True)
    serve.add_argument("--control-root", required=True)
    serve.add_argument("--index-root", required=True)
    serve.add_argument("--runtime-root", required=True)
    desktop_ingress = subparsers.add_parser("desktop-ingress")
    desktop_ingress.add_argument("--app-local-root", required=True)
    desktop_ingress.add_argument("--queue-root", required=True)
    desktop_ingress.add_argument("--control-root", required=True)
    desktop_ingress.add_argument("--index-root", required=True)
    apple_notes = subparsers.add_parser("apple-notes-import")
    apple_notes.add_argument("--queue-root", required=True)
    apple_notes.add_argument("--control-root", required=True)
    apple_notes.add_argument("--index-root")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    locator = ActiveVaultLocator(args.control_root)
    if args.command == "apple-notes-import":
        try:
            index = IndexManager(args.index_root or locator.state_dir.parent / "index", locator)
            index.open()
            try:
                result = HistoricalImporter(args.queue_root, locator, index).import_items("APPLE_NOTES", AppleNotesAdapter().enumerate(), recent_n=1)
            finally:
                index.close()
        except (ValueError, IndexCapabilityError, OSError):
            print("ACTION_REQUIRED", file=sys.stderr)
            raise SystemExit(2)
        print(result.import_session_id, result.committed_count, result.already_imported_count, result.blocked_count, result.failed_count)
        return
    if args.command == "mcp" and args.host == "chatgpt":
        index = IndexManager(Path(args.index_root).expanduser(), locator)
        index.open()
        try:
            clips = ClipDigestAdapter(AppleNotesClipBridge(), locator)
            selected = SelectedNoteLinkAdapter(SelectedNoteBridge(), locator, Path(args.runtime_root).expanduser() / "queue", index)
            serve_stdio(ClaudeMcpServer(ChatGPTNotesAdapter(clips, selected)))
        finally:
            index.close()
        return
    index = IndexManager(args.index_root, locator)
    index.open()
    try:
        if args.command == "desktop-ingress":
            for result in DesktopDraftIngress(args.app_local_root, args.queue_root, locator, index).process_all():
                print(result.status, result.draft_id or "", result.source_id or "")
            return
        registry = CapabilityRegistry()
        adapter_id, verifier = {
            "claude-code": ("claude_code", verify_claude_capability),
            "codex": ("codex", verify_codex_capability),
            "cursor": ("cursor", verify_cursor_capability),
        }[args.host]
        registry.publish(verifier())
        adapter = ClaudeHostAdapter(RetrievalService(index), ContextBundleBuilder(locator, args.runtime_root), registry, adapter_id=adapter_id)
        serve_stdio(ClaudeMcpServer(adapter))
    finally:
        index.close()


if __name__ == "__main__":
    main()
