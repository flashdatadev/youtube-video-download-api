# Examples and maintenance

- Keep this repository Python-only and build on the official `flashdata` SDK.
- In Python examples, pass placeholder API keys directly: `FlashData(api_key="your-flashdata-api-key")`. Environment variables are optional.
- Public API downloads deliver media into customer cloud storage. Result JSON describes that delivery.
- Save accepted job IDs before uploading or polling. Never automatically repeat a submission after a lost response.
- Keep storage credentials, API keys and signed upload descriptors out of checkpoints and committed files.
- Tests and CI must run offline. Do not submit billable requests during ordinary verification.
- Run `python -m pytest`, `python -m ruff check .`, `python -m ruff format --check .`, and `python -m build` after code changes.
