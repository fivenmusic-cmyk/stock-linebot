import schedule
import time
import threading
from linebot import LineBotApi
from linebot.models import TextSendMessage
from config import Config
from scraper import (
    scrape_limit_up_stocks,
    scrape_institution_buy,
    format_combined_report
)
from database import get_db


def get_paid_users():
    """取得所有付費用戶的 LINE ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT line_user_id FROM users WHERE plan IN ('basic', 'pro')"
    )
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


def send_daily_report():
    """每日盤前報告推播（付費版專屬）"""
    print("⏰ 開始產生每日盤前報告...")

    line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)

    # 爬取資料
    limit_stocks = scrape_limit_up_stocks()
    institution_stocks = scrape_institution_buy()
    report = format_combined_report(limit_stocks, institution_stocks)

    # 取得付費用戶
    paid_users = get_paid_users()

    if not paid_users:
        print("目前無付費用戶，跳過推播")
        return

    # 推播給所有付費用戶
    success = 0
    for user_id in paid_users:
        try:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text=f"📊 每日盤前報告自動推播\n\n{report}")
            )
            success += 1
            print(f"✅ 推播成功：{user_id[:8]}...")
        except Exception as e:
            print(f"❌ 推播失敗：{user_id[:8]}... 錯誤：{e}")

    print(f"推播完成！成功 {success}/{len(paid_users)} 人")


def run_scheduler():
    """啟動排程器"""
    # 每天早上 8:30 推播
    schedule.every().day.at("08:30").do(send_daily_report)

    # 測試用：每分鐘執行一次（之後關掉）
    # schedule.every(1).minutes.do(send_daily_report)

    print("✅ 排程器已啟動")
    print("📅 每天 08:30 自動推播盤前報告")

    while True:
        schedule.run_pending()
        time.sleep(30)  # 每30秒檢查一次


def start_scheduler_thread():
    """在背景執行排程器（不阻塞主程式）"""
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
    print("✅ 背景排程器已啟動")


# 測試用
if __name__ == "__main__":
    print("=== 測試立即推播 ===")
    send_daily_report()