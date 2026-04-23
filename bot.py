import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, 
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)
from exchanges import get_combined_report

# --- 설정 ---
TOKEN = "8235198849:AAG_EhtfSFihmtnaAmskdq1BfnyO0DAhiBY"
SET_SEED = 1  # 대화 상태값

# 임시 메모리 저장소 (재배포 시 초기화됨)
user_info = {"seed": 1000.0}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- 메인 메뉴 표시 함수 ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 오늘 성과 (1일)", callback_data='rep_1'),
         InlineKeyboardButton("📅 어제+오늘 (2일)", callback_data='rep_2')],
        [InlineKeyboardButton("📆 최근 일주일 (7일)", callback_data='rep_7')],
        [InlineKeyboardButton("💰 시드 머니 설정", callback_data='set_seed_start')],
        [InlineKeyboardButton("📈 현재 수익 현황", callback_data='total_status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (f"🤖 **OKX 트레이딩 매니저**\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"📍 현재 기준 시드: `{user_info['seed']}` USDT\n"
           f"원하시는 항목을 선택하세요.")
    
    # 메시지가 신규인지, 기존 메시지 수정인지 판단
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

# --- /start 명령어 ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context)

# --- 버튼 클릭 처리 ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith('rep_'):
        days = query.data.split('_')[1]
        await query.message.reply_text(f"⏳ {days}일간의 내역을 분석 중입니다...")
        result = await get_combined_report(days, user_info['seed'])
        await query.message.reply_text(result)
        await show_main_menu(update, context) # 결과 보고 메뉴 다시 띄우기

    elif query.data == 'total_status':
        result = await get_combined_report("1", user_info['seed'])
        await query.message.reply_text(f"💰 **현재 수익 현황**\n{result}")
        await show_main_menu(update, context)

# --- 시드 설정 대화 (Conversation) ---
async def seed_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("💰 **새로운 시드 금액을 숫자만 입력해주세요.**\n예) 2500\n(취소하려면 /cancel)")
    return SET_SEED

async def seed_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_seed = float(update.message.text)
        user_info['seed'] = new_seed
        await update.message.reply_text(f"✅ 시드가 `{new_seed}` USDT로 변경되었습니다.")
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
    
    # 시드 설정을 위한 대화 핸들러 등록
    seed_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(seed_start, pattern='^set_seed_start$')],
        states={SET_SEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, seed_received)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(seed_conv)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    application.run_polling()
