"""Capture screenshots of Zero500 frontend UI tabs via Chrome DevTools Protocol.

Drives a headless Chrome instance (already running with --remote-debugging-port=9222
and --remote-allow-origins=*) to capture screenshots of the dashboard's different
workbench tabs and modals for the README.
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
import websocket


DEBUG_PORT = 9222
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT_DIR = os.path.join(SCRIPTS_DIR, "..", "README_assets")


def log(msg):
    print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def find_page_ws():
    with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json/list", timeout=10) as r:
        targets = json.load(r)
    for t in targets:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No page target found")


class CDP:
    def __init__(self, url):
        self.ws = websocket.create_connection(url, timeout=30)
        self._id = 0

    def send(self, method, params=None):
        self._id += 1
        msg = {"id": self._id, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        while True:
            resp = json.loads(self.ws.recv())
            if resp.get("id") == self._id:
                if "error" in resp:
                    raise RuntimeError(f"CDP error {method}: {resp['error']}")
                return resp.get("result", {})

    def screenshot(self, path, quality=90):
        result = self.send("Page.captureScreenshot", {"format": "png", "quality": quality})
        data = base64.b64decode(result["data"])
        with open(path, "wb") as f:
            f.write(data)
        log(f"saved {path} ({len(data)} bytes)")

    def eval_click(self, selector, desc=""):
        js = f"""
        (() => {{
          const el = document.querySelector({json.dumps(selector)});
          if (!el) return "NOT_FOUND: {selector}";
          el.click();
          return "CLICKED: {desc or selector}";
        }})()
        """
        res = self.send("Runtime.evaluate", {"expression": js, "returnByValue": True})
        log(res["result"]["value"])
        return res["result"]["value"]

    def eval_js(self, expr):
        res = self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        return res["result"]["value"]


def wait(secs):
    time.sleep(secs)


def main():
    parser = argparse.ArgumentParser(description="Capture Zero500 frontend screenshots via CDP.")
    parser.add_argument(
        "--out-dir",
        default=os.environ.get("ZERO500_OUT_DIR", DEFAULT_OUT_DIR),
        help="Directory to write screenshots into (default: ../README_assets, overridable via ZERO500_OUT_DIR)",
    )
    args = parser.parse_args()
    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    ws_url = find_page_ws()
    log("connecting to " + ws_url)
    cdp = CDP(ws_url)
    cdp.send("Page.enable")
    cdp.send("Runtime.enable")

    wait(3)

    # 1) Dashboard home (empty state - no incident selected)
    cdp.screenshot(f"{out_dir}/01_dashboard_home.png")

    # Check for incident cards in the sidebar
    incident_count = cdp.eval_js(
        "document.querySelectorAll('.incident-card').length"
    )
    log(f"incident cards present: {incident_count}")

    if incident_count and incident_count > 0:
        # 2) Select the first incident -> shows workspace + PLAYBOOK tab (default)
        cdp.eval_click(".incident-card", "select first incident")
        wait(3)
        cdp.screenshot(f"{out_dir}/02_incident_selected_playbook.png")

        # 3) Click Telemetry Log Explorer tab
        cdp.eval_click(".tab-btn", "Telemetry Log Explorer tab")
        # target the LOGS tab specifically (second tab-btn)
        cdp.eval_js("""
        (() => {
          const tabs = Array.from(document.querySelectorAll('.tab-btn'));
          const logs = tabs.find(t => t.innerText.includes('Telemetry Log Explorer'));
          if (logs) { logs.click(); return 'clicked LOGS'; }
          return 'LOGS tab not found';
        })()
        """)
        wait(2)
        cdp.screenshot(f"{out_dir}/03_telemetry_log_explorer.png")

        # 4) Click Runbooks & Knowledge tab
        cdp.eval_js("""
        (() => {
          const tabs = Array.from(document.querySelectorAll('.tab-btn'));
          const rb = tabs.find(t => t.innerText.includes('Runbooks & Knowledge'));
          if (rb) { rb.click(); return 'clicked RUNBOOKS'; }
          return 'RUNBOOKS tab not found';
        })()
        """)
        wait(2)
        cdp.screenshot(f"{out_dir}/04_runbooks_knowledge.png")

        # 5) Back to Playbook
        cdp.eval_js("""
        (() => {
          const tabs = Array.from(document.querySelectorAll('.tab-btn'));
          const pb = tabs.find(t => t.innerText.includes('Remediation Playbook'));
          if (pb) { pb.click(); return 'clicked PLAYBOOK'; }
          return 'PLAYBOOK tab not found';
        })()
        """)
        wait(2)
        cdp.screenshot(f"{out_dir}/05_remediation_playbook.png")
    else:
        log("No incidents found; skipping tab screenshots.")

    log("Done.")


if __name__ == "__main__":
    main()
