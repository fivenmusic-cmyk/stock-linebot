import sqlite3
from datetime import datetime, date


def get_db():
    """連接資料庫"""
    conn = sqlite3.connect('stock_bot.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化資料庫，建立表格"""
    conn = get_db()
    cursor = conn.cursor()

    # 用戶表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_user_id TEXT UNIQUE NOT NULL,
            display_name TEXT,
            plan TEXT DEFAULT 'free',
            daily_queries INTEGER DEFAULT 0,
            last_query_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ 資料庫初始化完成")


def get_or_create_user(line_user_id, display_name=""):
    """取得或建立用戶"""
    conn = get_db()
    cursor = conn.cursor()

    # 查詢用戶
    cursor.execute(
        'SELECT * FROM users WHERE line_user_id = ?',
        (line_user_id,)
    )
    user = cursor.fetchone()

    if not user:
        # 新用戶
        cursor.execute(
            '''INSERT INTO users 
               (line_user_id, display_name, plan, daily_queries, last_query_date) 
               VALUES (?, ?, 'free', 0, ?)''',
            (line_user_id, display_name, str(date.today()))
        )
        conn.commit()
        print(f"✅ 新用戶建立: {line_user_id}")

        cursor.execute(
            'SELECT * FROM users WHERE line_user_id = ?',
            (line_user_id,)
        )
        user = cursor.fetchone()

    conn.close()
    return dict(user)


def check_query_limit(line_user_id):
    """
    檢查查詢次數限制
    回傳: (可以查詢, 剩餘次數, 方案)
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        'SELECT * FROM users WHERE line_user_id = ?',
        (line_user_id,)
    )
    user = cursor.fetchone()

    if not user:
        conn.close()
        return True, 3, 'free'

    user = dict(user)
    today = str(date.today())

    # 如果是新的一天，重置計數
    if user['last_query_date'] != today:
        cursor.execute(
            'UPDATE users SET daily_queries = 0, last_query_date = ? WHERE line_user_id = ?',
            (today, line_user_id)
        )
        conn.commit()
        user['daily_queries'] = 0

    conn.close()

    plan = user['plan']
    queries_used = user['daily_queries']

    # 免費版：每天 3 次
    if plan == 'free':
        remaining = 3 - queries_used
        can_query = remaining > 0
        return can_query, remaining, plan

    # 基礎版/專業版：無限
    return True, 999, plan


def increment_query_count(line_user_id):
    """增加查詢次數"""
    conn = get_db()
    today = str(date.today())

    conn.execute(
        '''UPDATE users 
           SET daily_queries = daily_queries + 1,
               last_query_date = ?
           WHERE line_user_id = ?''',
        (today, line_user_id)
    )
    conn.commit()
    conn.close()


def upgrade_user(line_user_id, plan):
    """升級用戶方案"""
    conn = get_db()
    conn.execute(
        'UPDATE users SET plan = ? WHERE line_user_id = ?',
        (plan, line_user_id)
    )
    conn.commit()
    conn.close()
    print(f"✅ 用戶 {line_user_id} 升級為 {plan}")


def get_user_info(line_user_id):
    """取得用戶資訊"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM users WHERE line_user_id = ?',
        (line_user_id,)
    )
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


# 測試
if __name__ == "__main__":
    init_db()
    print("測試用戶建立...")
    user = get_or_create_user("test_user_123", "測試用戶")
    print(f"用戶: {user}")

    can_query, remaining, plan = check_query_limit("test_user_123")
    print(f"可查詢: {can_query}, 剩餘: {remaining}, 方案: {plan}")