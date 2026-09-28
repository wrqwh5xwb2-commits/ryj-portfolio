"""启动入口：优先在 Edge 打开，服务只监听本机。"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent


def is_ours(url):
    try:
        with urlopen(url + "/api/health", timeout=1) as response:
            info = json.load(response)
            return info.get("status") == "ok" and info.get("app") == "ocrdesk"
    except Exception:
        return False


def open_browser(url):
    paths = [Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe", Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe"]
    for path in paths:
        if path.exists():
            subprocess.Popen([str(path), url])
            return
    webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=8771)
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    if is_ours(url):
        if not args.no_browser:
            open_browser(url)
        print("OCRDesk already running: " + url)
        return
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", args.port))
        except OSError:
            raise SystemExit(f"Port {args.port} is occupied. Try: python launch.py --port 8773")
    if not args.no_browser:
        def when_ready():
            for _ in range(80):
                if is_ours(url):
                    open_browser(url)
                    return
                time.sleep(.25)
        threading.Thread(target=when_ready, daemon=True).start()
    import uvicorn
    print("OCRDesk: " + url + " | Ctrl+C to stop")
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, app_dir=str(ROOT))


if __name__ == "__main__":
    main()
