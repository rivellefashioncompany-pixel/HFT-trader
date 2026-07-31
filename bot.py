import os
import pytz
import asyncio
import MetaTrader5 as mt5
from datetime import datetime, time
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# WAKTU SESSION (GMT)
ASIA_START = time(1, 0)   # 01:00 GMT
ASIA_END = time(10, 0)    # 10:00 GMT
LONDON_START = time(8, 0) # 08:00 GMT
LONDON_END = time(17, 0)  # 17:00 GMT

def is_trading_hours():
    now = datetime.now(pytz.UTC).time()
    return (ASIA_START <= now <= ASIA_END) or (LONDON_START <= now <= LONDON_END)

def find_support_resistance(data, lookback=20):
    highs = data['high'].values
    lows = data['low'].values
    resistance = []
    support = []
    for i in range(lookback, len(data)-lookback):
        if highs[i] == max(highs[i-lookback:i+lookback]):
            resistance.append(highs[i])
        if lows[i] == min(lows[i-lookback:i+lookback]):
            support.append(lows[i])
    return support[-1] if support else None, resistance[-1] if resistance else None

def check_and_execute():
    if not is_trading_hours():
        return "⏸️ Di luar jam trading (Asia/London)"
    mt5.initialize()
    symbol = "EURUSD"
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
    df = pd.DataFrame(rates)
    support, resistance = find_support_resistance(df)
    price = mt5.symbol_info_tick(symbol).ask
    # Logika entry
    if price <= support * 1.001:
        return f"📈 ENTRY BUY di {price} (Support {support})"
    elif price >= resistance * 0.999:
        return f"📉 ENTRY SELL di {price} (Resistance {resistance})"
    return f"⏳ Menunggu sentuhan S/R | S:{support} R:{resistance}"

async def start(update, context):
    await update.message.reply_text("🤖 Bot S/R Aktif! Kirim /scan untuk cek")

async def scan(update, context):
    result = check_and_execute()
    await update.message.reply_text(result)

# SCHEDULER: Scan otomatis tiap 5 menit di jam trading
async def auto_scan(context: ContextTypes.DEFAULT_TYPE):
    if is_trading_hours():
        result = check_and_execute()
        await context.bot.send_message(chat_id=CHAT_ID, text=result)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    # Jadwalkan auto-scan tiap 5 menit
    job_queue = app.job_queue
    job_queue.run_repeating(auto_scan, interval=300, first=10)
    app.run_polling()

if __name__ == "__main__":
    main()
