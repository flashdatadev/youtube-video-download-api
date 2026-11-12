from __future__ import annotations

import argparse
import importlib
import math
import sys
from typing import Any

from flashdata import FlashData
from flashdata.errors import FlashDataError, PollingTimeoutError


def positive_timeout(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Timeout must be a positive number of seconds.") from None
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("Timeout must be a positive finite number of seconds.")
    return seconds


def settings() -> tuple[str, dict[str, Any]]:
    try:
        config = importlib.import_module("examples.config")
    except ModuleNotFoundError as exc:
        if exc.name != "examples.config":
            raise
        raise ValueError(
            "Copy examples/config.example.py to examples/config.py and fill it in."
        ) from None
    key = config.API_KEY
    if not isinstance(key, str) or not key.strip() or key == "your-flashdata-api-key":
        raise ValueError("Set API_KEY in examples/config.py to your FlashData API key.")
    return key, config.STORAGE


def client_and_storage() -> tuple[FlashData, dict[str, Any]]:
    api_key, storage = settings()
    return FlashData(api_key=api_key), storage


def run(main) -> None:
    try:
        main()
    except PollingTimeoutError as exc:
        print(f"{exc} Use examples.recover with the saved checkpoint.", file=sys.stderr)
        raise SystemExit(2) from None
    except (FlashDataError, OSError, ValueError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
