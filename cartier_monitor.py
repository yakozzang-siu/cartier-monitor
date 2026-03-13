"""
카르티에 재고 모니터 (GitHub Actions용) v3
봇 차단 우회 + 텔레그램 알람
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
        print(f"텔레그램 응답: {r.status_code} / {r.text[:100]}")
    except Exception as e:
        print(f"텔레그램 전송 오류: {e}")


def main():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] 카르티에 재고 확인 시작 v3")

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
            # 봇 감지 우회
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            },
        )

        # webdriver 속성 제거 (봇 감지 우회)
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

        # 사람처럼 대기
        page.wait_for_timeout(8000)

        # 스크롤 (JS 렌더링 유도)
        page.evaluate("window.scrollTo(0, 300)")
        page.wait_for_timeout(3000)

        # 페이지 전체 텍스트 탐색
        try:
            page_text = page.inner_text("body")
        except Exception:
            page_text = ""

        content = page.content()

        print(f"페이지 텍스트 길이: {len(page_text)}자")
        print(f"HTML 길이: {len(content)}자")

        # 버튼 탐색 및 출력
        print("--- 버튼 목록 ---")
        try:
            buttons = page.locator("button").all()
            print(f"버튼 총 {len(buttons)}개")
            for i, btn in enumerate(buttons[:30]):
                try:
                    txt = btn.inner_text().strip()
                    if txt:
                        print(f"  버튼[{i}]: '{txt}'")
                except Exception:
                    pass
        except Exception as e:
            print(f"버튼 탐색 오류: {e}")

        # 키워드 탐색
        print("--- 키워드 탐색 ---")
        for kw in [TARGET_TEXT, SOLDOUT_TEXT, "Add to bag", "Contact", "advisor"]:
            in_html = kw in content
            in_text = kw in page_text
            print(f"  '{kw}' → HTML:{in_html} / 텍스트:{in_text}")

        # 결과 판단
        found_text = None
        if TARGET_TEXT in content or TARGET_TEXT in page_text:
            found_text = TARGET_TEXT
        elif SOLDOUT_TEXT in content or SOLDOUT_TEXT in page_text:
            found_text = SOLDOUT_TEXT

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
            print("품절 상태 확인됨 — 정상 모니터링 중")
            # 정상 작동 확인용 (처음 한번만 보고싶으면 이 send_telegram 삭제 가능)
            send_telegram(
                "✅ <b>카르티에 모니터 정상 작동</b>\n"
                "현재 상태: 품절 (상담원에 연결)\n"
                "재고 생기면 즉시 알려드릴게요!\n"
                f"<i>{now}</i>"
            )
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
