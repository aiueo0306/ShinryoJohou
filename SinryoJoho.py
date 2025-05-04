from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("MHLW｜診療報酬改定関連 更新情報")
    fg.link(href="https://www.mhlw.go.jp/shinryohoshu/")
    fg.description("厚生労働省保険局『診療報酬改定関連』ページの更新履歴")
    fg.language("ja")

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])
        entry.guid(item['link'], permalink=False)
        entry.pubDate(datetime.now(timezone.utc))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)

with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")
        page.goto("https://www.mhlw.go.jp/shinryohoshu/", timeout=30000)
        page.wait_for_load_state("load", timeout=30000)
    except PlaywrightTimeoutError:
        print("⚠ ページ読み込み失敗")
        browser.close()
        exit()

    print("▶ 更新情報を抽出しています...")

    # 2つ目の .main2 内の table tr を取得
    rows = page.locator("div.main2:nth-of-type(2) table tr")
    count = rows.count()
    print(f"📦 発見した更新情報行数: {count}")

    items = []

    for i in range(count):
        row = rows.nth(i)
        try:
            date = row.locator("td:nth-child(1)").inner_text().strip()
            description = row.locator("td:nth-child(2)").inner_html().strip()
            link_elem = row.locator("td:nth-child(2) a")
            if link_elem.count() > 0:
                link = link_elem.first.get_attribute("href")
                if link and not link.startswith("http"):
                    link = f"https://www.mhlw.go.jp{link}"
            else:
                link = "https://www.mhlw.go.jp/shinryohoshu/"

            title = f"{date} の更新"
            items.append({
                "title": title,
                "link": link,
                "description": description
            })
        except Exception as e:
            print(f"⚠ 行{i+1}の処理に失敗: {e}")
            continue

    if not items:
        print("⚠ 抽出できた更新情報がありません。HTML構造が変更された可能性があります。")

    rss_path = "rss_output/mhlw_shinryohoshu.xml"
    generate_rss(items, rss_path)
    print(f"✅ RSSフィード生成完了！保存先: {rss_path}")

    browser.close()
