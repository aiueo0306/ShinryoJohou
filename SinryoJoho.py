from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# RSS生成関数
def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("MHLW｜診療報酬改定関連 更新情報")
    fg.link(href="https://www.mhlw.go.jp/shinryohoshu/")
    fg.description("厚生労働省保険局『診療報酬改定関連』ページの更新履歴")
    fg.language("ja")
    fg.generator("python-feedgen")

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])
        entry.guid(item['link'], permalink=False)
        entry.pubDate(datetime.now(timezone.utc))  # 日時は現時点のタイムスタンプを使用

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path, pretty=True)
    print(f"✅ RSSフィード生成完了！保存先: {output_path}")

# メイン処理
with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")
        page.goto("https://www.mhlw.go.jp/shinryohoshu/", timeout=30000)
        page.wait_for_load_state("load", timeout=30000)
    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。")
        browser.close()
        exit()

    print("▶ 情報を抽出中...")
    items = []
    rows = page.locator("div.main2 table tr")
    count = rows.count()
    print(f"📦 発見した更新情報行数: {count}")

    for i in range(count):
        try:
            row = rows.nth(i)
            tds = row.locator("td")
            if tds.count() < 2:
                continue

            date_text = tds.nth(0).inner_text().strip()
            desc_html = tds.nth(1).inner_html().strip()
            link_elem = tds.nth(1).locator("a")

            link = "https://www.mhlw.go.jp/shinryohoshu/"
            if link_elem.count() > 0:
                raw_link = link_elem.first.get_attribute("href")
                if raw_link:
                    link = raw_link if raw_link.startswith("http") else f"https://www.mhlw.go.jp{raw_link}"

            title = desc_html.split("<br>")[0].strip()
            items.append({
                "title": title,
                "link": link,
                "description": desc_html
            })

        except Exception as e:
            print(f"⚠ 行 {i} の処理中にエラー: {e}")
            continue

    if not items:
        print("⚠ 更新情報が抽出できませんでした。構造変更の可能性があります。")

    # RSS出力
    rss_output_path = "rss_output/mhlw_shinryohoshu.xml"
    generate_rss(items, rss_output_path)

    browser.close()
