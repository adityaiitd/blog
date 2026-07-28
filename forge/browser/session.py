"""Headful Chrome driven over the DevTools Protocol.

Several of the sources this project depends on reject plain HTTP clients while
serving an ordinary browser. That is a reason to use a browser, not a reason to
defeat a security control: when a managed challenge or CAPTCHA appears, the
session reports it and stops. See :mod:`forge.browser.manual_gate`.

Chrome ignores ``--remote-debugging-port`` for the default profile as of
Chrome 136, so a dedicated ``--user-data-dir`` is mandatory rather than
merely tidy.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_PORT = 9222
CHALLENGE_TEXT = (
    "just a moment",
    "checking your browser",
    "verify you are human",
    "enable javascript and cookies",
    "attention required",
    "cf-challenge",
    "captcha",
)


class BrowserError(RuntimeError):
    pass


def _free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if probe.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@dataclass
class PageResult:
    url: str
    final_url: str
    status: int
    html: str
    title: str
    challenged: bool
    screenshot_png: Optional[bytes] = None

    @property
    def looks_like_content(self) -> bool:
        return self.status == 200 and not self.challenged and len(self.html) > 2000


class ChromeSession:
    """A managed headful Chrome instance with its own profile and CDP port."""

    def __init__(
        self,
        user_data_dir: Optional[Path] = None,
        port: int = DEFAULT_PORT,
        headless: bool = False,
        display: Optional[str] = None,
        binary: Optional[str] = None,
        download_dir: Optional[Path] = None,
    ):
        self.binary = binary or shutil.which("google-chrome") or shutil.which(
            "google-chrome-stable"
        )
        if not self.binary:
            raise BrowserError("google-chrome is not installed")
        self._owns_profile = user_data_dir is None
        self.user_data_dir = Path(
            user_data_dir or tempfile.mkdtemp(prefix="forge-chrome-")
        )
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.port = _free_port(port)
        self.headless = headless
        self.display = display or os.environ.get("DISPLAY", "")
        self.download_dir = Path(download_dir) if download_dir else None
        if self.download_dir:
            self.download_dir.mkdir(parents=True, exist_ok=True)
        self._proc: Optional[subprocess.Popen] = None
        self._msg_id = 0

    # ------------------------------------------------------------- lifecycle

    def start(self, timeout: float = 45.0) -> "ChromeSession":
        args = [
            self.binary,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.user_data_dir}",
            # Chrome rejects DevTools websockets whose Origin it does not know.
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-features=Translate,MediaRouter",
            "--window-size=1600,1100",
            "about:blank",
        ]
        if self.headless:
            args.insert(1, "--headless=new")
        env = dict(os.environ)
        if self.display and not self.headless:
            env["DISPLAY"] = self.display
        self._proc = subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self._http_get("/json/version")
                return self
            except Exception:
                if self._proc.poll() is not None:
                    raise BrowserError(
                        f"Chrome exited immediately with code {self._proc.returncode}"
                    )
                time.sleep(0.4)
        raise BrowserError(f"Chrome did not open a CDP port within {timeout:g}s")

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        if self._owns_profile:
            shutil.rmtree(self.user_data_dir, ignore_errors=True)

    def __enter__(self) -> "ChromeSession":
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.stop()

    # ------------------------------------------------------------------ CDP

    def _http_get(self, path: str, timeout: float = 10.0) -> Any:
        url = f"http://127.0.0.1:{self.port}{path}"
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode())

    def version(self) -> Dict[str, Any]:
        return self._http_get("/json/version")

    def _open_tab(self) -> Dict[str, Any]:
        pages = [t for t in self._http_get("/json/list") if t.get("type") == "page"]
        if pages:
            return pages[0]
        return self._http_get("/json/new?about:blank")

    def fetch(
        self,
        url: str,
        wait_seconds: float = 6.0,
        screenshot: bool = False,
        timeout: float = 75.0,
    ) -> PageResult:
        """Navigate and return the rendered DOM.

        A managed challenge is detected and reported rather than worked around.
        """
        import websocket  # imported lazily so the module loads without it

        tab = self._open_tab()
        ws_url = tab["webSocketDebuggerUrl"]
        ws = websocket.create_connection(ws_url, timeout=timeout)
        try:
            status = 0
            final_url = url

            def send(method: str, params: Optional[Dict[str, Any]] = None) -> int:
                self._msg_id += 1
                ws.send(json.dumps(
                    {"id": self._msg_id, "method": method, "params": params or {}}
                ))
                return self._msg_id

            def wait_for(msg_id: int, limit: float) -> Dict[str, Any]:
                end = time.time() + limit
                while time.time() < end:
                    raw = json.loads(ws.recv())
                    if raw.get("id") == msg_id:
                        return raw
                    method = raw.get("method")
                    if method == "Network.responseReceived":
                        response = raw["params"]["response"]
                        if raw["params"].get("type") == "Document":
                            nonlocal status, final_url
                            status = response.get("status", 0)
                            final_url = response.get("url", final_url)
                raise BrowserError(f"timed out waiting for CDP message {msg_id}")

            send("Network.enable")
            send("Page.enable")
            if self.download_dir:
                send("Browser.setDownloadBehavior", {
                    "behavior": "allow",
                    "downloadPath": str(self.download_dir),
                })
            nav = send("Page.navigate", {"url": url})
            wait_for(nav, timeout)
            time.sleep(wait_seconds)

            doc = send("Runtime.evaluate", {
                "expression": "document.documentElement.outerHTML",
                "returnByValue": True,
            })
            html = wait_for(doc, timeout)["result"]["result"].get("value", "") or ""

            ttl = send("Runtime.evaluate", {
                "expression": "document.title", "returnByValue": True,
            })
            title = wait_for(ttl, timeout)["result"]["result"].get("value", "") or ""

            loc = send("Runtime.evaluate", {
                "expression": "location.href", "returnByValue": True,
            })
            href = wait_for(loc, timeout)["result"]["result"].get("value", "")
            if href:
                final_url = href

            shot: Optional[bytes] = None
            if screenshot:
                cap = send("Page.captureScreenshot", {"format": "png"})
                data = wait_for(cap, timeout)["result"].get("data", "")
                if data:
                    shot = base64.b64decode(data)

            haystack = f"{title}\n{html[:8000]}".lower()
            challenged = any(marker in haystack for marker in CHALLENGE_TEXT)

            return PageResult(
                url=url, final_url=final_url, status=status or 200, html=html,
                title=title, challenged=challenged, screenshot_png=shot,
            )
        finally:
            ws.close()

    def download(self, url: str, dest: Path, timeout: float = 180.0) -> Path:
        """Fetch a binary using the browser's cookie jar and TLS fingerprint."""
        import websocket

        tab = self._open_tab()
        ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=timeout)
        try:
            self._msg_id += 1
            expression = (
                "(async () => {"
                f"  const r = await fetch({json.dumps(url)}, "
                "     {credentials: 'include'});"
                "  const b = new Uint8Array(await r.arrayBuffer());"
                "  let s = '';"
                "  for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);"
                "  return JSON.stringify({status: r.status, body: btoa(s)});"
                "})()"
            )
            ws.send(json.dumps({
                "id": self._msg_id,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": expression,
                    "awaitPromise": True,
                    "returnByValue": True,
                },
            }))
            end = time.time() + timeout
            while time.time() < end:
                raw = json.loads(ws.recv())
                if raw.get("id") == self._msg_id:
                    value = raw["result"]["result"].get("value")
                    if not value:
                        raise BrowserError(f"download of {url} returned nothing")
                    payload = json.loads(value)
                    if payload["status"] != 200:
                        raise BrowserError(
                            f"download of {url} returned HTTP {payload['status']}"
                        )
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(base64.b64decode(payload["body"]))
                    return dest
            raise BrowserError(f"download of {url} timed out")
        finally:
            ws.close()
