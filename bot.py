import csv
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN, ADMIN_ID
from data.codes import valid_codes  # 8 xonali kodlar ro‘yxati

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

main_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🎁 Aksiyada ishtirok etish")]],
    resize_keyboard=True
)

USED_CODES_FILE = "storage/used_codes.csv"
USERS_FILE = "storage/users.csv"

# ✅ Foydalanilgan kodni tekshirish
def is_code_used(code: str) -> bool:
    if not os.path.exists(USED_CODES_FILE):
        return False
    with open(USED_CODES_FILE, "r", encoding="utf-8") as f:
        used = [line.strip() for line in f if line.strip()]
        return code in used

# ✅ Kodni saqlash
def save_used_code(code: str):
    with open(USED_CODES_FILE, "a", encoding="utf-8") as f:
        f.write(code + "\n")

# ✅ Yangi foydalanuvchiga raqam berish
def get_next_number() -> int:
    if not os.path.exists(USERS_FILE):
        return 1
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        lines = list(csv.reader(f))
        return len(lines)  # header ham bor

# ✅ Holat
class Form(StatesGroup):
    phone = State()
    code = State()

# ✅ /start
@dp.message(F.text == "/start")
async def start_handler(message: Message, state: FSMContext):
    await message.answer("👋 Assalomu alaykum! Sizni Ali Glass aksiyasida ko'rib turganimizdan xursandmiz!\n 🌟 Har bir kod — bu imkoniyat. Har bir imkoniyat — bu orzuga bir qadam yaqinlik !!!", reply_markup=main_menu)

# ✅ "Aksiyada ishtirok etish"
@dp.message(F.text == "🎁 Aksiyada ishtirok etish")
async def register_start(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="📱 Telefon raqam yuborish", request_contact=True)]
    ])
    await state.set_state(Form.phone)
    await message.answer("Iltimos, telefon raqamingizni yuboring:", reply_markup=keyboard)

# ✅ Telefon raqamini olish
@dp.message(Form.phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await state.set_state(Form.code)
    await message.answer("Endi sovrinli 🎁o‘yinda ishtirok etish uchun  🤗 🧾 8 xonali mahsulot kodini kiriting", reply_markup=ReplyKeyboardRemove())

# ✅ Kodni tekshirish va saqlash
@dp.message(Form.code)
async def get_code(message: Message, state: FSMContext):
    code = message.text.strip()
    user_data = await state.get_data()

    if code not in valid_codes:
        await message.answer("❌ Bu kod Ali Glass Aksiyasida mavjud emas.\n Iltimos, tekshirib qayta kiriting.")
        return

    if is_code_used(code):
        await message.answer("⚠️ Afsuski, bu kod allaqachon ishlatilgan. \n📌 Balki sizdan oldin boshqa ishtirokchi harakat qilgandir.\n💡 Harakatdan to‘xtamang — sizni hali omad kutib turibdi!")
        return

    action_number = get_next_number()
    user_data.update({
        'code': code,
        'telegram_id': message.from_user.id,
        'datetime': datetime.now().isoformat(),
        'random_number': action_number
    })

    os.makedirs("storage", exist_ok=True)
    file_exists = os.path.isfile(USERS_FILE)

    with open(USERS_FILE, "a", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['phone', 'code', 'telegram_id', 'datetime', 'random_number'])
        if not file_exists:
            writer.writeheader()
        writer.writerow(user_data)

    save_used_code(code)

    await message.answer(
        f"✅ Barakalla! Sizning kodingiz muvaffaqiyatli ro‘yxatdan o‘tdi! \n🎯 Sizga aksiya uchun noyob raqam berildi — omad siz tomonda bo‘lishi mumkin!\n🌟 Orzularingizga bir qadam yaqinlashdingiz. Endi esa, omadni kutamiz!\n {action_number}",
        reply_markup=main_menu
    )
    await state.clear()

# ✅ Admin uchun export qilish
@dp.message(F.text == "/export")
async def export_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda ruxsat yo'q.")
        return

    if os.path.isfile(USERS_FILE):
        await message.answer_document(types.FSInputFile(USERS_FILE))
    else:
        await message.answer("📂 Hozircha hech kim ro'yxatdan o'tmagan.")

# ✅ Botni ishga tushurish
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
