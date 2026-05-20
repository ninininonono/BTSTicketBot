from playwright.sync_api import sync_playwright
import time
import re
import requests

#URL = "https://www.viagogo.de/Konzert-Tickets/Pop-Rock/Asian-Pop/Korean-Pop/BTS-Karten/E-160262243?backUrl=%2FKonzert-Tickets%2FPop-Rock%2FAsian-Pop%2FKorean-Pop%2FBTS-Karten&lt=48.146&lg=11.456"
URL = "https://www.viagogo.de/Konzert-Tickets/Pop-Rock/Asian-Pop/Korean-Pop/BTS-Karten/E-160262240?backUrl=%2FKonzert-Tickets%2FPop-Rock%2FAsian-Pop%2FKorean-Pop%2FBTS-Karten&lt=48.146&lg=11.456"

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1506654570057564250/c4VY3EHCcxJ_t5FMhsTTZpWcrqz3AiqQk9Zbw3wd91lfIDEhR3sWkZnEl1mJT1hJXd6b"


def extract_listings(page):
    cards = page.locator('[data-listing-id]').all()
    
    results = []

    for c in cards:
        listing = {}

        # price
        price = c.get_attribute("data-price")
        if price:
           listing["price"] = float(price.replace("€", "").strip())

        # title
        title = c.locator("h3").inner_text().strip()
        listing["title"] = title

        match = re.search(r"\d+", title)

        if match:
            level = int(match.group()[0])   # 只取第一位数字（1/2/3）
        else:
            level = None

        if level == 1:
            listing["level"] = "一层看台"
        elif level == 2:
            listing["level"] = "二层看台"
        elif level == 3:
            listing["level"] = "三层看台"
        else:
            listing["level"] = "内场"

        if level == 3 and listing.get("price", 0) >= 400:
            continue

        # row（可能不存在）
        row_locator = c.locator("text=/Reihe/")

        if row_locator.count() > 0:
            row_text = row_locator.first.inner_text()

            match = re.search(r"\d+", row_text)

            if match:
                listing["row"] = int(match.group())
            else:
                listing["row"] = "未知"

        else:
            listing["row"] = ""

        results.append(listing)

    return results


with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False
    )

    page = browser.new_page()

    page.goto(URL)

    page.wait_for_selector("[data-listing-id]", timeout=15000)

# 模拟人类行为
    page.mouse.move(100, 300)
    page.mouse.wheel(0, 800)
    page.wait_for_timeout(1000)

    page.mouse.click(200, 400)
    page.wait_for_timeout(2000)

    page.mouse.wheel(0, -400)
    page.wait_for_timeout(2000)


    # quantity - button版本
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

    # quantity - Jede版本（新增，不改原逻辑）
    #try:
    #    qty = page.locator("div[data-testid='event-detail-quantity-filter'] [role='combobox']")
    #    qty.click()

    #    page.locator("li[role='option']:has-text('1 Ticket')").click()

    #except:
    #    pass

    page.wait_for_selector("[data-listing-id]")
    page.wait_for_timeout(1000)
    
    listings = extract_listings(page)

    def send_to_discord(message):
        data = {
            "content": message
        }

        requests.post(DISCORD_WEBHOOK, json=data)

    message = ""

    for i, item in enumerate(listings):
        text = (
            f"\n星期天🎫{i+1}\n"
            f"💶 {int(item.get('price'))}€\n"
            f"📍 {item.get('level')}\n"
            f"🪑 第{item.get('row')}排\n"
        )

        print(text)

        message += text
    
    send_to_discord(message)

    browser.close()
