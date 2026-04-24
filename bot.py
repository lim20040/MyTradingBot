import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, 
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)
from exchanges import get_combined_report

# --- [필독] 본인의 텔레그램 봇 토큰 입력 ---
TOKEN = "8235198849:AAG_EhtfSFihmtnaAmskdq1BfnyO0DAhiBY"

SET_SEED = 1
user_info = {"seed": 2000.0}

# 로그 설정 (Railway 로그에서 확인 가능)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 버튼 구성 (callback_data 오타 수정 완료)
    keyboard = [
        [InlineKeyboardButton("🕒 오늘 성과", callback_data='rep_today'),
         InlineKeyboardButton("📅 어제+오늘", callback_data='rep_2days')],
        [InlineKeyboardButton("🗓️ 이번 주", callback_data='rep_week'),
         InlineKeyboardButton("📊 이번 달", callback_data='rep_month')],
        [InlineKeyboardButton("🏆 올해 전체", callback_data='rep_year')],
        [InlineKeyboardButton("💰 시드 머니 설정", callback_data='set_seed_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (f"🤖 **OKX 트레이딩 매니저**\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"📍 기준 시드: `{user_info['seed']}` USDT\n"
           f"조회할 기간을 선택하세요.")
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith('rep_'):
        period = query.data.split('_')[1]
        result = await get_combined_report(period, user_info['seed'])
        await query.message.reply_text(result)
        # 리포트 출력 후 메뉴 다시 띄우기
        await start(update, context)

async def seed_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("💰 **변경할 시드 금액을 입력하세요 (숫자만):**")
    return SET_SEED

async def seed_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_info['seed'] = float(update.message.text)
        await update.message.reply_text(f"✅ 시드가 `{user_info['seed']}` USDT로 설정되었습니다.")
    except:
        await update.message.reply_text("❌ 숫자만 입력해주세요.")
        return SET_SEED
    await start(update, context)
    return ConversationHandler.END

if __name__ == '__main__':
    logger.info("봇 시작 중...")
    application = ApplicationBuilder().token(TOKEN).build()
    
    seed_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(seed_start, pattern='^set_seed_start$')],
        states={SET_SEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, seed_received)]},
        fallbacks=[]
    )
    
    application.add_handler(seed_conv)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("봇이 정상적으로 실행되었습니다.")
    application.run_polling()
