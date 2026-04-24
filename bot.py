import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, 
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)
from exchanges import get_combined_report

# --- 설정 ---
TOKEN = "8235198849:AAG_EhtfSFihmtnaAmskdq1BfnyO0DAhiBY"
SET_SEED = 1
user_info = {"seed": 2000.0} # 어제 시작한 시드값

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 요청하신 버튼 구성: 오늘, 어제+오늘, 이번주, 이번달, 올해
    keyboard = [
        [InlineKeyboardButton("🕒 오늘 성과", callback_query_data='rep_today'),
         InlineKeyboardButton("📅 어제+오늘", callback_query_data='rep_2days')],
        [InlineKeyboardButton("🗓️ 이번 주", callback_query_data='rep_week'),
         InlineKeyboardButton("📊 이번 달", callback_query_data='rep_month')],
        [InlineKeyboardButton("🏆 올해 전체", callback_query_data='rep_year')],
        [InlineKeyboardButton("💰 시드 머니 설정", callback_query_data='set_seed_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (f"🤖 **OKX 트레이딩 매니저**\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"📍 기준 시드: `{user_info['seed']}` USDT\n"
           f"조회할 기간을 선택하세요.")
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith('rep_'):
        period = query.data.split('_')[1]
        result = await get_combined_report(period, user_info['seed'])
        await query.message.reply_text(result)
        # 리포트 출력 후 다시 메뉴 보여주기
        await start(update, context)

# --- 시드 설정 대화 로직 ---
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
    application = ApplicationBuilder().token(TOKEN).build()
    
    seed_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(seed_start, pattern='^set_seed_start$')],
        states={SET_SEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, seed_received)]},
        fallbacks=[]
    )
    
    application.add_handler(seed_conv)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    application.run_polling()
