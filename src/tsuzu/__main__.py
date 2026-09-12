from __future__ import annotations

import argparse

from .capability import CapabilityRegistry
from .claude_adapter import ClaudeHostAdapter, ClaudeMcpServer, serve_stdio, verify_claude_capability, verify_codex_capability
from .context import ContextBundleBuilder
from .index import IndexManager
from .retrieval import RetrievalService
from .vault import ActiveVaultLocator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tsuzu")
    subparsers = parser.add_subparsers(dest="command", required=True)
    mcp = subparsers.add_parser("mcp")
    mcp_subparsers = mcp.add_subparsers(dest="mcp_command", required=True)
    serve = mcp_subparsers.add_parser("serve")
    serve.add_argument("--host", choices=("claude-code", "codex"), required=True)
    serve.add_argument("--control-root", required=True)
    serve.add_argument("--index-root", required=True)
    serve.add_argument("--runtime-root", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    locator = ActiveVaultLocator(args.control_root)
    index = IndexManager(args.index_root, locator)
    index.open()
    try:
        registry = CapabilityRegistry()
        adapter_id, verifier = ("claude_code", verify_claude_capability) if args.host == "claude-code" else ("codex", verify_codex_capability)
        registry.publish(verifier())
        adapter = ClaudeHostAdapter(RetrievalService(index), ContextBundleBuilder(locator, args.runtime_root), registry, adapter_id=adapter_id)
        serve_stdio(ClaudeMcpServer(adapter))
    finally:
        index.close()


if __name__ == "__main__":
    main()
