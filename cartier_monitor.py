"""
카르티에 재고 모니터 (GitHub Actions용) v5
- playwright-stealth 으로 Cloudflare 우회
- 실제 보이고 활성화된 버튼만 감지
"""

import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

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
    print(f"[{now}] 카르티에 재고 확인 시작 v5")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1440,900",
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
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            },
        )

        page = context.new_page()

        # ★ stealth 적용 (Cloudflare 우회 핵심)
        stealth_sync(page)

        print("페이지 로딩 중...")
        try:
            page.goto(URL, timeout=45000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"goto 오류: {e}")

        # 사람처럼 행동
        page.wait_for_timeout(6000)
        page.mouse.move(600, 400)
        page.wait_for_timeout(1000)
        page.evaluate("window.scrollTo({top: 500, behavior: 'smooth'})")
        page.wait_for_timeout(4000)

        # 페이지 상태 출력
        content = page.content()
        print(f"HTML 길이: {len(content)}자")

        # 버튼 탐색
        found_text = None
        print("--- 보이는 버튼 탐색 ---")
        try:
            buttons = page.locator("button").all()
            print(f"전체 버튼 수: {len(buttons)}")
            for i, btn in enumerate(buttons[:30]):
                try:
                    if not btn.is_visible():
                        continue
                    txt = btn.inner_text().strip()
                    is_disabled = btn.is_disabled()
                    print(f"  visible 버튼[{i}]: '{txt}' | disabled={is_disabled}")
                    if TARGET_TEXT in txt and not is_disabled:
                        found_text = TARGET_TEXT
                        break
                    elif SOLDOUT_TEXT in txt:
                        found_text = SOLDOUT_TEXT
                        break
                except Exception:
                    pass
        except Exception as e:
            print(f"버튼 탐색 오류: {e}")

        # 버튼으로 못찾으면 HTML 전체에서 탐색
        if found_text is None:
            print("버튼 탐색 실패 → HTML 전체 탐색")
            if TARGET_TEXT in content:
                # 숨겨진 버튼인지 확인
                disabled_check = page.locator(f"button:has-text('{TARGET_TEXT}')").first
                try:
                    if disabled_check.count() > 0 and not disable_check.is_disabled():
                        found_text = TARGET_TEXT
                    else:
                        print(f"  '{TARGET_TEXT}' HTML에 있지만 비활성/숨김 상태")
                except Exception:
                    pass
            if SOLDOUT_TEXT in content:
                found_text = SOLDOUT_TEXT
                print(f"  '{SOLDOUT_TEXT}' HTML에서 발견")

        print(f"\n최종 판단: '{found_text}'")

        if found_text == TARGET_TEXT:
            print("재고 감지! 텔레그램 전송")
            send_telegram(
                "🛒 <b>카르티에 재고 알람!</b>\n\n"
                "탱크 머스트 솔라비트™ (CRWSTA0089)\n"
                "✅ <b>지금 구매 가능합니다!</b>\n\n"
                f"🔗 {URL}\n\n"
                f"<i>{now}</i>"
            )
        elif found_text == SOLDOUT_TEXT:
            print("품절 상태 확인 — 알람 없음 (정상 모니터링 중)")
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
