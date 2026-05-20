from playwright.sync_api import sync_playwright
import re
import requests
import time

URL = "https://www.viagogo.de/Konzert-Tickets/Pop-Rock/Asian-Pop/Korean-Pop/BTS-Karten/E-160262243?backUrl=%2FKonzert-Tickets%2FPop-Rock%2FAsian-Pop%2FKorean-Pop%2FBTS-Karten&lt=48.146&lg=11.456"

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/xxx"


# -----------------------------
# 等待 listings 出现（稳定版）
# -----------------------------
def wait_for_listings(page, timeout=30000):
    for _ in range(int(timeout / 1000)):
        count = page.locator("[data-listing-id]").count()
        if count > 0:
            return True
        page.wait_for_timeout(1000)
    return False


# -----------------------------
# 提取数据
# -----------------------------
def extract_listings(page):
    cards = page.locator("[data-listing-id]")
    count = cards.count()

    results = []

    for i in range(count):
        c = cards.nth(i)

        listing = {}

        # price
        price = c.get_attribute("data-price")
        if price:
            try:
                listing["price"] = float(price.replace("€", "").strip())
            except:
                listing["price"] = None

        # title
        try:
            title = c.locator("h3").inner_text().strip()
        except:
            title = "Unknown"

        listing["title"] = title

        match = re.search(r"\d+", title)
        level = int(match.group()[0]) if match else None

        if level == 1:
            listing["level"] = "一层看台"
        elif level == 2:
            listing["level"] = "二层看台"
        elif level == 3:
            listing["level"] = "三层看台"
        else:
            listing["level"] = "内场"

        if level == 3 and (listing.get("price") or 0) >= 400:
            continue

        # row
        try:
            row_text = c.locator("text=/Reihe/").first.inner_text()
            match = re.search(r"\d+", row_text)
            listing["row"] = int(match.group()) if match else "未知"
        except:
            listing["row"] = ""

        results.append(listing)

    return results


# -----------------------------
# Discord
# -----------------------------
def send_to_discord(message):
    if not message:
        return

    try:
        requests.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        print("Discord send failed:", e)


# -----------------------------
# 主程序
# -----------------------------
def run():
    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )

        page = context.new_page()

        # 打开页面（稳定加载）
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        try:
            page.locator("button[aria-label='1 Ticket']").click(timeout=2000)
        except:
            pass

        # cookie
        try:
            page.locator("button[data-testid='cookie-compliance-allow-all-button']").click(timeout=3000)
            #page.wait_for_timeout(2000000)
        except:
            pass

        # quantity - select版本

        try:
            modal = page.locator("div[data-testid='quantity-modal']")
            modal.wait_for(timeout=10000)

            modal.locator("select[aria-label='Anzahl der Tickets']").select_option("1")

            modal.locator("button:has-text('Weiter')").click(timeout=3000)

        except:
            pass

        # 等 listings
        if not wait_for_listings(page):
            print("❌ no listings found")
            page.screenshot(path="debug.png", full_page=True)
            browser.close()
            return

        page.wait_for_timeout(2000)

        listings = extract_listings(page)

        if not listings:
            print("❌ empty listings")
            browser.close()
            return

        message = ""

        for i, item in enumerate(listings):
            text = (
                f"\n星期六🎫{i+1}\n"
                f"💶 {int(item.get('price') or 0)}€\n"
                f"📍 {item.get('level'), item.get('title')}\n"
                f"🪑 第{item.get('row')}排\n"
            )

            print(text)
            message += text

        send_to_discord(message)

        browser.close()


if __name__ == "__main__":
    run()