"""
카르티에 재고 모니터 (GitHub Actions용)
"상담원에 연결" → "백에 추가하기" 감지 시 텔레그램 알람
"""

import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# GitHub Secrets에서 환경변수로 읽어옴
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

URL = (
    "https://www.cartier.com/ko-kr/watches/all-collections/tank/"
    "%ED%83%B1%ED%81%AC-%EB%A8%B8%EC%8A%A4%ED%8A%B8-%EC%86%94%EB%9D%BC%EB%B9%84%ED%8A%B8%E2%84%A2-"
    "%EC%9B%8C%EC%B9%98-CRWSTA0089.html"
)

TARGET_TEXT  = "백에 추가하기"
SOLDOUT_TEXT = "상담원에 연결"


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }, timeout=10)


def get_button_text(page) -> str | None:
    try:
        page.wait_for_load_state("networkidle", timeout=25000)

        selectors = [
            f"button:has-text('{TARGET_TEXT}')",
            f"button:has-text('{SOLDOUT_TEXT}')",
            "button[class*='cta']",
            "button[class*='add']",
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    text = el.inner_text().strip()
                    if text:
                        return text
            except Exception:
                continue

        content = page.content()
        if TARGET_TEXT in content:
            return TARGET_TEXT
        if SOLDOUT_TEXT in content:
            return SOLDOUT_TEXT

        return None
    except Exception as e:
        print(f"오류: {e}")
        return None


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 카르티에 재고 확인 시작")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
        )
        page = context.new_page()
        page.goto(URL, timeout=30000)

        btn_text = get_button_text(page)
        print(f"버튼 텍스트: '{btn_text}'")

        if btn_text and TARGET_TEXT in btn_text:
            print("재고 감지! 텔레그램 전송")
            send_telegram(
                "🛒 <b>카르티에 재고 알람!</b>\n\n"
                "탱크 머스트 솔라비트™ (CRWSTA0089)\n"
                "✅ <b>지금 구매 가능합니다!</b>\n\n"
                f"🔗 {URL}\n\n"
                f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            )
        elif btn_text is None:
            print("버튼을 찾지 못했습니다.")
            send_telegram(
                "⚠️ <b>카르티에 모니터 경고</b>\n"
                "버튼을 찾지 못했습니다. 사이트 구조가 바뀌었을 수 있어요.\n"
                f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            )
        else:
            print(f"품절 상태 유지 중: '{btn_text}'")

        browser.close()


if __name__ == "__main__":
    main()
