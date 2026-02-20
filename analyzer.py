import yfinance as yf
import pandas as pd
import numpy as np


def get_stock_data(stock_id, period="3mo"):
    """
    取得股票K線資料
    stock_id: 台股代號，例如 "2330"
    """
    ticker = f"{stock_id}.TW"
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    
    if hist.empty:
        # 嘗試上櫃股票
        ticker = f"{stock_id}.TWO"
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
    
    return hist, stock


def calculate_indicators(hist):
    """計算技術指標"""
    if hist.empty or len(hist) < 20:
        return None
    
    close = hist['Close']
    high = hist['High']
    low = hist['Low']
    volume = hist['Volume']
    
    # 均線
    ma5  = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    
    # RSI(14)
    delta = close.diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs    = gain / loss
    rsi   = 100 - (100 / (1 + rs))
    
    # KD(9)
    low9  = low.rolling(9).min()
    high9 = high.rolling(9).max()
    rsv   = (close - low9) / (high9 - low9) * 100
    k     = rsv.ewm(com=2).mean()
    d     = k.ewm(com=2).mean()
    
    # 近期高低點（20日）
    recent_high = high.rolling(20).max().iloc[-1]
    recent_low  = low.rolling(20).min().iloc[-1]
    
    # 成交量均量
    vol_ma5 = volume.rolling(5).mean()
    
    return {
        'close':       round(close.iloc[-1], 2),
        'ma5':         round(ma5.iloc[-1], 2),
        'ma20':        round(ma20.iloc[-1], 2),
        'ma60':        round(ma60.iloc[-1] if len(hist) >= 60 else 0, 2),
        'rsi':         round(rsi.iloc[-1], 1),
        'k':           round(k.iloc[-1], 1),
        'd':           round(d.iloc[-1], 1),
        'recent_high': round(recent_high, 2),
        'recent_low':  round(recent_low, 2),
        'volume':      int(volume.iloc[-1]),
        'vol_ma5':     int(vol_ma5.iloc[-1]),
    }


def analyze_stock(stock_id):
    """
    完整個股分析
    回傳進出場參考區間 + 技術指標
    """
    try:
        hist, stock = get_stock_data(stock_id)
        
        if hist.empty:
            return None
            
        ind = calculate_indicators(hist)
        if not ind:
            return None
        
        close       = ind['close']
        ma5         = ind['ma5']
        ma20        = ind['ma20']
        ma60        = ind['ma60']
        rsi         = ind['rsi']
        k           = ind['k']
        d           = ind['d']
        recent_high = ind['recent_high']
        recent_low  = ind['recent_low']
        
        # ===== 多空判斷 =====
        bull_signals = 0
        bear_signals = 0
        
        if close > ma5:  bull_signals += 1
        else:            bear_signals += 1
            
        if close > ma20: bull_signals += 1
        else:            bear_signals += 1
            
        if ma5 > ma20:   bull_signals += 1
        else:            bear_signals += 1
            
        if rsi > 50:     bull_signals += 1
        else:            bear_signals += 1
            
        if k > d:        bull_signals += 1
        else:            bear_signals += 1
        
        if bull_signals >= 4:
            trend = "強勢多方 🚀"
        elif bull_signals == 3:
            trend = "偏多 📈"
        elif bear_signals >= 4:
            trend = "強勢空方 🔻"
        elif bear_signals == 3:
            trend = "偏空 📉"
        else:
            trend = "盤整觀望 ➡️"
        
        # ===== 進出場參考區間 =====
        # 支撐：MA5 和 MA20 取較高者（更貼近現價）
        support = max(ma5, ma20)
        support = round(support, 1)
        
        # 進場區間：支撐附近
        entry_low  = round(support * 0.99, 1)
        entry_high = round(support * 1.01, 1)
        
        # 停損：支撐再下 3%
        stop_loss = round(support * 0.97, 1)
        
        # 目標：近期高點或 MA20 上方 5%
        target = round(max(recent_high, ma20 * 1.05), 1)
        
        # 風險報酬比
        entry_mid = round((entry_low + entry_high) / 2, 1)
        risk      = round(entry_mid - stop_loss, 1)
        reward    = round(target - entry_mid, 1)
        rr        = round(reward / risk, 1) if risk > 0 else 0
        
        return {
            'stock_id':   stock_id,
            'close':      close,
            'trend':      trend,
            'ma5':        ma5,
            'ma20':       ma20,
            'ma60':       ma60,
            'rsi':        rsi,
            'k':          k,
            'd':          d,
            'support':    support,
            'entry_low':  entry_low,
            'entry_high': entry_high,
            'stop_loss':  stop_loss,
            'target':     target,
            'rr':         rr,
            'vol_ratio':  round(ind['volume'] / ind['vol_ma5'], 1),
        }
        
    except Exception as e:
        print(f"分析失敗: {e}")
        return None


def format_analysis_report(stock_id, name=""):
    """格式化分析報告"""
    result = analyze_stock(stock_id)
    
    if not result:
        return f"❌ 查無 {stock_id} 資料，請確認股票代號"
    
    label = f"{name}({stock_id})" if name else stock_id
    
    msg  = f"📊 {label} 技術分析\n"
    msg += "=" * 22 + "\n\n"
    
    msg += f"💰 現價：{result['close']}\n"
    msg += f"📈 趨勢：{result['trend']}\n\n"
    
    msg += "📉 技術指標\n"
    msg += f"  MA5：{result['ma5']}\n"
    msg += f"  MA20：{result['ma20']}\n"
    if result['ma60'] > 0:
        msg += f"  MA60：{result['ma60']}\n"
    msg += f"  RSI：{result['rsi']}\n"
    msg += f"  KD：{result['k']} / {result['d']}\n"
    msg += f"  量比：{result['vol_ratio']}x\n\n"
    
    msg += "🎯 參考區間（技術計算）\n"
    msg += f"  進場：{result['entry_low']}～{result['entry_high']}\n"
    msg += f"  停損：{result['stop_loss']}\n"
    msg += f"  目標：{result['target']}\n"
    msg += f"  風報比：1:{result['rr']}\n\n"
    
    msg += "⚠️ 以上為技術指標自動計算\n"
    msg += "非投資建議，請自行判斷"
    
    return msg


# 測試
if __name__ == "__main__":
    print("=== 測試台積電 2330 ===")
    report = format_analysis_report("2330", "台積電")
    print(report)
    
    print("\n=== 測試聯發科 2454 ===")
    report = format_analysis_report("2454", "聯發科")
    print(report)