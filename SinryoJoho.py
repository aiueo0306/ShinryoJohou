from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os
from playwright.sync_api import sync_playwright

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
        entry.pubDate(datetime.now(timezone.utc))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)

with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    print("▶ ページにアクセス中...")
    page.goto("https://www.mhlw.go.jp/shinryohoshu/")
    page.wait_for_load_state("load")

    print("▶ 更新情報を抽出しています...")
    items = []

    # 「掲載情報の更新について」のh2要素を探す
    all_main2_divs = page.locator("div.main2")
    for i in range(all_main2_divs.count()):
        div = all_main2_divs.nth(i)
        header_text = div.locator("h2").inner_text().strip()
        if "掲載情報の更新" in header_text:
            table = div.locator("table").first
            rows = table.locator("tr")
            row_count = rows.count()
            print(f"📦 発見した更新情報行数: {row_count}")

            for j in range(row_count):
                row = rows.nth(j)
                tds = row.locator("td")
                if tds.count() < 2:
                    continue

                date = tds.nth(0).inner_text().strip()
                description = tds.nth(1).inner_text().strip()
                raw_html = tds.nth(1).inner_html().strip()

                # 最初のリンクを使う
                link = "https://www.mhlw.go.jp/shinryohoshu/"
                link_elem = tds.nth(1).locator("a")
                if link_elem.count() > 0:
                    href = link_elem.first.get_attribute("href")
                    if href:
                        link = href if href.startswith("http") else f"https://www.mhlw.go.jp{href}"

                items.append({
                    "title": f"{date}｜{description.splitlines()[0]}",
                    "link": link,
                    "description": raw_html
                })
            break  # 対象の<div class="main2">が見つかればループ終了

    if not items:
        print("⚠ 抽出できた更新情報がありません。HTML構造が変更された可能性があります。")

    output_path = "rss_output/mhlw_shinryohoshu.xml"
    generate_rss(items, output_path)
    print(f"✅ RSSフィード生成完了！保存先: {output_path}")

    browser.close()
