import os
import cv2
import numpy as np
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "7566138243:AAFR9ajzet5WpIDhiWdeipOLGXB23kQGH50"
CHANNEL_USERNAME = "p2busdt"

user_subscriptions = set()
user_states = {}

# التحقق من الاشتراك
async def is_user_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# قائمة الفلاتر
FILTERS_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("📝 1. رسم بالقلم الرصاص", callback_data="pencil")],
    [InlineKeyboardButton("⚫ 2. أبيض وأسود", callback_data="bw")],
    [InlineKeyboardButton("🧒 3. كارتون", callback_data="cartoon")],
    [InlineKeyboardButton("😊 4. تصفية البشرة", callback_data="smooth")],
    [InlineKeyboardButton("🔁 إعادة اختيار", callback_data="back")]
])

# بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_subscriptions:
        subscribed = await is_user_subscribed(context.bot, user_id)
        if not subscribed:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}")],
                [InlineKeyboardButton("✅ اشتركت، اضغط هنا للمتابعة", callback_data="restart")]
            ])
            await update.message.reply_text(
                "🔒 لاستخدام هذا البوت، يجب أولاً الاشتراك في القناة:",
                reply_markup=keyboard
            )
            return
        user_subscriptions.add(user_id)

    await update.message.reply_text("📸 أرسل صورة وسأعرض عليك مجموعة من الفلاتر!")

# عند استقبال صورة
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_subscriptions:
        subscribed = await is_user_subscribed(context.bot, user_id)
        if not subscribed:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}")],
                [InlineKeyboardButton("✅ اشتركت، اضغط هنا للمتابعة", callback_data="restart")]
            ])
            await update.message.reply_text(
                "🔒 لاستخدام هذا البوت، يجب أولاً الاشتراك في القناة:",
                reply_markup=keyboard
            )
            return

    photo_file = await update.message.photo[-1].get_file()
    image_path = f"user_{user_id}.jpg"
    await photo_file.download_to_drive(image_path)
    user_states[user_id] = image_path

    await update.message.reply_text("ماذا تريد أن أفعل بالصورة؟", reply_markup=FILTERS_KEYBOARD)

# الفلاتر
def apply_pencil_sketch(image_path):
    img = cv2.imread(image_path)
    gray, sketch = cv2.pencilSketch(img, sigma_s=60, sigma_r=0.07, shade_factor=0.05)
    output_path = image_path.replace(".jpg", "_pencil.jpg")
    cv2.imwrite(output_path, sketch)
    return output_path

def apply_black_white(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    output_path = image_path.replace(".jpg", "_bw.jpg")
    cv2.imwrite(output_path, gray)
    return output_path

def apply_cartoon(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)
    edges = cv2.adaptiveThreshold(gray, 255,
                                  cv2.ADAPTIVE_THRESH_MEAN_C,
                                  cv2.THRESH_BINARY, 9, 9)
    color = cv2.bilateralFilter(img, 9, 250, 250)
    cartoon = cv2.bitwise_and(color, color, mask=edges)
    output_path = image_path.replace(".jpg", "_cartoon.jpg")
    cv2.imwrite(output_path, cartoon)
    return output_path

def apply_smooth_skin(image_path):
    img = cv2.imread(image_path)
    smooth = cv2.bilateralFilter(img, d=15, sigmaColor=75, sigmaSpace=75)
    output_path = image_path.replace(".jpg", "_smooth.jpg")
    cv2.imwrite(output_path, smooth)
    return output_path

# عند الضغط على زر
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    image_path = user_states.get(user_id)

    if not image_path:
        await query.edit_message_text("❗ لم يتم إرسال صورة بعد. أرسل صورة أولًا.")
        return

    if query.data == "pencil":
        output = apply_pencil_sketch(image_path)
        await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(output, 'rb'))
    elif query.data == "bw":
        output = apply_black_white(image_path)
        await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(output, 'rb'))
    elif query.data == "cartoon":
        output = apply_cartoon(image_path)
        await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(output, 'rb'))
    elif query.data == "smooth":
        output = apply_smooth_skin(image_path)
        await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(output, 'rb'))
    elif query.data == "back":
        await query.edit_message_text("🔄 اختر التأثير من جديد:", reply_markup=FILTERS_KEYBOARD)
        return

    os.remove(image_path)
    if os.path.exists(output):
        os.remove(output)
    user_states.pop(user_id, None)

# عند الضغط على زر "اشتركت"
async def restart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    subscribed = await is_user_subscribed(context.bot, user_id)
    if not subscribed:
        await query.edit_message_text(
            f"❗ لم يتم التحقق من اشتراكك بعد. تأكد من الاشتراك في القناة:\n👉 https://t.me/{CHANNEL_USERNAME}"
        )
        return

    user_subscriptions.add(user_id)
    await query.edit_message_text("✅ تم التحقق من اشتراكك! أرسل صورة الآن.")

# تشغيل البوت
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(restart_handler, pattern="^restart$"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ Bot is running...")
    app.run_polling()