"""Capture the Benchmark Scorecard and New Investigation modals via CDP."""
import base64
import json
import os
import time
import urllib.request
import websocket

DEBUG_PORT = 9222
OUT_DIR = "D:/Projects/zero500/README_assets"


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

    def eval_js(self, expr):
        res = self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        return res["result"]["value"]


def wait(secs):
    time.sleep(secs)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cdp = CDP(find_page_ws())
    cdp.send("Page.enable")
    cdp.send("Runtime.enable")
    wait(2)

    # Open Benchmark Scorecard modal
    cdp.eval_js("""
    (() => {
      const btn = Array.from(document.querySelectorAll('button')).find(
        b => b.innerText.includes('Benchmark Scorecard')
      );
      if (btn) { btn.click(); return 'opened eval modal'; }
      return 'eval btn not found';
    })()
    """)
    wait(2)
    cdp.screenshot(f"{OUT_DIR}/06_eval_scorecard_modal.png")

    log("Done.")


if __name__ == "__main__":
    main()
