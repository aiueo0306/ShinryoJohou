from playwright.sync_api import sync_playwright
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

    print("▶ ページにアクセス中...")
    url = "https://www.mhlw.go.jp/shinryohoshu/"
    page.goto(url, timeout=30000)
    page.wait_for_load_state("load", timeout=30000)

    print("▶ HTMLから更新情報を抽出しています...")

    # すべての更新行を含む行を取得（div.main2 > table）
    rows = page.locator("div.main2 table tr")
    row_count = rows.count()
    print(f"📦 発見した更新情報行数: {row_count}")

    items = []
    for i in range(row_count):
        try:
            row = rows.nth(i)
            date = row.locator("td").nth(0).inner_text().strip()
            description = row.locator("td").nth(1).inner_text().strip()

            # 埋め込まれている最初のリンクを取得（ある場合）
            try:
                link = row.locator("td").nth(1).locator("a").first.get_attribute("href")
                if link and not link.startswith("http"):
                    link = "https://www.mhlw.go.jp" + link
            except:
                link = url  # fallback

            items.append({
                "title": f"{date} 更新情報",
                "link": link,
                "description": description
            })
        except Exception as e:
            print(f"⚠ エラーが発生しました: {e}")
            continue

    if not items:
        print("⚠ 抽出できた更新情報がありません。HTML構造が変更された可能性があります。")

    rss_path = "rss_output/mhlw_shinryohoshu.xml"
    generate_rss(items, rss_path)
    print(f"✅ RSSフィード生成完了！保存先: {os.path.abspath(rss_path)}")

    browser.close()
