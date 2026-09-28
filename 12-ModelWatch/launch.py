"""Build the reports, then open the static entry page in Edge. No server is needed."""

import os
import subprocess
from pathlib import Path

from modelwatch.pipeline import ROOT, run


def main():
    run(ROOT / "reports")
    target = (ROOT / "reports" / "index.html").as_uri()
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    browser = next((path for path in candidates if path.exists()), None)
    if browser:
        subprocess.Popen([str(browser), target])
    elif os.name == "nt":
        os.startfile(str(ROOT / "reports" / "index.html"))
    else:
        import webbrowser
        webbrowser.open(target)
    print("Report ready:", ROOT / "reports" / "index.html")


if __name__ == "__main__":
    main()
