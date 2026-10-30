"""为 Docker 后端提供本机无头 Chrome；调试端口仅监听本机。"""

from __future__ import annotations

import argparse
import signal
from threading import Event
from types import FrameType

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9223)
    parser.add_argument("--channel", default="chrome")
    args = parser.parse_args()
    stopping = Event()

    def stop(signum: int, frame: FrameType | None) -> None:
        stopping.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel=args.channel, headless=True,
            args=[f"--remote-debugging-port={args.port}", "--remote-debugging-address=127.0.0.1"],
        )
        try:
            page = browser.new_page()
            print(f"无头 Chrome 已启动，本机调试端口 {args.port}", flush=True)
            while not stopping.is_set():
                page.wait_for_timeout(1000)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
