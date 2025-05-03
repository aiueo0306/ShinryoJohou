from feedgen.feed import FeedGenerator
from datetime import datetime, timezone, timedelta
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# 和暦「令和」→西暦変換
def convert_reiwa_date(reiwa_date_str):
    try:
        reiwa_date_str = reiwa_date_str.replace("令和", "").replace("年", "-").replace("月", "-").replace("日", "").replace(" ", "")
        parts = reiwa_date_str.split("-")
        if len(parts) == 3:
            year = 2018 + int(parts[0])  # 令和元年は2019年
            month = int(parts[1])
            day = int(parts[2])
            return datetime(year, month, day, tzinfo=timezone(timedelta(hours=9)))  # JST
    except:
        pass
    return datetime.now(timezone.utc)

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("診療報酬情報提供サービス｜更新履歴")
    fg.link(href="https://shinryohoshu.mhlw.go.jp/shinryohoshu/infoMenu/")
    fg.description("厚生労働省による診療報酬制度に関する最新情報")
    fg.language("ja")

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])
        entry.guid(item['link'], permalink=False)
        entry.pubDate(item['pubDate'])

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
    rows = page.locator("table tr")
    count = rows.count()
    print(f"📦 発見した行数: {count}")

    items = []

    for i in range(count):
        row = rows.nth(i)
        try:
            # 日付（1列目）
            raw_date = row.locator("td:nth-child(1)").inner_text().strip()
            pub_date = convert_reiwa_date(raw_date)

            # 内容（HTML付き）
            td2_html = row.locator("td:nth-child(2)").inner_html().strip()
            td2_text = row.locator("td:nth-child(2)").inner_text().strip()

            # 最初の行をタイトルに
            title = td2_text.split("\n")[0].strip()

            # 1つ目のリンクがあればそれを使用、なければ固定ページ
            first_link = row.locator("td:nth-child(2) a").first
            if first_link.count() > 0:
                link = first_link.get_attribute("href")
                if link and not link.startswith("http"):
                    link = "https://shinryohoshu.mhlw.go.jp" + link
            else:
                link = "https://shinryohoshu.mhlw.go.jp/shinryohoshu/infoMenu/"

            items.append({
                "title": title,
                "link": link,
                "description": td2_html,
                "pubDate": pub_date
            })
        except Exception as e:
            print(f"⚠ 行{i}でエラー: {e}")
            continue

    if not items:
        print("⚠ 抽出されたデータが空です。")

    rss_path = "rss_output/shinryohoshu.xml"
    generate_rss(items, rss_path)

    print(f"\n✅ RSSフィード生成完了！\n📄 保存先: {rss_path}")
    browser.close()
