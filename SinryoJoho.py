from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os

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
        print("⚠ ページの読み込みに失敗しました。")
        browser.close()
        exit()

    print("▶ 更新情報を抽出しています...")

    # 掲載情報の更新について -> div.main2の2つ目
    try:
        rows = page.locator("div.main2:nth-of-type(2) table tr")
        count = rows.count()
        print(f"📦 発見した更新情報行数: {count}")
        items = []

        for i in range(count):
            row = rows.nth(i)
            date = row.locator("td").nth(0).inner_text().strip()
            content_td = row.locator("td").nth(1)
            content_html = content_td.inner_html().strip()
            link_el = content_td.locator("a")
            link = link_el.first.get_attribute("href") if link_el.count() > 0 else "#"

            # 絶対パスに変換
            if link and not link.startswith("http"):
                link = f"https://www.mhlw.go.jp{link}"

            # タイトルに日付を含める（RSS上で重複しないように）
            title = f"{date} 更新情報"
            items.append({
                "title": title,
                "link": link,
                "description": content_html
            })

    except Exception as e:
        print(f"⚠ エラー発生: {e}")
        items = []

    if not items:
        print("⚠ 抽出できた更新情報がありません。HTML構造が変更された可能性があります。")

    rss_path = "rss_output/mhlw_shinryohoshu.xml"
    generate_rss(items, rss_path)
    print(f"✅ RSSフィード生成完了！保存先: {rss_path}")
    browser.close()
