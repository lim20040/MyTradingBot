import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from exchanges import get_combined_report  # exchanges.py의 함수 호출

# --- 텔레그램 봇 토큰 설정 ---
TOKEN = "8235198849:AAG_EhtfSFihmtnaAmskdq1BfnyO0DAhiBY"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 인자가 없는 경우 (그냥 /report만 친 경우)
    if not context.args:
        await update.message.reply_text("사용법: /report [일수] 또는 [YYYY-MM-DD]\n예) /report 1\n예) /report 2026-04-16")
        return

    query = context.args[0]
    await update.message.reply_text(f"⏳ {query} 기간의 거래 내역을 불러오는 중...")

    try:
        # 숫자든 날짜든 일단 exchanges.py로 그대로 넘겨줍니다.
        result = await get_combined_report(query)
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ 에러 발생: {str(e)}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    report_handler = CommandHandler('report', report)
    application.add_handler(report_handler)
    
    application.run_polling()
