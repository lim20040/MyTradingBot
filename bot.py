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
user_info = {"seed": 2000.0} # 기본 시드값

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 메뉴 구성: 오늘, 2일, 7일, 시드 설정
    keyboard = [
        [InlineKeyboardButton("📊 오늘 성과 (1일)", callback_data='rep_1'),
         InlineKeyboardButton("📅 어제+오늘 (2일)", callback_data='rep_2')],
        [InlineKeyboardButton("🗓️ 최근 일주일 (7일)", callback_data='rep_7')],
        [InlineKeyboardButton("💰 시드 머니 설정", callback_data='set_seed_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (f"🤖 **OKX 트레이딩 매니저**\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"📍 현재 기준 시드: `{user_info['seed']}` USDT\n"
           f"원하시는 항목을 선택하거나\n"
           f"`/report 7` 또는 `/report 2026-04-23`을 입력하세요.")
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context)

# 버튼 클릭 처리
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith('rep_'):
        days = query.data.split('_')[1]
        result = await get_combined_report(days, user_info['seed'])
        await query.message.reply_text(result)
        await show_main_menu(update, context)

# /report 명령어 처리 (예: /report 3, /report 2026-04-20)
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("💡 사용법: `/report 7` 또는 `/report 2026-04-23`", parse_mode='Markdown')
        return
    
    query = context.args[0]
    result = await get_combined_report(query, user_info['seed'])
    await update.message.reply_text(result)

# 시드 머니 설정 대화
async def seed_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("💰 **새로운 시드 금액을 입력하세요 (숫자만):**")
    return SET_SEED

async def seed_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_info['seed'] = float(update.message.text)
        await update.message.reply_text(f"✅ 시드가 `{user_info['seed']}` USDT로 설정되었습니다.")
    except ValueError:
        await update.message.reply_text("❌ 숫자만 입력 가능합니다. 다시 시도해주세요.")
        return SET_SEED
    
    await show_main_menu(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("취소되었습니다.")
    await show_main_menu(update, context)
    return ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # 시드 설정 대화 핸들러
    seed_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(seed_start, pattern='^set_seed_start$')],
        states={SET_SEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, seed_received)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(seed_conv)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('report', report_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    application.run_polling()
