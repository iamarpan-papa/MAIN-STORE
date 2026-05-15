import os
import asyncio
import logging
import sqlite3
from datetime import datetime
from typing import Optional
import json
import urllib.request
import urllib.parse

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN", "8707891025:AAHn0t0O6HX0I_Fhf1x0D1N1njyIy_HGSPs")
ADMIN_IDS = {5815040020}
BOT_NAME = os.getenv("BOT_NAME", "ABHIJEET STORE")
QR_PATH = os.getenv("QR_PATH", "qr.png")
UPI_ID = os.getenv("UPI_ID", "arpam.bistan.ag@fam")
UPI_NAME = os.getenv("UPI_NAME", "BISTAN Charchil")
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/A_bhijeeet")
PAYMENT_PROOF_LINK = os.getenv("PAYMENT_PROOF_LINK", "https://t.me/abhi_feedback")
FILES_LINK = os.getenv("FILES_LINK", "https://t.me/ABHI_FILES")
FAMPAY_API_KEY = os.getenv("FAMPAY_API_KEY", "FAM_2ca7488cf4e43efd3908151bd3060d261d511eaa0747e46f")
FAMPAY_QR_API = os.getenv("FAMPAY_QR_API", "https://fampay.anujbots.xyz/qr.php")
FAMPAY_VERIFY_API = os.getenv("FAMPAY_VERIFY_API", "https://fampay.anujbots.xyz/verify.php")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", "store.db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

# =========================
# DB INIT
# =========================
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        is_reseller INTEGER DEFAULT 0
    )
    """
)

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """
)

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        stock TEXT DEFAULT '',
        FOREIGN KEY(category_id) REFERENCES categories(id)
    )
    """
)

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """
)

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS payment_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        utr TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        created_at TEXT NOT NULL
    )
    """
)

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        category_name TEXT NOT NULL,
        price INTEGER NOT NULL,
        delivered_item TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """
)

conn.commit()

# =========================
# HELPERS
# =========================
def get_setting(key: str, default: str = "") -> str:
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()
    return row[0] if row else default


def set_setting(key: str, value: str) -> None:
    cur.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


def ensure_user(user_id: int) -> None:
    cur.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_reseller(user_id: int) -> bool:
    cur.execute("SELECT is_reseller FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return bool(row and row[0] == 1)


def get_balance(user_id: int) -> int:
    cur.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return int(row[0]) if row else 0


def add_balance(user_id: int, amount: int) -> None:
    ensure_user(user_id)
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()


def deduct_balance(user_id: int, amount: int) -> bool:
    bal = get_balance(user_id)
    if bal < amount:
        return False
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    return True


def pending_key(user_id: int) -> str:
    return f"pending_payment:{user_id}"


def get_category_id(name: str) -> Optional[int]:
    cur.execute("SELECT id FROM categories WHERE name=?", (name,))
    row = cur.fetchone()
    return int(row[0]) if row else None


def get_product(pid: int):
    cur.execute(
        """
        SELECT p.id, p.category_id, p.name, p.price, p.stock, c.name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.id=?
        """,
        (pid,),
    )
    return cur.fetchone()


def consume_stock(stock_text: str):
    lines = [x.strip() for x in stock_text.splitlines() if x.strip()]
    if not lines:
        return None, None
    item = lines[0]
    rest = "\n".join(lines[1:])
    return item, rest


def seed_catalog() -> None:
    categories = ["Category 1", "Category 2", "Category 3"]
    for name in categories:
        cur.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (name,))
    conn.commit()


async def on_startup() -> None:
    seed_catalog()
    if not get_setting("bot_status"):
        set_setting("bot_status", "ON")


# =========================
# KEYBOARDS
# =========================
def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Shop Now")],
            [KeyboardButton(text="📦 My Orders"), KeyboardButton(text="👤 Profile")],
            [KeyboardButton(text="🧾 Pay Proof"), KeyboardButton(text="🗂 Feedback")],
            [KeyboardButton(text="📘 How to Use"), KeyboardButton(text="💬 Support")],
        ],
        resize_keyboard=True,
    )


def admin_panel() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="🤖 Bot Status")],
            [KeyboardButton(text="💰 Add Balance"), KeyboardButton(text="🛠 Shop Setup")],
            [KeyboardButton(text="👥 Add Reseller"), KeyboardButton(text="🛑 Remove Reseller")],
            [KeyboardButton(text="📋 Reseller List"), KeyboardButton(text="➕ Add Category")],
            [KeyboardButton(text="🗑 Remove Category"), KeyboardButton(text="➕ Add Product")],
            [KeyboardButton(text="💲 Change Price"), KeyboardButton(text="🗑 Remove Product")],
            [KeyboardButton(text="📦 Stock")],
            [KeyboardButton(text="🔙 Main Menu")],
        ],
        resize_keyboard=True,
    )


def back_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Main Menu")]],
        resize_keyboard=True,
    )


def category_kb() -> ReplyKeyboardMarkup:
    cur.execute("SELECT id, name FROM categories ORDER BY id ASC")
    rows = cur.fetchall()
    kb = [[KeyboardButton(text=f"📁 {name}")] for _, name in rows]
    kb.append([KeyboardButton(text="🔙 Main Menu")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def support_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💬 Support", url=SUPPORT_LINK)]]
    )


def info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧾 Pay Proof", url=PAYMENT_PROOF_LINK)],
            [InlineKeyboardButton(text="📁 All Files", url=FILES_LINK)],
            [InlineKeyboardButton(text="💬 Support", url=SUPPORT_LINK)],
        ]
    )


def payment_action_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ I have paid", callback_data="paid_btn")],
            [InlineKeyboardButton(text="➕ Add Funds", callback_data="add_funds")],
            [InlineKeyboardButton(text="💬 Support", url=SUPPORT_LINK)],
        ]
    )


def product_inline_kb(category_id: int):
    cur.execute(
        "SELECT id, name, price, stock FROM products WHERE category_id=? ORDER BY id ASC",
        (category_id,),
    )
    rows = cur.fetchall()
    buttons = []
    for pid, name, price, stock in rows:
        stock_count = len([x for x in stock.splitlines() if x.strip()])
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{name} • ₹{price} • Stock:{stock_count}",
                    callback_data=f"buy:{pid}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


def product_text(category_id: int) -> str:
    cur.execute("SELECT name FROM categories WHERE id=?", (category_id,))
    cat = cur.fetchone()
    if not cat:
        return "Category not found."

    cur.execute(
        "SELECT id, name, price, stock FROM products WHERE category_id=? ORDER BY id ASC",
        (category_id,),
    )
    rows = cur.fetchall()
    if not rows:
        return f"No products found in {cat[0]}."

    text = f"🛍 *{cat[0]} Products*\n\n"
    for pid, name, price, stock in rows:
        stock_count = len([x for x in stock.splitlines() if x.strip()])
        text += f"#{pid} — {name}\n₹{price} | Stock: {stock_count}\n\n"
    return text



def http_get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))

async def create_fampay_qr(amount: int) -> Optional[dict]:
    if not FAMPAY_API_KEY or FAMPAY_API_KEY == "FAM_2ca7488cf4e43efd3908151bd3060d261d511eaa0747e46f":
        return None
    params = urllib.parse.urlencode({"upi": UPI_ID, "amount": amount})
    url = f"{FAMPAY_QR_API}?{params}"
    try:
        data = await asyncio.to_thread(http_get_json, url)
        if data.get("status") == "success":
            return data.get("data", {})
    except Exception as exc:
        logger.exception("FamPay QR generation failed: %s", exc)
    return None

async def verify_fampay_payment(order_id: str) -> Optional[dict]:
    if not FAMPAY_API_KEY or FAMPAY_API_KEY == "FAM_2ca7488cf4e43efd3908151bd3060d261d511eaa0747e46f":
        return None
    params = urllib.parse.urlencode({
        "order_id": order_id,
        "api_key": FAMPAY_API_KEY,
    })
    url = f"{FAMPAY_VERIFY_API}?{params}"
    try:
        data = await asyncio.to_thread(http_get_json, url)
        if data.get("status") == "success":
            return data.get("data", {})
    except Exception as exc:
        logger.exception("FamPay verify failed: %s", exc)
    return None

async def send_payment_qr(message: Message, amount: int) -> None:
    # Try automatic FamPay QR first
    fam = await create_fampay_qr(amount)
    if fam:
        order_id = str(fam.get("order_id", ""))
        qr_url = fam.get("qr_url")
        expires_at = fam.get("expires_at_ist", "5 minutes")
        if order_id:
            set_setting(pending_key(message.from_user.id), f"AUTO_VERIFY|{amount}|{order_id}")

        caption = (
            f"💳 *Auto Deposit ₹{amount}*

"
            f"⏳ Expires: {expires_at}
"
            f"🔄 After payment, tap *I have paid* to auto verify."
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ I have paid", callback_data="paid_btn")],
                [InlineKeyboardButton(text="💬 Support", url=SUPPORT_LINK)],
            ]
        )

        if qr_url:
            try:
                await message.answer_photo(photo=qr_url, caption=caption, reply_markup=kb)
                return
            except Exception as exc:
                logger.exception("Failed to send FamPay QR: %s", exc)

    # Fallback to manual QR
    caption = (
        f"💳 *Pay ₹{amount}*

"
        f"UPI ID: `{UPI_ID}`
"
        f"Name: `{UPI_NAME}`

"
        f"After payment, tap *I have paid* and then send your UTR / transaction reference number."
    )

    qr_full_path = os.path.join(BASE_DIR, QR_PATH)
    if os.path.isfile(qr_full_path):
        try:
            await message.answer_photo(
                photo=FSInputFile(qr_full_path),
                caption=caption,
                reply_markup=payment_action_kb(),
            )
            return
        except Exception as exc:
            logger.exception("Failed to send QR photo: %s", exc)

    await message.answer(
        caption + f"

QR file not found or could not be sent: `{qr_full_path}`",
        reply_markup=payment_action_kb(),
    )


async def notify_admins_purchase(
    user_id: int,
    full_name: str,
    username: str,
    order_id: int,
    product_id: int,
    product_name: str,
    category_name: str,
    price: int,
    delivered_item: str,
    balance_left: int,
) -> None:
    admin_text = (
        f"🛒 *New Order*\n\n"
        f"Order ID: `{order_id}`\n"
        f"User ID: `{user_id}`\n"
        f"Name: {full_name}\n"
        f"Username: @{username if username else 'None'}\n"
        f"Product ID: `{product_id}`\n"
        f"Product: {product_name}\n"
        f"Category: {category_name}\n"
        f"Price: ₹{price}\n"
        f"Delivered: `{delivered_item}`\n"
        f"Remaining Balance: ₹{balance_left}\n"
        f"Time: {datetime.utcnow().isoformat()}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception:
            pass


async def send_order_history(message: Message) -> None:
    cur.execute(
        """
        SELECT id, product_name, category_name, price, delivered_item, created_at
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
        """,
        (message.from_user.id,),
    )
    rows = cur.fetchall()
    if not rows:
        await message.answer("You have no orders yet.", reply_markup=main_menu())
        return

    text = "📜 *Your Order History*\n\n"
    for oid, pname, cname, price, item, created_at in rows:
        text += (
            f"Order #{oid}\n"
            f"Product: {pname}\n"
            f"Category: {cname}\n"
            f"Price: ₹{price}\n"
            f"Item: `{item}`\n"
            f"Time: {created_at}\n\n"
        )
    await message.answer(text, reply_markup=main_menu())


# =========================
# START / BASIC COMMANDS
# =========================
@dp.message(CommandStart())
async def start(message: Message):
    ensure_user(message.from_user.id)
    shop_status = get_setting("bot_status", "ON")
    # fixed broken multiline string
    welcome = (
    f"👋 Welcome {message.from_user.first_name}\n\n"
    f"🤖 Bot Status: {'🟢 On' if shop_status == 'ON' else '🔴 Off'}"
)
    await message.answer(welcome, reply_markup=main_menu())


@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(f"👑 Admin Panel — {BOT_NAME}", reply_markup=admin_panel())


@dp.message(Command("orders"))
async def orders_cmd(message: Message):
    ensure_user(message.from_user.id)
    await send_order_history(message)


@dp.message(F.text == "🔙 Main Menu")
async def main_menu_handler(message: Message):
    await message.answer("Main menu:", reply_markup=main_menu())


@dp.message(F.text == "🛒 Shop Now")
async def shop(message: Message):
    await message.answer("Choose a category:", reply_markup=category_kb())


@dp.message(F.text == "🛒 Shop")
async def shop_legacy(message: Message):
    await message.answer("Choose a category:", reply_markup=category_kb())


@dp.message(F.text == "💳 Balance")
async def balance_legacy(message: Message):
    ensure_user(message.from_user.id)
    bal = get_balance(message.from_user.id)
    await message.answer(f"💰 Your balance: ₹{bal}", reply_markup=main_menu())


@dp.message(F.text == "👤 Profile")
async def profile(message: Message):
    ensure_user(message.from_user.id)
    bal = get_balance(message.from_user.id)
    role = "Admin" if is_admin(message.from_user.id) else ("Reseller" if is_reseller(message.from_user.id) else "User")
    text = (
        f"👤 Profile\n\n"
        f"ID: `{message.from_user.id}`\n"
        f"Name: {message.from_user.full_name}\n"
        f"Role: {role}\n"
        f"Balance: ₹{bal}"
    )
    await message.answer(text, reply_markup=main_menu())


@dp.message(F.text == "👤 My Profile")
async def profile_legacy(message: Message):
    ensure_user(message.from_user.id)
    bal = get_balance(message.from_user.id)
    role = "Admin" if is_admin(message.from_user.id) else ("Reseller" if is_reseller(message.from_user.id) else "User")
    text = (
        f"👤 Profile\n\n"
        f"ID: `{message.from_user.id}`\n"
        f"Name: {message.from_user.full_name}\n"
        f"Role: {role}\n"
        f"Balance: ₹{bal}"
    )
    await message.answer(text, reply_markup=main_menu())


@dp.message(F.text == "📦 My Orders")
async def my_orders(message: Message):
    ensure_user(message.from_user.id)
    await send_order_history(message)


@dp.message(F.text == "📜 Order History")
async def order_history_legacy(message: Message):
    ensure_user(message.from_user.id)
    await send_order_history(message)


@dp.message(F.text == "🧾 Pay Proof")
async def pay_proof_btn(message: Message):
    await message.answer(
        "Payment proof channel:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🧾 Pay Proof", url=PAYMENT_PROOF_LINK)]]
        ),
    )


@dp.message(F.text == "🗂 Feedback")
async def feedback_btn(message: Message):
    await message.answer(
        "All files channel:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📁 All Files", url=FILES_LINK)]]
        ),
    )


@dp.message(F.text == "📘 How to Use")
async def how_to_use_btn(message: Message):
    await message.answer(
        "Use Shop Now to browse categories. Use Add Money to top up via QR.\n"
        "Pay Proof opens your payment proof channel and All Files opens your files channel.",
        reply_markup=info_kb(),
    )


@dp.message(F.text == "ℹ️ Help")
async def help_legacy(message: Message):
    await message.answer(
        "Use Shop Now to browse categories. Use Add Money to top up via QR.\n"
        "Pay Proof opens your payment proof channel and All Files opens your files channel.",
        reply_markup=info_kb(),
    )


@dp.message(F.text == "💬 Support")
async def support_btn(message: Message):
    await message.answer("Support:", reply_markup=support_kb())





@dp.message(F.text == "➕ Add Money")
async def add_money_start(message: Message):
    ensure_user(message.from_user.id)
    set_setting(pending_key(message.from_user.id), "AMOUNT")
    await message.answer(
        "Send the amount you want to add, for example: `500`\n\n"
        f"UPI ID: `{UPI_ID}`\n"
        f"Name: `{UPI_NAME}`",
        reply_markup=payment_action_kb(),
    )


@dp.message(F.text == "🤖 Bot Status")
async def bot_status(message: Message):
    if not is_admin(message.from_user.id):
        return
    current = get_setting("bot_status", "ON")
    new_status = "OFF" if current == "ON" else "ON"
    set_setting("bot_status", new_status)
    await message.answer(f"Bot status changed to {new_status}.", reply_markup=admin_panel())


# =========================
# ADMIN ACTION STARTERS
# =========================
@dp.message(F.text == "📢 Broad
