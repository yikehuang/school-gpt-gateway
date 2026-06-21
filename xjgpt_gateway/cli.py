"""Command-line entry point for the XJGPT gateway."""

from __future__ import annotations

import argparse

import uvicorn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the XJGPT FastAPI gateway.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Default: 127.0.0.1")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind. Default: 8000")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for local development.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    uvicorn.run("gateway:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
