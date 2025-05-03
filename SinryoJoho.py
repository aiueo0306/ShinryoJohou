from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("診療報酬情報提供サービス｜更新情報")
    fg.link(href="https://shinryohoshu.mhlw.go.jp/shinryohoshu/infoMenu/")
    fg.description("厚労省 診療報酬情報提供サービスの更新履歴")
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
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")
        page.goto("https://shinryohoshu.mhlw.go.jp/shinryohoshu/infoMenu/", timeout=30000)
        page.wait_for_load_state("load", timeout=30000)
    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。")
        browser.close()
        exit()

    print("▶ 情報を抽出しています...")
    rows = page.locator("body > table > tr > td > div > table > tr")
    items = []

    count = rows.count()
    print(f"📦 発見した行数: {count}")

    for i in range(count):
        row = rows.nth(i)
        try:
            # td[2]/child::node() での説明取得
            description = row.locator("td:nth-child(2)").inner_html().strip()

            # タイトルとリンクの抽出（aタグがあれば）
            link_el = row.locator("td:nth-child(2) a")
            if link_el.count() > 0:
                title = link_el.inner_text().strip()
                link = link_el.get_attribute("href")
                if link and not link.startswith("http"):
                    link = f"https://shinryohoshu.mhlw.go.jp{link}"
            else:
                title = description[:30]  # タイトルがなければ先頭数文字
                link = "https://shinryohoshu.mhlw.go.jp/shinryohoshu/infoMenu/"  # ベースURL

            items.append({"title": title, "link": link, "description": description})
        except Exception as e:
            print(f"⚠ 行 {i} の抽出中にエラー: {e}")
            continue

    if not items:
        print("⚠ 抽出できた情報がありません。HTML構造変更の可能性があります。")

    rss_path = f"rss_output/shinryohoshu.xml"
    generate_rss(items, rss_path)

    print(f"\n✅ RSSフィード生成完了！\n📄 保存先: {rss_path}")
    browser.close()
