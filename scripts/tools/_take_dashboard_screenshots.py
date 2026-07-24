"""用 Playwright 截取仪表盘桌面和移动端截图。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "outputs" / "playwright"
OUTPUT.mkdir(parents=True, exist_ok=True)

URL = "http://localhost:8502"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )

        # 桌面截图 (1920x1080)
        desktop_page = browser.new_page(viewport={"width": 1920, "height": 1080})
        desktop_page.goto(URL, wait_until="load", timeout=30000)
        time.sleep(5)  # 等待 Streamlit 渲染完成
        desktop_path = OUTPUT / "dashboard-desktop-latest.png"
        desktop_page.screenshot(path=str(desktop_path), full_page=True)
        print(f"[OK] 桌面截图: {desktop_path}")
        desktop_page.close()

        # 移动端截图 (375x812, iPhone X)
        mobile_page = browser.new_page(viewport={"width": 375, "height": 812})
        mobile_page.goto(URL, wait_until="load", timeout=30000)
        time.sleep(5)
        mobile_path = OUTPUT / "dashboard-mobile-latest.png"
        mobile_page.screenshot(path=str(mobile_path), full_page=True)
        print(f"[OK] 移动端截图: {mobile_path}")
        mobile_page.close()

        browser.close()
    print("[OK] Playwright 截图完成")


if __name__ == "__main__":
    main()
