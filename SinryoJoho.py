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

    print("▶ 更新情報を抽出しています...")
    items = []

    # 明示的に「掲載情報の更新について」セクションのtableをターゲットにする
    try:
        table = page.locator("text=掲載情報の更新について").locator("xpath=..").locator("xpath=..").locator("table").first
        rows = table.locator("tr")
        count = rows.count()
        print(f"📦 発見した更新情報行数: {count}")

        for i in range(count):
            row = rows.nth(i)
            cols = row.locator("td")
            if cols.count() < 2:
                continue

            date_text = cols.nth(0).inner_text().strip()
            desc_html = cols.nth(1).inner_html().strip()
            desc_text = cols.nth(1).inner_text().strip()

            link = "https://www.mhlw.go.jp/shinryohoshu/"
            link_elem = cols.nth(1).locator("a")
            if link_elem.count() > 0:
                raw_link = link_elem.first.get_attribute("href")
                if raw_link:
                    if raw_link.startswith("http"):
                        link = raw_link
                    else:
                        link = f"https://www.mhlw.go.jp{raw_link}"

            title = desc_text.splitlines()[0].strip() if desc_text else "診療報酬改定関連のお知らせ"
            items.append({
                "title": f"{date_text}｜{title}",
                "link": link,
                "description": desc_html
            })

    except Exception as e:
        print(f"⚠ 更新情報の抽出に失敗しました: {e}")

    if not items:
        print("⚠ 抽出できた情報がありません。HTML構造が変更された可能性があります。")

    rss_path = "rss_output/mhlw_shinryohoshu.xml"
    generate_rss(items, rss_path)
    print(f"\n✅ RSSフィード生成完了！\n📄 保存先: {rss_path}")

    browser.close()
