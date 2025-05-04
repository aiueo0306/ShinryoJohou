from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def convert_japanese_date(jp_date):
    match = re.match(r"令和\s*(\d+)年\s*(\d+)月\s*(\d+)日", jp_date)
    if not match:
        return datetime.now(timezone.utc)
    year = 2018 + int(match.group(1))  # 令和元年＝2019年
    month = int(match.group(2))
    day = int(match.group(3))
    return datetime(year, month, day, tzinfo=timezone.utc)

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
        entry.description(f"<![CDATA[{item['description']}]]>")
        entry.guid(item['link'], permalink=False)
        entry.pubDate(item['pubDate'])

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
    selector = "body > table > tbody > tr > td:nth-child(1) > div:nth-child(5) > p:nth-child(2) > table > tbody > tr"
    rows = page.locator(selector)
    count = rows.count()
    print(f"📦 発見した更新情報行数: {count}")

    items = []

    for i in range(count):
        row = rows.nth(i)
        try:
            date_text = row.locator("td:nth-child(1)").inner_text(timeout=3000).strip()
            html_content = row.locator("td:nth-child(2)").inner_html(timeout=3000).strip()

            # 複数のリンクのうちPDFを優先
            link_elements = row.locator("td:nth-child(2) a")
            link_count = link_elements.count()
            file_link = "https://shinryohoshu.mhlw.go.jp/shinryohoshu/infoMenu/"  # fallback

            for j in range(link_count):
                href = link_elements.nth(j).get_attribute("href")
                if href and href.endswith(".pdf"):
                    file_link = "https://shinryohoshu.mhlw.go.jp" + href
                    break

            items.append({
                "title": f"更新情報: {date_text}",
                "link": file_link,
                "description": html_content,
                "pubDate": convert_japanese_date(date_text)
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
