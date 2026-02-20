from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from config import Config
from scraper import (
    scrape_limit_up_stocks,
    scrape_institution_buy,
    scrape_institution_continuous_buy,
    format_daily_report,
    format_institution_report,
    format_combined_report
)
from database import (
    init_db,
    get_or_create_user,
    check_query_limit,
    increment_query_count,
    get_user_info
)
from analyzer import format_analysis_report
from scheduler import start_scheduler_thread

# ==================== 初始化 ====================
app = Flask(__name__)
line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)
init_db()
start_scheduler_thread()


def handle_query(event, scrape_func, format_func, format_args=None):
    """通用查詢處理（含次數限制）"""
    user_id = event.source.user_id
    get_or_create_user(user_id)
    can_query, remaining, plan = check_query_limit(user_id)

    if not can_query:
        msg = (
            "⚠️ 今日免費查詢額度已用完！\n\n"
            "免費版：每天 3 次查詢\n\n"
            "🔓 升級方案：\n"
            "💵 基礎版 NT$199/月\n"
            "   → 無限查詢\n"
            "   → 個股技術分析\n\n"
            "💎 專業版 NT$499/月\n"
            "   → 基礎版全部功能\n"
            "   → 每日盤前自動推播\n"
            "   → 智能選股\n\n"
            "輸入「升級」查看詳情"
        )
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=msg)
        )
        return

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text=f"🔍 查詢中，請稍等約 15 秒...\n"
                 f"{'今日剩餘：' + str(remaining-1) + ' 次' if plan == 'free' else '（無限查詢）'}"
        )
    )

    stocks = scrape_func()
    report = format_func(stocks, format_args) if format_args else format_func(stocks)
    line_bot_api.push_message(event.source.user_id, TextSendMessage(text=report))

    if plan == 'free':
        increment_query_count(user_id)


# ==================== Webhook ====================
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


# ==================== 訊息處理 ====================
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_message = event.message.text.strip()
    user_id = event.source.user_id
    print(f"收到訊息: {user_message} 來自: {user_id[:8]}...")

    get_or_create_user(user_id)

    # ===== 個股查詢（4位數股票代號）=====
    if user_message.isdigit() and len(user_message) == 4:
        can_query, remaining, plan = check_query_limit(user_id)

        if not can_query:
            msg = (
                "⚠️ 今日免費查詢額度已用完！\n\n"
                "免費版：每天 3 次查詢\n\n"
                "輸入「升級」查看付費方案"
            )
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=msg)
            )
            return

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"🔍 分析 {user_message} 中\n"
                     f"請稍等約 5 秒...\n"
                     f"{'今日剩餘：' + str(remaining-1) + ' 次' if plan == 'free' else '（無限查詢）'}"
            )
        )

        report = format_analysis_report(user_message)
        line_bot_api.push_message(user_id, TextSendMessage(text=report))

        if plan == 'free':
            increment_query_count(user_id)

    # ===== 連續漲停 =====
    elif user_message in ['漲停', '連續漲停', '漲停股']:
        handle_query(
            event,
            scrape_limit_up_stocks,
            format_daily_report
        )

    # ===== 法人買最多 =====
    elif user_message in ['法人', '法人買超', '外資']:
        handle_query(
            event,
            scrape_institution_buy,
            format_institution_report,
            format_args="法人買最多"
        )

    # ===== 法人連續買 =====
    elif user_message in ['法人連買', '連續買超', '法人一直買']:
        handle_query(
            event,
            scrape_institution_continuous_buy,
            format_institution_report,
            format_args="法人連續買"
        )

    # ===== 每日完整報告 =====
    elif user_message in ['今日報告', '盤前報告', '報告', '每日報告']:
        user_info = get_user_info(user_id)
        plan = user_info['plan'] if user_info else 'free'

        if plan == 'free':
            msg = (
                "📊 每日完整盤前報告\n"
                "此功能需要升級方案\n\n"
                "💵 基礎版 NT$199/月\n"
                "💎 專業版 NT$499/月\n\n"
                "輸入「升級」查看詳情\n\n"
                "💡 免費版可分別查詢：\n"
                "🔥 漲停\n"
                "🏦 法人\n"
                "🔢 股票代號（如：2330）"
            )
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=msg)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="📊 產生今日盤前報告中\n請稍等約 30 秒...")
            )
            limit_stocks = scrape_limit_up_stocks()
            institution_stocks = scrape_institution_buy()
            report = format_combined_report(limit_stocks, institution_stocks)
            line_bot_api.push_message(user_id, TextSendMessage(text=report))

    # ===== 查看我的方案 =====
    elif user_message in ['我的方案', '方案', '我的帳號', '帳號']:
        user_info = get_user_info(user_id)
        if user_info:
            plan_names = {
                'free': '免費版',
                'basic': '基礎版',
                'pro': '專業版'
            }
            plan_name = plan_names.get(user_info['plan'], '免費版')
            today_queries = user_info['daily_queries']

            msg = (
                f"👤 你的帳號資訊\n"
                f"{'=' * 20}\n\n"
                f"方案：{plan_name}\n"
            )

            if user_info['plan'] == 'free':
                msg += (
                    f"今日查詢：{today_queries}/3 次\n"
                    f"剩餘：{3 - today_queries} 次\n\n"
                    f"💡 升級享無限查詢！\n"
                    f"輸入「升級」查看方案"
                )
            else:
                msg += "查詢次數：無限制 ✅\n"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=msg)
            )

    # ===== 升級方案說明 =====
    elif user_message in ['升級', '訂閱', '付費', '價格']:
        msg = (
            "💰 升級方案\n"
            "=" * 20 + "\n\n"
            "🆓 免費版（目前）\n"
            "• 每天 3 次查詢\n"
            "• 個股技術分析\n"
            "• 連續漲停查詢\n\n"
            "💵 基礎版 NT$199/月\n"
            "• 無限次查詢\n"
            "• 個股完整技術分析\n"
            "• 進出場參考區間\n"
            "• 法人買超資料\n\n"
            "💎 專業版 NT$499/月\n"
            "• 基礎版所有功能\n"
            "• 每日盤前自動推播\n"
            "• 法人連續買超分析\n"
            "• 每日完整報告\n\n"
            "📩 升級請聯繫：\n"
            "（填入你的聯絡方式）"
        )
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=msg)
        )

    # ===== 選單/說明 =====
    elif user_message in ['你好', 'hi', 'hello', 'Hi', 'Hello',
                          '哈囉', '選單', 'menu', '?', '？', '幫助', '說明']:
        user_info = get_user_info(user_id)
        plan = user_info['plan'] if user_info else 'free'
        plan_names = {'free': '免費版', 'basic': '基礎版', 'pro': '專業版'}
        plan_name = plan_names.get(plan, '免費版')

        reply = (
            f"👋 你好！我是股票精靈！\n"
            f"目前方案：{plan_name}\n\n"
            "📌 可用指令：\n\n"
            "🔢 輸入股票代號\n"
            "→ 例如：2330、2454\n"
            "→ 技術分析＋進出場參考\n\n"
            "🔥 漲停 → 連續漲停股\n\n"
            "🏦 法人 → 今日法人買超\n\n"
            "📈 法人連買 → 法人連續買超\n\n"
            "📊 今日報告 → 完整盤前報告\n"
            "（基礎版以上）\n\n"
            "👤 我的方案 → 查看帳號資訊\n\n"
            "💰 升級 → 查看付費方案\n\n"
            "⚠️ 資料來源：Goodinfo＋Yahoo\n"
            "僅供參考，投資請謹慎"
        )
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )

    # ===== 其他訊息 =====
    else:
        reply = (
            "📌 可用指令：\n"
            "🔢 股票代號（如：2330）\n"
            "🔥 漲停\n"
            "🏦 法人\n"
            "📈 法人連買\n"
            "📊 今日報告\n"
            "👤 我的方案\n"
            "💰 升級\n\n"
            "輸入「你好」查看完整說明"
        )
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )


# ==================== 首頁 ====================
@app.route("/")
def home():
    return "股票精靈 LINE Bot is running! 🚀"


# ==================== 啟動 ====================
if __name__ == "__main__":
    app.run(
        host='0.0.0.0',
        port=Config.PORT,
        debug=Config.DEBUG
    )