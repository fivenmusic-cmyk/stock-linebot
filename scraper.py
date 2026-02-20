import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def create_driver():
    """建立 Chrome 瀏覽器（背景執行）"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-logging')
    options.add_argument('--log-level=3')
    options.add_argument('--silent')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def scrape_goodinfo(url, label="", has_rank=False):
    """
    通用爬蟲
    has_rank=True : 有排名欄位（法人買最多）
    has_rank=False: 無排名欄位（連續漲停、法人連買）
    """
    print(f"啟動瀏覽器爬取{label}...")
    driver = create_driver()
    stocks = []

    try:
        driver.get(url)
        time.sleep(8)

        table = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "tblStockList"))
        )
        print(f"✅ 找到表格！")

        rows = table.find_elements(By.TAG_NAME, "tr")
        print(f"共 {len(rows)} 行資料")

        for i, row in enumerate(rows):
            if i == 0:
                continue

            row_text = row.text.strip()
            if not row_text:
                continue

            parts = row_text.split()

            if has_rank:
                # 格式：排名 代號 名稱 股價 漲跌 漲幅 ...
                if len(parts) >= 4:
                    rank = parts[0]
                    code = parts[1]
                    name = parts[2]
                    price = parts[3]
                    change = parts[4] if len(parts) > 4 else 'N/A'
                    change_pct = parts[5] if len(parts) > 5 else 'N/A'

                    if rank.isdigit() and (code.isdigit() or code.startswith('00')):
                        stocks.append({
                            'code': code,
                            'name': name,
                            'price': price,
                            'change': change,
                            'change_pct': change_pct,
                            'days': 'N/A',
                        })
                        print(f"✅ {code} {name} 價:{price} {change_pct}%")
            else:
                # 格式：代號 名稱 股價 漲跌 漲幅 ...
                if len(parts) >= 3:
                    code = parts[0]
                    name = parts[1]
                    price = parts[2]
                    change = parts[3] if len(parts) > 3 else 'N/A'
                    change_pct = parts[4] if len(parts) > 4 else 'N/A'
                    days = parts[6] if len(parts) > 6 else 'N/A'

                    if code.isdigit() and len(code) == 4:
                        stocks.append({
                            'code': code,
                            'name': name,
                            'price': price,
                            'change': change,
                            'change_pct': change_pct,
                            'days': days,
                        })
                        print(f"✅ {code} {name} 價:{price}")

    except Exception as e:
        print(f"❌ 爬取{label}失敗: {e}")

    finally:
        driver.quit()
        print(f"完成，共爬到 {len(stocks)} 筆")

    return stocks


def scrape_limit_up_stocks():
    """爬取連續漲停股"""
    url = (
        "https://goodinfo.tw/tw/StockList.asp"
        "?MARKET_CAT=%E6%99%BA%E6%85%A7%E9%81%B8%E8%82%A1"
        "&INDUSTRY_CAT=%E9%80%A3%E7%BA%8C%E5%A4%9A%E6%97%A5%E6%BC%B2%E5%81%9C"
        "%40%40%E9%80%A3%E7%BA%8C%E6%BC%B2%E5%81%9C%28%E6%88%96%E6%BC%B210%25%29"
        "%40%40%E9%80%A3%E7%BA%8C%E5%A4%9A%E6%97%A5%E6%BC%B2%E5%81%9C"
    )
    return scrape_goodinfo(url, label="連續漲停股", has_rank=False)


def scrape_institution_buy():
    """爬取三大法人買最多（當日排行）"""
    url = (
        "https://goodinfo.tw/tw/StockList.asp"
        "?MARKET_CAT=%E7%86%B1%E9%96%80%E6%8E%92%E8%A1%8C"
        "&INDUSTRY_CAT=%E4%B8%89%E5%A4%A7%E6%B3%95%E4%BA%BA%E7%B4%AF%E8%A8%88%E8%B2%B7%E8%B6%85%E5%BC%B5%E6%95%B8"
        "+%E2%80%93+%E7%95%B6%E6%97%A5%40%40%E4%B8%89%E5%A4%A7%E6%B3%95%E4%BA%BA%E7%B4%AF%E8%A8%88%E8%B2%B7%E8%B6%85"
        "%40%40%E4%B8%89%E5%A4%A7%E6%B3%95%E4%BA%BA%E8%B2%B7%E8%B6%85%E5%BC%B5%E6%95%B8"
        "+%E2%80%93+%E7%95%B6%E6%97%A5"
    )
    return scrape_goodinfo(url, label="三大法人買最多", has_rank=True)


def scrape_institution_continuous_buy():
    """爬取三大法人連續買超"""
    url = (
        "https://goodinfo.tw/tw/StockList.asp"
        "?MARKET_CAT=%E6%99%BA%E6%85%A7%E9%81%B8%E8%82%A1"
        "&INDUSTRY_CAT=%E4%B8%89%E5%A4%A7%E6%B3%95%E4%BA%BA%E9%80%A3%E8%B2%B7"
        "+%E2%80%93+%E6%97%A5%40%40%E4%B8%89%E5%A4%A7%E6%B3%95%E4%BA%BA"
        "%E9%80%A3%E7%BA%8C%E8%B2%B7%E8%B6%85%40%40%E4%B8%89%E5%A4%A7"
        "%E6%B3%95%E4%BA%BA%E9%80%A3%E7%BA%8C%E8%B2%B7%E8%B6%85"
        "+%E2%80%93+%E6%97%A5"
    )
    return scrape_goodinfo(url, label="法人連續買", has_rank=False)

# ==================== 訊息格式化 ====================

def format_daily_report(stocks):
    """連續漲停報告"""
    if not stocks:
        return "😔 今日無連續漲停股資料"

    msg = "🔥 今日連續漲停精選\n"
    msg += "=" * 20 + "\n"

    for i, s in enumerate(stocks, 1):
        msg += f"\n{i}. {s['name']} ({s['code']})\n"
        msg += f"   💰 股價: {s['price']}\n"
        msg += f"   📈 漲幅: {s['change_pct']}%\n"
        msg += f"   🔥 連續: {s['days']}日\n"

    msg += "\n⚠️ 僅供參考，投資請謹慎"
    return msg


def format_institution_report(stocks, title="法人買超"):
    """法人買超報告"""
    if not stocks:
        return f"😔 今日無{title}資料"

    msg = f"🏦 {title}精選\n"
    msg += "=" * 20 + "\n"

    for i, s in enumerate(stocks[:10], 1):
        msg += f"\n{i}. {s['name']} ({s['code']})\n"
        msg += f"   💰 股價: {s['price']}\n"
        msg += f"   📈 漲跌: {s['change_pct']}%\n"

    msg += "\n⚠️ 僅供參考，投資請謹慎"
    return msg


def format_combined_report(limit_stocks, institution_stocks):
    """每日盤前完整報告"""
    msg = "📊 每日盤前精選報告\n"
    msg += "=" * 20 + "\n\n"

    msg += "🔥 連續漲停股 Top 5\n"
    if limit_stocks:
        for i, s in enumerate(limit_stocks[:5], 1):
            msg += f"{i}. {s['name']}({s['code']}) "
            msg += f"{s['price']} {s['change_pct']}%\n"
    else:
        msg += "今日無資料\n"

    msg += "\n"

    msg += "🏦 法人買超 Top 5\n"
    if institution_stocks:
        for i, s in enumerate(institution_stocks[:5], 1):
            msg += f"{i}. {s['name']}({s['code']}) "
            msg += f"{s['price']} {s['change_pct']}%\n"
    else:
        msg += "今日無資料\n"

    msg += "\n⚠️ 僅供參考，投資請謹慎"
    return msg


# ==================== 測試 ====================
if __name__ == "__main__":
    print("=== 測試法人連續買 ===")
    stocks = scrape_institution_continuous_buy()
    print(format_institution_report(stocks, "法人連續買"))