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
    fg.docs("http://www.rssboard.org/rss-specification")

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])
        entry.guid(item['link'], permalink=False)
        entry.pubDate(datetime.now(timezone.utc))  # タイムゾーン付きで統一

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
    try:
        main2_divs = page.locator("div.main2")
        rows = main2_divs.nth(1).locator("table tr")  # 2つ目のmain2にあるテーブル
        count = rows.count()
        print(f"📦 発見した更新情報行数: {count}")

        items = []
        for i in range(count):
            row = rows.nth(i)
            try:
                date_text = row.locator("td:nth-child(1)").inner_text().strip()
                desc_td = row.locator("td:nth-child(2)")
                desc_text = desc_td.inner_text().strip()

                # 最初のリンク取得（あれば）
                try:
                    first_link = desc_td.locator("a").first
                    href = first_link.get_attribute("href")
                    if href and not href.startswith("http"):
                        href = "https://www.mhlw.go.jp" + href
                except:
                    href = "https://www.mhlw.go.jp/shinryohoshu/"  # fallback

                title = f"{date_text} 更新情報"
                items.append({
                    "title": title,
                    "link": href,
                    "description": desc_text
                })
            except Exception as e:
                print(f"⚠ エラー行（{i}）: {e}")
                continue

        if not items:
            print("⚠ 抽出できた更新情報がありません。HTML構造が変更された可能性があります。")

        rss_path = "rss_output/mhlw_shinryohoshu.xml"
        generate_rss(items, rss_path)

        print(f"\n✅ RSSフィード生成完了！\n📄 保存先: {rss_path}")
    finally:
        browser.close()
