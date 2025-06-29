import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN, ADMIN_ID
from data.codes import valid_codes  # 8 xonali kodlar ro‘yxati
import database  # siz yozgan database.py modul

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎁 Aksiyada ishtirok etish")],
        [KeyboardButton(text="📱 Bizning ijtimoiy tarmoqlarimiz")]
    ],
    resize_keyboard=True
)

# ✅ Holatlar
class Form(StatesGroup):
    phone = State()
    code = State()
    ask_more = State()  # Yangi holat

# ✅ /start
@dp.message(F.text == "/start")
async def start_handler(message: Message, state: FSMContext):
    await message.answer(
        "👋 Assalomu alaykum! Sizni Ali Glass aksiyasida ko‘rib turganimizdan xursandmiz!\n"
        "🌟 Har bir kod — bu imkoniyat. Har bir imkoniyat — bu orzuga bir qadam yaqinlik !!!",
        reply_markup=main_menu
    )

# ✅ "Aksiyada ishtirok etish"
@dp.message(F.text == "🎁 Aksiyada ishtirok etish")
async def register_start(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="📱 Telefon raqam yuborish", request_contact=True)]
    ])
    await state.set_state(Form.phone)
    await message.answer("📞 Iltimos, telefon raqamingizni pastdagi tugma orqali yuboring:", reply_markup=keyboard)

# ✅ Telefon raqam tugmasi orqali
@dp.message(Form.phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data({
        'phone': phone,
        'retries': 0
    })
    await state.set_state(Form.code)
    await message.answer("🎯 Endi 8 xonali mahsulot kodini kiriting:", reply_markup=ReplyKeyboardRemove())

# ❌ Telefon raqamini noto‘g‘ri yuborish
@dp.message(Form.phone, F.text)
async def phone_invalid(message: Message, state: FSMContext):
    await message.answer("❗️ Iltimos, faqat 📱 telefon tugmasi orqali raqam yuboring.")

# ✅ Kodni tekshirish
@dp.message(Form.code)
async def get_code(message: Message, state: FSMContext):
    user_data = await state.get_data()
    code = message.text.strip()
    retries = user_data.get("retries", 0)

    if code not in valid_codes:
        retries += 1
        await state.update_data(retries=retries)

        if retries >= 3:
            await state.clear()
            await message.answer("🚫 3 marta noto‘g‘ri kod kiritdingiz.\nIltimos, '🎁 Aksiyada ishtirok etish' tugmasini bosib qaytadan urinib ko‘ring.", reply_markup=main_menu)
            return
        else:
            qoldi = 3 - retries
            await message.answer(f"❌ Kod noto‘g‘ri. Yana {qoldi} ta urinish qoldi.")
            return

    if database.is_code_used(code):
        await message.answer("⚠️ Bu kod allaqachon ishlatilgan. Iltimos, boshqa kod kiriting.")
        return

    action_number = database.get_next_number()
    now = datetime.now().isoformat()
    phone = user_data.get('phone')

    database.add_user(
        phone=phone,
        code=code,
        telegram_id=message.from_user.id,
        datetime_str=now,
        random_number=action_number
    )
    database.save_used_code(code)

    # ✅ Kod muvaffaqiyatli ro'yxatdan o'tdi, so'raymiz:
    await state.clear()
    markup = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="✅ Ha bor"), KeyboardButton(text="❌ Yo‘q")]
    ])
    await message.answer(
        f"✅ Barakalla! Kodingiz qabul qilindi!\n"
        f"🎯 Sizga aksiya uchun raqam berildi: {action_number}\n\n 🎉 Har oy g‘oliblar @aliglass_uz sahifasida aniqlanadi! \n📲 Obuna bo‘ling, kuzatib boring — omad siz tomonda bo‘lishi mumkin!\n"
        f"Yana kodingiz bormi?",
        reply_markup=markup
    )
    await state.set_state(Form.ask_more)

# ✅ Ha bor — yana boshlaymiz
@dp.message(Form.ask_more, F.text == "✅ Ha bor")
async def ask_more_yes(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="📱 Telefon raqam yuborish", request_contact=True)]
    ])
    await state.set_state(Form.phone)
    await message.answer("📞 Yangi kod uchun telefon raqamingizni yuboring:", reply_markup=keyboard)

# ✅ Yo‘q — ijtimoiy tarmoqlarni ko'rsatamiz
@dp.message(Form.ask_more, F.text == "❌ Yo‘q")
async def ask_more_no(message: Message, state: FSMContext):
    await state.clear()
    buttons = [
        [types.InlineKeyboardButton(text="📸 Instagram", url="https://instagram.com/aliglass_uz")],
        [types.InlineKeyboardButton(text="📢 Telegram", url="https://t.me/aliglass_uz")]
    ]
    markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Aksiyada ishtirok etganingiz uchun rahmat!\nBizni ijtimoiy tarmoqlarda kuzatib boring:", reply_markup=markup)
    
    # 🔁 Bosh menyuga qaytarish
    await message.answer("🏠 Asosiy menyuga qaytdingiz:", reply_markup=main_menu)


# ✅ Admin uchun export
@dp.message(F.text == "/export")
async def export_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Sizda ruxsat yo'q.")
        return

    database.export_users_csv()
    await message.answer_document(types.FSInputFile("storage/users.csv"))

# ✅ Ijtimoiy tarmoqlar tugmasi
@dp.message(F.text == "📱 Bizning ijtimoiy tarmoqlarimiz")
async def social_links(message: Message):
    buttons = [
        [types.InlineKeyboardButton(text="📸 Instagram", url="https://instagram.com/aliglass_uz")],
        [types.InlineKeyboardButton(text="📢 Telegram", url="https://t.me/aliglass_uz")]
    ]
    markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Bizni ijtimoiy tarmoqlarda kuzatib boring:", reply_markup=markup)

# ✅ Botni ishga tushurish
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    database.create_tables()  # bazani ishga tushirganda jadval ochilsin
    asyncio.run(main())
