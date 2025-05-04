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
    print(f"✅ RSSフィード生成完了！\n📄 保存先: {output_path}")

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
    rows = page.locator("div.main2 table tr")
    items = []

    row_count = rows.count()
    print(f"📦 発見した更新行数: {row_count}")

    for i in range(row_count):
        row = rows.nth(i)
        try:
            date_text = row.locator("td").nth(0).inner_text().strip()
            content_html = row.locator("td").nth(1).inner_html().strip()

            title = f"更新情報 {date_text}"
            link_tag = row.locator("td").nth(1).locator("a")

            if link_tag.count() > 0:
                link = link_tag.first.get_attribute("href")
                if link and not link.startswith("http"):
                    link = "https://www.mhlw.go.jp" + link
            else:
                link = "https://www.mhlw.go.jp/shinryohoshu/"

            items.append({
                "title": title,
                "link": link,
                "description": content_html
            })

        except Exception as e:
            print(f"⚠ 行 {i} の処理中にエラーが発生: {e}")
            continue

    if not items:
        print("⚠ 情報が抽出できませんでした。HTML構造の変化が疑われます。")

    today = datetime.now().strftime("%Y%m%d")
    rss_output_path = f"rss_output/shinryohoshu_{today}.xml"
    generate_rss(items, rss_output_path)

    browser.close()
