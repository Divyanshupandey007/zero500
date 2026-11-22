# scripts/

Capture utilities used to generate the README screenshots (`README_assets/`). Both drive a headless Chrome instance over the Chrome DevTools Protocol.

## Prerequisites

Start the Angular dev server (`npm start` from `frontend/`) and launch Chrome with remote debugging enabled:

```bash
chrome --remote-debugging-port=9222 --remote-allow-origins=*
```

Then open `http://localhost:4200` in that Chrome instance so CDP has a page target to attach to.

## capture_screenshots.py

Captures screenshots of the dashboard workbench tabs (home, incident selected, telemetry logs, runbooks, remediation playbook) for `README_assets/`.

```bash
python capture_screenshots.py
# or with a custom output dir:
python capture_screenshots.py --out-dir /path/to/dir
ZERO500_OUT_DIR=/path/to/dir python capture_screenshots.py
```

Output dir defaults to `../README_assets` relative to this script; override with the `--out-dir` flag or `ZERO500_OUT_DIR` env var.

## capture_modals.py

Captures the Benchmark Scorecard modal for `README_assets/`.

```bash
python capture_modals.py
```

Same output-dir overrides as `capture_screenshots.py`.
