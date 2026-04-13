import os
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from exchanges import get_combined_report

BOT_TOKEN = os.environ.get("8235198849:AAG_EhtfSFihmtnaAmskdq1BfnyO0DAhiBY")
ALLOWED_USER_ID = int(os.environ.get("1801734156", "0"))  # 본인 텔레그램 ID

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ALLOWED_USER_ID and user_id != ALLOWED_USER_ID:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return

    # 기간 파싱
    try:
        days = int(context.args[0]) if context.args else 7
    except (ValueError, IndexError):
        await update.message.reply_text("사용법: /report [일수]\n예) /report 50")
        return

    await update.message.reply_text(f"⏳ {days}일 동안의 거래 내역을 불러오는 중...")

    try:
        text = await get_combined_report(days)
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류 발생: {str(e)}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("report", report))
    print("봇 시작됨!")
    app.run_polling()

if __name__ == "__main__":
    main()