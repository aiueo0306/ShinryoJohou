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
    page.goto("https://www.mhlw.go.jp/shinryohoshu/", timeout=60000)
    page.wait_for_load_state("load", timeout=10000)

    print("▶ HTMLを保存中（デバッグ用）...")
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(page.content())

    print("▶ 更新情報を抽出しています...")
    items = []

    # XPathで最初のmain2ブロック内の最初のtableを取得
    rows = page.locator('//div[@class="main2"][1]//table[1]//tr')
    count = rows.count()
    print(f"📦 発見した更新情報行数: {count}")

    for i in range(count):
        row = rows.nth(i)
        tds = row.locator("td")
        if tds.count() < 2:
            continue

        date = tds.nth(0).inner_text().strip()
        description = tds.nth(1).inner_text().strip()
        raw_html = tds.nth(1).inner_html().strip()

        # 最初のリンクを取得（なければトップページ）
        link_elem = tds.nth(1).locator("a")
        link = "https://www.mhlw.go.jp/shinryohoshu/"
        if link_elem.count() > 0:
            href = link_elem.first.get_attribute("href")
            if href:
                link = href if href.startswith("http") else f"https://www.mhlw.go.jp{href}"

        items.append({
            "title": f"{date}｜{description.splitlines()[0]}",
            "link": link,
            "description": raw_html
        })

    if not items:
        print("⚠ 抽出できた更新情報がありません。HTML構造が変更された可能性があります。")

    output_path = "rss_output/mhlw_shinryohoshu.xml"
    generate_rss(items, output_path)
    print(f"✅ RSSフィード生成完了！保存先: {output_path}")
    browser.close()
