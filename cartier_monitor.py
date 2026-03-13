"""
카르티에 재고 모니터 (GitHub Actions용) v2
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
    """텔레그램 전송 + 결과 출력"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
        print(f"텔레그램 응답 코드: {r.status_code}")
        print(f"텔레그램 응답 내용: {r.text}")
    except Exception as e:
        print(f"텔레그램 전송 오류: {e}")


def main():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] 카르티에 재고 확인 시작")

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
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        print(f"페이지 로딩 중: {URL}")
        page.goto(URL, timeout=40000)

        # 페이지 완전 로딩 대기
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            print("networkidle 타임아웃 — 계속 진행")

        # 추가 대기 (JS 렌더링)
        page.wait_for_timeout(5000)

        # 페이지 전체 텍스트에서 키워드 탐색
        content = page.content()
        page_text = page.inner_text("body")

        print("--- 페이지 텍스트 일부 (버튼 주변) ---")
        # 관련 키워드 주변 텍스트 출력
        for keyword in [TARGET_TEXT, SOLDOUT_TEXT, "Add to bag", "add-to-bag", "카트", "장바구니"]:
            if keyword in content:
                print(f"  HTML에서 발견: '{keyword}'")
            if keyword in page_text:
                print(f"  페이지텍스트에서 발견: '{keyword}'")

        # 버튼 요소 전체 탐색
        print("--- 발견된 버튼 목록 ---")
        buttons = page.locator("button").all()
        print(f"  버튼 총 {len(buttons)}개 발견")
        for i, btn in enumerate(buttons[:20]):  # 최대 20개
            try:
                txt = btn.inner_text().strip()
                if txt:
                    print(f"  버튼[{i}]: '{txt}'")
            except Exception:
                pass

        # 결과 판단
        found_text = None
        if TARGET_TEXT in content or TARGET_TEXT in page_text:
            found_text = TARGET_TEXT
        elif SOLDOUT_TEXT in content or SOLDOUT_TEXT in page_text:
            found_text = SOLDOUT_TEXT
        else:
            # 버튼에서 직접 탐색
            for btn in buttons[:20]:
                try:
                    txt = btn.inner_text().strip()
                    if TARGET_TEXT in txt:
                        found_text = TARGET_TEXT
                        break
                    elif SOLDOUT_TEXT in txt:
                        found_text = SOLDOUT_TEXT
                        break
                except Exception:
                    pass

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
            print("품절 상태 확인됨 — 알람 없음")
        else:
            print("버튼을 찾지 못함 — 경고 전송")
            send_telegram(
                "⚠️ <b>카르티에 모니터 경고</b>\n"
                "버튼을 찾지 못했습니다. 사이트 구조 확인 필요.\n"
                f"<i>{now}</i>"
            )

        browser.close()


if __name__ == "__main__":
    main()
