"""
카르티에 재고 모니터 (GitHub Actions용) v10
- 여러 제품 동시 모니터링
"""

import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

# ★ 모니터링할 제품 목록 — 추가하고 싶으면 여기에 계속 추가
PRODUCTS = [
    {
        "name": "탱크 머스트 솔라비트™ (CRWSTA0089)",
        "url": (
            "https://www.cartier.com/ko-kr/watches/all-collections/tank/"
            "%ED%83%B1%ED%81%AC-%EB%A8%B8%EC%8A%A4%ED%8A%B8-%EC%86%94%EB%9D%BC%EB%B9%84%ED%8A%B8%E2%84%A2-"
            "%EC%9B%8C%EC%B9%98-CRWSTA0089.html"
        ),
    },
    {
        "name": "탱크 머스트 드 까르띠에 (CRWSTA0135)",
        "url": (
            "https://www.cartier.com/ko-kr/watches/all-collections/tank/"
            "%ED%83%B1%ED%81%AC-%EB%A8%B8%EC%8A%A4%ED%8A%B8-%EB%93%9C-%EA%B9%8C%EB%A5%B4%EB%9D%A0%EC%97%90-"
            "%EC%9B%8C%EC%B9%98-CRWSTA0135.html"
        ),
    },
]

TARGET_TEXT  = "백에 추가하기"
SOLDOUT_TEXT = "상담원 연결"

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en']});
Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});
window.chrome = {runtime: {}};
"""


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


def dismiss_popup(page) -> bool:
    """국가 선택 팝업 닫기"""
    popup_texts = [
        "현재 사이트로 계속하기",
        "현재 위치로 계속",
        "계속하기",
        "Stay on this site",
        "Continue",
    ]
    for text in popup_texts:
        try:
            btn = page.get_by_text(text, exact=False).first
            if btn.count() > 0 and btn.is_visible():
                btn.click()
                print(f"  팝업 닫음: '{text}' 클릭")
                page.wait_for_timeout(3000)
                return True
        except Exception:
            pass

    try:
        buttons = page.locator("button").all()
        for btn in buttons:
            try:
                if not btn.is_visible():
                    continue
                txt = btn.inner_text().strip()
                for text in popup_texts:
                    if text in txt:
                        btn.click()
                        print(f"  팝업 닫음 (버튼): '{txt}' 클릭")
                        page.wait_for_timeout(3000)
                        return True
            except Exception:
                pass
    except Exception:
        pass

    return False


def check_product(page, product: dict) -> str | None:
    """제품 페이지 확인 — 버튼 텍스트 반환"""
    print(f"\n{'='*50}")
    print(f"확인 중: {product['name']}")
    print(f"URL: {product['url']}")

    try:
        page.goto(product["url"], timeout=45000, wait_until="domcontentloaded")
    except Exception as e:
        print(f"goto 오류: {e}")
        return None

    page.wait_for_timeout(6000)

    # 팝업 처리
    dismiss_popup(page)
    page.wait_for_timeout(3000)
    page.evaluate("window.scrollTo({top: 500, behavior: 'smooth'})")
    page.wait_for_timeout(3000)

    content = page.content()
    found_text = None

    # 버튼 탐색
    try:
        buttons = page.locator("button").all()
        print(f"전체 버튼 수: {len(buttons)}")
        for i, btn in enumerate(buttons[:30]):
            try:
                if not btn.is_visible():
                    continue
                txt = btn.inner_text().strip()
                is_disabled = btn.is_disabled()
                print(f"  버튼[{i}]: '{txt}' | disabled={is_disabled}")
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

    # HTML 전체 탐색 (백업)
    if found_text is None:
        if SOLDOUT_TEXT in content:
            found_text = SOLDOUT_TEXT
            print(f"  HTML에서 '{SOLDOUT_TEXT}' 발견")
        elif TARGET_TEXT in content:
            found_text = TARGET_TEXT
            print(f"  HTML에서 '{TARGET_TEXT}' 발견")

    print(f"최종 판단: '{found_text}'")
    return found_text


def main():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] 카르티에 재고 확인 시작 v10 — {len(PRODUCTS)}개 제품")

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
                "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            },
        )
        context.add_init_script(STEALTH_JS)
        page = context.new_page()

        for product in PRODUCTS:
            result = check_product(page, product)

            if result == TARGET_TEXT:
                print(f"재고 감지! → {product['name']}")
                send_telegram(
                    "🛒 <b>카르티에 재고 알람!</b>\n\n"
                    f"<b>{product['name']}</b>\n"
                    "✅ <b>지금 구매 가능합니다!</b>\n\n"
                    f"🔗 {product['url']}\n\n"
                    f"<i>{now}</i>"
                )
            elif result == SOLDOUT_TEXT:
                print(f"품절 상태 — 알람 없음")
            else:
                print(f"버튼 찾지 못함 — 경고")
                send_telegram(
                    f"⚠️ <b>카르티에 모니터 경고</b>\n"
                    f"버튼을 찾지 못했습니다.\n"
                    f"제품: {product['name']}\n"
                    f"<i>{now}</i>"
                )

        browser.close()


if __name__ == "__main__":
    main()
