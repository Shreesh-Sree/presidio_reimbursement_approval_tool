"""Local entry point for the policy assistant service."""

from __future__ import annotations

import os

import uvicorn

from .api import create_app


def main() -> None:
    uvicorn.run(
        create_app(),
        host=os.getenv("POLICY_ASSISTANT_HOST", "127.0.0.1"),
        port=int(os.getenv("POLICY_ASSISTANT_PORT", "8012")),
    )


if __name__ == "__main__":
    main()
