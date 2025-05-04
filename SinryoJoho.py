from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re

BASE_URL = "https://shinryohoshu.mhlw.go.jp/shinryohoshu/"
DEFAULT_LINK = "https://shinryohoshu.mhlw.go.jp/shinryohoshu/infoMenu/"

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("MHLW｜診療報酬改定関連 更新情報")
    fg.link(href=DEFAULT_LINK)
    fg.description("厚生労働省保険局『診療報酬改定関連』ページの更新履歴")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])

        # GUIDはユニークにする（リンク＋日付で）
        guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
        entry.guid(guid_value, permalink=False)

        entry.pubDate(item['pub_date'])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")

def extract_items(page):
    selector = "body > table > tbody > tr > td:nth-child(1) > div:nth-child(5) > p:nth-child(2) > table > tbody > tr"
    rows = page.locator(selector)
    count = rows.count()
    print(f"📦 発見した更新情報行数: {count}")

    items = []

    for i in range(count):
        row = rows.nth(i)
        try:
            date_text = row.locator("td:nth-child(1)").inner_text().strip()
            content_html = row.locator("td:nth-child(2)").inner_html().strip()
            a_links = row.locator("td:nth-child(2) a")
            first_link = None
            if a_links.count() > 0:
                href = a_links.first.get_attribute("href")
                if href:
                    first_link = urljoin(BASE_URL, href)
            else:
                first_link = DEFAULT_LINK

            # description内の相対パスを絶対パスに変換
            content_html = content_html.replace('href="/', f'href="{BASE_URL}')

            try:
                pub_date = parse_date_text(date_text)
            except Exception as e:
                print(f"⚠ 日付の変換に失敗: {e}")
                pub_date = datetime.now(timezone.utc)

            items.append({
                "title": f"更新情報: {date_text}",
                "link": first_link,
                "description": content_html,  # CDATA不要
                "pub_date": pub_date
            })

        except Exception as e:
            print(f"⚠ 行{i+1}の解析に失敗: {e}")
            continue

    return items

def parse_date_text(text):
    text = text.replace("　", " ").replace("\u3000", " ")
    match = re.search(r"令和\s*(\d)年\s*(\d{1,2})月\s*(\d{1,2})日?", text)
    if match:
        r_year, month, day = map(int, match.groups())
        year = 2018 + r_year  # 令和元年＝2019年
        return datetime(year, month, day, tzinfo=timezone.utc)
    else:
        raise ValueError(f"日付変換失敗: {text}")

# ===== 実行ブロック =====
with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")
        page.goto(DEFAULT_LINK, timeout=30000)
        page.wait_for_load_state("load", timeout=30000)
    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。")
        browser.close()
        exit()

    print("▶ 更新情報を抽出しています...")
    items = extract_items(page)

    if not items:
        print("⚠ 抽出できた更新情報がありません。HTML構造が変わっている可能性があります。")

    rss_path = "rss_output/mhlw_shinryohoshu.xml"
    generate_rss(items, rss_path)
    browser.close()
