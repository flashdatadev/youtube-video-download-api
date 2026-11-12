# Contributing

Use Python 3.10+ and install the development dependencies:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m build
```

Keep HTTP authentication, request validation and signed-result handling in the official
FlashData SDK. Add regression tests for changes to checkpointing, recovery, URL handling
and exports. Tests must remain offline and must not need API keys or cloud credentials.

Examples should use placeholder API keys directly in Python. Never commit a filled-in
`examples/config.py`, checkpoint, signed upload URL or real customer's dataset.

For a bug report, include Python/OS versions, the example command, the error class and
a redacted minimal reproduction. Report account or billing issues through
[FlashData support](https://flashdata.dev/contact).
