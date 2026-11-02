# Contributing

Thanks for helping improve clipscribe-local. This project is local-first: do not submit client footage, secrets, or personal data.

Before opening a change:

1. Keep changes focused and explain the user-facing behavior.
2. Add or update tests for behavior changes.
3. For benchmark changes, record the exact model, settings, hardware, and command; never estimate results.
4. Confirm that any media or reference transcript you contribute is legally redistributable.

## Development

Use Python 3.11–3.14, FFmpeg, and Node.js 24. See the README for first-time setup and the Windows launcher. From the repository root, run:

```powershell
python -m pip install -e ".[dev]"
python -m pytest
ruff check .
mypy src
```

Build the browser app from `frontend/` with `npm ci` and `npm run build`. Docker Compose is also available for a local deployment.
