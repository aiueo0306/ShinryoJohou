from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("MHLW｜診療報酬改定関連 更新情報")
    fg.link(href="https://shinryohoshu.mhlw.go.jp/shinryohoshu/infoMenu/")
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
        page.goto("https://shinryohoshu.mhlw.go.jp/shinryohoshu/infoMenu/", timeout=30000)
        page.wait_for_load_state("load", timeout=30000)
    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。")
        browser.close()
        exit()

    print("▶ 更新情報を抽出しています...")

    # 該当するテーブル行を抽出
    selector = "body > table > tbody > tr > td:nth-child(1) > div:nth-child(5) > p:nth-child(2) > table > tbody > tr
    rows = page.locator(selector)
    count = rows.count()
    print(f"📦 発見した更新情報行数: {count}")

    items = []

    for i in range(count):
        row = rows.nth(i)
        try:
            date = row.locator("td:nth-child(1)").inner_text().strip()
            content_html = row.locator("td:nth-child(2)").inner_html().strip()
            link = "https://www.mhlw.go.jp/shinryohoshu/"

            items.append({
                "title": f"更新情報: {date}",
                "link": link,
                "description": content_html
            })
        except Exception as e:
            print(f"⚠ 行{i+1}の解析に失敗: {e}")
            continue

    if not items:
        print("⚠ 抽出できた更新情報がありません。HTML構造が変わっている可能性があります。")

    rss_path = "rss_output/mhlw_shinryohoshu.xml"
    generate_rss(items, rss_path)

    print(f"\n✅ RSSフィード生成完了！📄 保存先: {rss_path}")
    browser.close()
