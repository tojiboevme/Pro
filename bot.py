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

# ✅ Kod ishlatilganmi
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

# ✅ Raqam
def get_next_number() -> int:
    if not os.path.exists(USERS_FILE):
        return 1
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        lines = list(csv.reader(f))
        return len(lines)

# ✅ Holatlar
class Form(StatesGroup):
    phone = State()
    code = State()

# ✅ Bloklanganini tekshirish
def is_locked(user_data: dict) -> str | None:
    now = datetime.now().timestamp()
    if 'locked_until' in user_data and now < user_data['locked_until']:
        wait_sec = int(user_data['locked_until'] - now)
        wait_min = wait_sec // 60
        wait_txt = f"{wait_min} daqiqa" if wait_min >= 1 else f"{wait_sec} soniya"
        return f"⏱ Siz vaqtincha bloklangansiz. {wait_txt} dan so‘ng urinib ko‘ring."
    return None

# ✅ /start
@dp.message(F.text == "/start")
async def start_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    lock_msg = is_locked(data)
    if lock_msg:
        await message.answer(lock_msg)
        return

    await message.answer(
        "👋 Assalomu alaykum! Sizni Ali Glass aksiyasida ko‘rib turganimizdan xursandmiz!\n"
        "🌟 Har bir kod — bu imkoniyat. Har bir imkoniyat — bu orzuga bir qadam yaqinlik !!!",
        reply_markup=main_menu
    )

# ✅ Aksiya tugmasi
@dp.message(F.text == "🎁 Aksiyada ishtirok etish")
async def register_start(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="📱 Telefon raqam yuborish", request_contact=True)]
    ])
    await state.set_state(Form.phone)
    await message.answer("Iltimos, telefon raqamingizni pastdagi tugma orqali yuboring:", reply_markup=keyboard)

# ✅ Telefon tugmadan
@dp.message(Form.phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data({
        'phone': phone,
        'retries': 0,
        'locked_until': 0
    })
    await state.set_state(Form.code)
    await message.answer("🎯 Endi 8 xonali mahsulot kodini kiriting:", reply_markup=ReplyKeyboardRemove())

# ❌ Oddiy text yuborsa
@dp.message(Form.phone, F.text)
async def phone_invalid(message: Message, state: FSMContext):
    await message.answer("❗️ Iltimos, 📱 telefon tugmasi orqali raqamingizni yuboring.")

# ✅ Kodni tekshirish
@dp.message(Form.code)
async def get_code(message: Message, state: FSMContext):
    user_data = await state.get_data()
    now = datetime.now().timestamp()

    # Bloklanganmi tekshirish
    lock_msg = is_locked(user_data)
    if lock_msg:
        await message.answer(lock_msg)
        return

    code = message.text.strip()
    retries = user_data.get("retries", 0)

    if code not in valid_codes:
        retries += 1
        if retries >= 3:
            await state.update_data(locked_until=now + 60)
            await state.clear()
            await message.answer("🚫 3 marta noto‘g‘ri kod kiritdingiz. 1 daqiqadan so‘ng urinib ko‘ring.")
            return
        else:
            await state.update_data(retries=retries)
            qoldi = 3 - retries
            await message.answer(f"❌ Kod noto‘g‘ri. Yana {qoldi} ta urinish qoldi.")
            return

    if is_code_used(code):
        await message.answer("⚠️ Bu kod allaqachon ishlatilgan. Yangi kod kiriting.")
        return

    action_number = get_next_number()

    # Yozish uchun faqat kerakli ma'lumotlar
    record = {
        'phone': user_data['phone'],
        'code': code,
        'telegram_id': message.from_user.id,
        'datetime': datetime.now().isoformat(),
        'random_number': action_number
    }

    os.makedirs("storage", exist_ok=True)
    file_exists = os.path.isfile(USERS_FILE)
    with open(USERS_FILE, "a", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['phone', 'code', 'telegram_id', 'datetime', 'random_number'])
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)

    save_used_code(code)

    await message.answer(
        f"✅ Barakalla! Kodingiz qabul qilindi!\n"
        f"🎯 Sizga aksiya uchun raqam berildi: {action_number}\n"
        f"🌟 Omad siz tomonda bo‘lishi mumkin!",
        reply_markup=main_menu
    )
    await state.clear()

# ✅ Admin uchun eksport
@dp.message(F.text == "/export")
async def export_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Sizda ruxsat yo'q.")
        return

    if os.path.isfile(USERS_FILE):
        await message.answer_document(types.FSInputFile(USERS_FILE))
    else:
        await message.answer("📂 Hozircha hech kim ro‘yxatdan o‘tmagan.")

# ✅ Botni ishga tushurish
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
