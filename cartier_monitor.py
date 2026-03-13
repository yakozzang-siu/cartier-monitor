"""
카르티에 재고 모니터 (GitHub Actions용) v4
- 실제로 보이고 클릭 가능한 버튼만 감지
- 오탐 방지
"""

import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

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
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
        print(f"텔레그램 응답: {r.status_code}")
    except Exception as e:
        print(f"텔레그램 전송 오류: {e}")


def main():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] 카르티에 재고 확인 시작 v4")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
            viewport={"width": 1440, "height": 900},
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            },
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en-US'] });
        """)

        page = context.new_page()

        print("페이지 로딩 중...")
        try:
            page.goto(URL, timeout=40000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"goto 오류: {e}")

        page.wait_for_timeout(8000)
        page.evaluate("window.scrollTo(0, 400)")
        page.wait_for_timeout(3000)

        # ─────────────────────────────────────────────────────
        # 핵심: 버튼이 실제로 보이고(visible) 활성화(enabled) 상태인지 확인
        # ─────────────────────────────────────────────────────
        found_text = None

        print("--- 실제 보이는 버튼 탐색 ---")
        try:
            buttons = page.locator("button").all()
            print(f"전체 버튼 수: {len(buttons)}")
            for i, btn in enumerate(buttons[:30]):
                try:
                    # 보이는 버튼만 체크
                    if not btn.is_visible():
                        continue
                    txt = btn.inner_text().strip()
                    is_disabled = btn.is_disabled()
                    print(f"  visible 버튼[{i}]: '{txt}' | disabled={is_disabled}")

                    if TARGET_TEXT in txt and not is_disabled:
                        found_text = TARGET_TEXT
                        print(f"  → 구매 가능 버튼 감지!")
                        break
                    elif SOLDOUT_TEXT in txt:
                        found_text = SOLDOUT_TEXT
                        print(f"  → 품절 버튼 감지")
                        break
                except Exception:
                    pass
        except Exception as e:
            print(f"버튼 탐색 오류: {e}")

        print(f"\n최종 판단: '{found_text}'")

        # ─────────────────────────────────────────────────────
        # 결과에 따라 텔레그램 전송
        # ─────────────────────────────────────────────────────
        if found_text == TARGET_TEXT:
            print("🎉 재고 감지! 텔레그램 전송")
            send_telegram(
                "🛒 <b>카르티에 재고 알람!</b>\n\n"
                "탱크 머스트 솔라비트™ (CRWSTA0089)\n"
                "✅ <b>지금 구매 가능합니다!</b>\n\n"
                f"🔗 {URL}\n\n"
                f"<i>{now}</i>"
            )
        elif found_text == SOLDOUT_TEXT:
            # 품절 상태 — 텔레그램 안 보냄 (정상)
            print("품절 상태 확인 — 알람 없음")
        else:
            print("버튼 찾지 못함 — 경고 전송")
            send_telegram(
                "⚠️ <b>카르티에 모니터 경고</b>\n"
                "버튼을 찾지 못했습니다. 사이트 차단 가능성 있음.\n"
                f"<i>{now}</i>"
            )

        browser.close()


if __name__ == "__main__":
    main()
