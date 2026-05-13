import random
import string
import time
import hashlib
import hmac
import base64
import struct
import telebot
from telebot import types
import sqlite3
from datetime import datetime, date
import re

# ================= CONFIG =================
TOKEN = "8627363377:AAHO7JJHeODw8YGNGJayu754PO9uV4nBmXI"
ADMIN_ID = 8585679491
CHANNEL_USERNAME = "@VXHASANYT0"
SUPPORT_ID = "@HASANYT0"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance REAL DEFAULT 0,
        invites INTEGER DEFAULT 0,
        total_earned_from_ref REAL DEFAULT 0,
        referrer_id INTEGER,
        joined_at TEXT
    )""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task_username TEXT,
        password TEXT,
        fa_secret TEXT,
        timestamp TEXT
    )""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        nagad_number TEXT,
        amount REAL,
        status TEXT DEFAULT 'Pending',
        timestamp TEXT
    )""")
    
    conn.commit()
    conn.close()

init_db()

# ================= HELPERS =================
def generate_username():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=6)) + ''.join(random.choices(string.ascii_lowercase, k=8))

def clean_secret(secret):
    return ''.join(c for c in secret if c.isalnum()).upper()

def get_totp_code(secret):
    try:
        clean_sec = clean_secret(secret)
        key = base64.b32decode(clean_sec + '=' * ((8 - len(clean_sec) % 8) % 8))
        counter = struct.pack('>Q', int(time.time() // 30))
        hmac_hash = hmac.new(key, counter, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        code = (struct.unpack('>I', hmac_hash[offset:offset+4])[0] & 0x7FFFFFFF) % 1000000
        return f"{code:06d}"
    except:
        return "000000"

def is_valid_instagram_2fa_secret(secret):
    pattern = r'^([A-Z2-7]{4}\s){7}[A-Z2-7]{4}$'
    return re.match(pattern, secret.strip().upper()) is not None

def is_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def today_date():
    return date.today().isoformat()

# ================= MENUS =================
def user_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📋 কাজ", "💰 ব্যালেন্স")
    markup.add("🏦 টাকা উতোলন", "🏆 লিডারবোর্ড")
    markup.add("🎁 Invite & Earn", "📞 সাপোর্ট")
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("👤 ইউজারনেম", "🔑 পাসওয়ার্ড")
    markup.add("🔐 2FA", "👥 রেফার")
    markup.add("📊 স্ট্যাটাস", "📢 ব্রডকাস্ট")
    markup.add("👥 ইউজার লিস্ট", "✅ অ্যাপ্রোভ অল")
    markup.add("❌ ক্যানসেল অল", "📜 উইথড্র হিস্টরি")
    markup.add("💰 ব্যালেন্স এড", "🗑️ ক্লিয়ার অল")
    return markup
    # ================= START & VERIFICATION =================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    first_name = message.from_user.first_name or "User"
    args = message.text.split()[1:] if len(message.text.split()) > 1 else None

    referrer_id = int(args[0]) if args and args[0].isdigit() and int(args[0]) != user_id else None

    if not is_joined(user_id):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("🔗 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"))
        btn.add(types.InlineKeyboardButton("✅ Check", callback_data="check_join"))
        bot.send_message(message.chat.id, "⚠️ প্রথমে চ্যানেলে জয়েন করুন", reply_markup=btn)
        return

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""INSERT OR IGNORE INTO users 
        (user_id, username, first_name, referrer_id, joined_at) 
        VALUES (?,?,?,?,?)""", 
        (user_id, username, first_name, referrer_id, datetime.now().isoformat()))
    if referrer_id:
        cur.execute("UPDATE users SET invites = invites + 1 WHERE user_id=?", (referrer_id,))
    conn.commit()
    conn.close()

    if user_id == ADMIN_ID:
        bot.send_message(message.chat.id, "👑 Welcome Admin", reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, f"👋 Welcome {first_name}", reply_markup=user_menu())


@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_channel_join(call):
    user_id = call.from_user.id
    if is_joined(user_id):
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✅ <b>আপনার ভেরিফিকেশন সফল হয়েছে!</b>\n\nএখন আপনি বট ব্যবহার করতে পারবেন 🎉",
            reply_markup=None
        )
        username = call.from_user.username or "NoUsername"
        first_name = call.from_user.first_name or "User"
        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at) VALUES (?,?,?,?)", 
                    (user_id, username, first_name, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        if user_id == ADMIN_ID:
            bot.send_message(call.message.chat.id, "👑 Welcome Admin", reply_markup=admin_menu())
        else:
            bot.send_message(call.message.chat.id, f"👋 Welcome {first_name}", reply_markup=user_menu())
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো চ্যানেলে জয়েন করেননি!", show_alert=True)

# ================= USER SIDE =================
@bot.message_handler(func=lambda m: m.text == "📋 কাজ")
def task_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💠 ইন্সটাগ্রাম 2FA (৳2.10)", callback_data="ig_2fa"))
    bot.send_message(message.chat.id, "⚡️ যেকোনো একটি কাজ সিলেক্ট করুন⏬", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💰 ব্যালেন্স")
def balance(message):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    result = cur.fetchone()
    bal = result[0] if result else 0
    bot.send_message(message.chat.id, f"💰 <b>আপনার ব্যালেন্স</b>\n\n💵 <code>{bal:.2f} টাকা</code>")

@bot.message_handler(func=lambda m: m.text == "🏦 টাকা উতোলন")
def withdraw_start(message):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    result = cur.fetchone()
    bal = result[0] if result else 0
    conn.close()
    if bal < 50:
        return bot.send_message(message.chat.id, "❌ উত্তোলনের জন্য ন্যূনতম ৫০ টাকা থাকতে হবে।")
    msg = bot.send_message(message.chat.id, "📱 নগদ নাম্বার লিখুন (১১ ডিজিট):")
    bot.register_next_step_handler(msg, process_nagad_number, bal)

def process_nagad_number(message, balance):
    number = message.text.strip()
    if len(number) != 11 or not number.isdigit():
        return bot.send_message(message.chat.id, "❌ সঠিক নগদ নাম্বার দিন (১১ ডিজিট)।")
    msg = bot.send_message(message.chat.id, f"💰 আপনার ব্যালেন্স: {balance:.2f} টাকা\n\nকত টাকা উত্তোলন করতে চান?")
    bot.register_next_step_handler(msg, process_withdraw_amount, number, balance)

def process_withdraw_amount(message, nagad_number, max_balance):
    try:
        amount = float(message.text.strip())
    except:
        return bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন।")
    if amount < 50:
        return bot.send_message(message.chat.id, "❌ ন্যূনতম ৫০ টাকা উত্তোলন করতে হবে।")
    if amount > max_balance:
        return bot.send_message(message.chat.id, f"❌ আপনার ব্যালেন্সের চেয়ে বেশি তুলতে পারবেন না।")
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, message.from_user.id))
    cur.execute("INSERT INTO withdrawals (user_id, nagad_number, amount, timestamp) VALUES (?,?,?,?)",
                (message.from_user.id, nagad_number, amount, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"""
✅ <b>উত্তোলন রিকোয়েস্ট সফল হয়েছে!</b>
📱 নগদ: <code>{nagad_number}</code>
💰 পরিমাণ: <b>{amount} টাকা</b>
⏳ আপনার টাকাটি ২৪ ঘণ্টার মধ্যে পাঠানো হবে।
""")
@bot.message_handler(func=lambda m: m.text == "🏆 লিডারবোর্ড")
def leaderboard(message):
    today = today_date()
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT u.first_name, COUNT(t.id) as tasks 
        FROM users u 
        JOIN tasks t ON u.user_id = t.user_id 
        WHERE t.timestamp LIKE ? 
        GROUP BY u.user_id 
        ORDER BY tasks DESC LIMIT 10
    """, (f"{today}%",))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return bot.send_message(message.chat.id, "আজকে এখনো কোনো টাস্ক অ্যাপ্রুভ হয়নি।")
    text = "🏆 <b>আজকের টপ ১০ লিডার</b>\n\n"
    for i, (fname, tasks) in enumerate(rows, 1):
        text += f"<b>{i}.</b> {fname} → <b>{tasks}</b> টাস্ক\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🎁 Invite & Earn")
def invite_earn(message):
    user_id = message.from_user.id
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT invites, total_earned_from_ref FROM users WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    conn.close()
    invites = result[0] if result else 0
    earned = result[1] if result else 0
    ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.send_message(message.chat.id, f"""
🎁 <b>Invite & Earn</b>
👥 রেফার করেছেন: <b>{invites}</b> জন
💰 রেফার থেকে ইনকাম: <b>৳{earned:.2f}</b>
📎 আপনার রেফার লিংক: <code>{ref_link}</code>
💵 রেফার কমিশন: <b>10%</b> লাইফটাইম
""")

@bot.message_handler(func=lambda m: m.text == "📞 সাপোর্ট")
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🆘 সাপোর্টে যোগাযোগ করুন", url=f"https://t.me/{SUPPORT_ID.replace('@','')}"))
    bot.send_message(message.chat.id, """
📞 <b>সাপোর্ট টিম</b>
যেকোনো সমস্যা বা সাহায্যের জন্য নিচের বাটনে ক্লিক করুন
""", reply_markup=markup)

# ================= 2FA TASK =================
@bot.callback_query_handler(func=lambda call: call.data == "ig_2fa")
def ig_2fa(call):
    username = generate_username()
    text = f"""
👤 <b>Username:</b> <code>{username}</code>
🔓 <b>Password:</b> <code>omor1212</code>
2FA Enable করে Secret Key পেলে নিচে ক্লিক করুন।
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔐 2FA Secret Key আছে", callback_data=f"has2fa_{username}"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("has2fa_"))
def ask_secret_key(call):
    username = call.data.split("_", 1)[1]
    msg = bot.send_message(call.message.chat.id, """
🔑 Instagram থেকে পাওয়া **2FA Secret Key** পুরোটা পেস্ট করে পাঠান:

উদাহরণ:
<code>QQYW RTTG Z244 ODUN 4XKP 7PN2 VHF2 2WGR</code>
""")
    bot.register_next_step_handler(msg, process_secret_key, username)

def process_secret_key(message, username):
    secret_key = message.text.strip()
    user_id = message.from_user.id
    if not is_valid_instagram_2fa_secret(secret_key):
        bot.send_message(message.chat.id, "❌ সঠিক ফরম্যাটে 2FA Secret Key দিন।")
        bot.send_message(message.chat.id, "🏠 মেইন মেনুতে ফিরে গেলাম।", reply_markup=user_menu())
        return
    current_code = get_totp_code(secret_key)
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks (user_id, task_username, password, fa_secret, timestamp) VALUES (?,?,?,?,?)",
                (user_id, username, "omor1212", secret_key, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Complete", callback_data=f"comp_{user_id}_{username}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data=f"canc_{user_id}")
    )
    bot.send_message(message.chat.id, f"""
✅ <b>কাজ সফলভাবে সাবমিট হয়েছে!</b>
👤 Username: <code>{username}</code>
🔢 Current 2FA Code: <code>{current_code}</code>
⏳ অ্যাডমিন রিভিউ করবে।
""")
    bot.send_message(ADMIN_ID, f"""
🔔 <b>New 2FA Task</b>
👤 Username: <code>{username}</code>
🔑 Secret: <code>{secret_key}</code>
🔢 Code: <code>{current_code}</code>
🆔 User: <code>{user_id}</code>
""", reply_markup=markup)
# ================= TASK COMPLETE & CANCEL =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("comp_"))
def complete_task(call):
    if call.from_user.id != ADMIN_ID: return
    try:
        _, user_id, username = call.data.split("_", 2)
        user_id = int(user_id)
        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("UPDATE users SET balance = balance + 2.10 WHERE user_id=?", (user_id,))
        cur.execute("SELECT referrer_id FROM users WHERE user_id=?", (user_id,))
        ref = cur.fetchone()
        if ref and ref[0]:
            cur.execute("UPDATE users SET balance = balance + 0.21, total_earned_from_ref = total_earned_from_ref + 0.21 WHERE user_id=?", (ref[0],))
            bot.send_message(ref[0], "🎉 আপনার রেফার করা ব্যক্তি কাজ কমপ্লিট করেছে। ১০% কমিশন পেয়েছেন ✅")
        conn.commit()
        conn.close()
        bot.send_message(user_id, "✅ Report approved, +৳2.10")
        bot.edit_message_text("✅ Completed", call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("canc_"))
def cancel_task(call):
    try:
        user_id = int(call.data.split("_")[1])
        bot.send_message(user_id, "❌ কাজটি ক্যানসেল করা হয়েছে। আবার ট্রাই করুন।")
        bot.edit_message_text("❌ Cancelled", call.message.chat.id, call.message.message_id)
    except:
        pass

# ================= ADMIN PANEL (সব বাটন) =================
@bot.message_handler(func=lambda m: m.text == "👤 ইউজারনেম" and m.from_user.id == ADMIN_ID)
def today_usernames(message):
    today = today_date()
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT task_username FROM tasks WHERE timestamp LIKE ? ORDER BY id", (f"{today}%",))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return bot.send_message(message.chat.id, "আজকে কোনো টাস্ক নেই।")
    text = "\n".join([row[0] for row in rows])
    bot.send_message(message.chat.id, f"<b>আজকের সব Username:</b>\n\n{text}")

@bot.message_handler(func=lambda m: m.text == "🔑 পাসওয়ার্ড" and m.from_user.id == ADMIN_ID)
def today_passwords(message):
    today = today_date()
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT password FROM tasks WHERE timestamp LIKE ? ORDER BY id", (f"{today}%",))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return bot.send_message(message.chat.id, "আজকে কোনো টাস্ক নেই।")
    text = "\n".join([row[0] for row in rows])
    bot.send_message(message.chat.id, f"<b>আজকের সব Password:</b>\n\n{text}")

@bot.message_handler(func=lambda m: m.text == "🔐 2FA" and m.from_user.id == ADMIN_ID)
def today_2fa(message):
    today = today_date()
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT fa_secret FROM tasks WHERE timestamp LIKE ? ORDER BY id", (f"{today}%",))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return bot.send_message(message.chat.id, "আজকে কোনো 2FA নেই।")
    text = "\n".join([row[0] for row in rows])
    bot.send_message(message.chat.id, f"<b>আজকের সব 2FA Secret:</b>\n\n{text}")

@bot.message_handler(func=lambda m: m.text == "✅ অ্যাপ্রোভ অল" and m.from_user.id == ADMIN_ID)
def bulk_approve_start(message):
    bot.send_message(message.chat.id, "যে ইউজারনেমগুলো অ্যাপ্রোভ করতে চান সেগুলো এক লাইনে পেস্ট করুন:")
    bot.register_next_step_handler(message, process_bulk_approve)

def process_bulk_approve(message):
    usernames = [u.strip() for u in message.text.splitlines() if u.strip()]
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    count = 0
    for uname in usernames:
        cur.execute("SELECT user_id FROM tasks WHERE task_username=?", (uname,))
        result = cur.fetchone()
        if result:
            uid = result[0]
            cur.execute("UPDATE users SET balance = balance + 2.10 WHERE user_id=?", (uid,))
            bot.send_message(uid, "✅ Report approved, +৳2.10")
            count += 1
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ {count} টি টাস্ক অ্যাপ্রোভ হয়েছে।")

@bot.message_handler(func=lambda m: m.text == "❌ ক্যানসেল অল" and m.from_user.id == ADMIN_ID)
def bulk_cancel_start(message):
    bot.send_message(message.chat.id, "যে ইউজারনেমগুলো ক্যানসেল করতে চান সেগুলো এক লাইনে পেস্ট করুন:")
    bot.register_next_step_handler(message, process_bulk_cancel)

def process_bulk_cancel(message):
    usernames = [u.strip() for u in message.text.splitlines() if u.strip()]
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    count = 0
    for uname in usernames:
        cur.execute("SELECT user_id FROM tasks WHERE task_username=?", (uname,))
        result = cur.fetchone()
        if result:
            uid = result[0]
            bot.send_message(uid, "❌ Report cancel")
            cur.execute("DELETE FROM tasks WHERE task_username=?", (uname,))
            count += 1
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"❌ {count} টি টাস্ক ক্যানসেল করা হয়েছে।")

@bot.message_handler(func=lambda m: m.text == "📜 উইথড্র হিস্টরি" and m.from_user.id == ADMIN_ID)
def withdraw_history(message):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""SELECT w.id, u.user_id, u.username, w.nagad_number, w.amount 
                   FROM withdrawals w 
                   JOIN users u ON w.user_id = u.user_id 
                   WHERE w.status = 'Pending' ORDER BY w.id DESC""")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return bot.send_message(message.chat.id, "কোনো পেন্ডিং উত্তোলন নেই।")
    for row in rows:
        wid, uid, uname, number, amount = row
        text = f"""
🆔 <code>{uid}</code>
👤 @{uname or 'N/A'}
📱 {number}
💰 {amount}৳
"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"w_app_{wid}_{uid}"),
            types.InlineKeyboardButton("❌ Cancel", callback_data=f"w_can_{wid}_{uid}")
        )
        bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🗑️ ক্লিয়ার অল" and m.from_user.id == ADMIN_ID)
def clear_today(message):
    today = today_date()
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE timestamp LIKE ?", (f"{today}%",))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ আজকের সব টাস্ক ক্লিয়ার করা হয়েছে।")

@bot.message_handler(func=lambda m: m.text == "📢 ব্রডকাস্ট" and m.from_user.id == ADMIN_ID)
def broadcast(message):
    bot.send_message(message.chat.id, "📢 সব ইউজারকে কী মেসেজ পাঠাবেন? লিখুন:")
    bot.register_next_step_handler(message, process_broadcast)

def process_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()
    conn.close()
    success = 0
    for (uid,) in users:
        try:
            bot.send_message(uid, message.text)
            success += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ ব্রডকাস্ট সম্পন্ন। {success} জনের কাছে পৌঁছেছে।")

@bot.message_handler(func=lambda m: m.text == "👥 রেফার" and m.from_user.id == ADMIN_ID)
def show_referrals(message):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT username, first_name, invites FROM users WHERE invites > 0 ORDER BY invites DESC")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return bot.send_message(message.chat.id, "কোনো রেফারাল নেই।")
    text = "👥 <b>রেফারাল লিস্ট</b>\n\n"
    for uname, fname, invites in rows:
        text += f"👤 {fname} | @{uname or 'N/A'} → <b>{invites}</b> রেফার\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📊 স্ট্যাটাস" and m.from_user.id == ADMIN_ID)
def bot_status(message):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    today = today_date()
    cur.execute("SELECT COUNT(*) FROM users WHERE joined_at LIKE ?", (f"{today}%",))
    today_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM tasks WHERE timestamp LIKE ?", (f"{today}%",))
    today_workers = cur.fetchone()[0]
    conn.close()
    bot.send_message(message.chat.id, f"""
📊 <b>বট স্ট্যাটাস</b>
👥 মোট ইউজার: <b>{total_users}</b>
📅 আজকের নতুন ইউজার: <b>{today_users}</b>
⚒️ আজকে কাজ করেছে: <b>{today_workers}</b>
""")

@bot.message_handler(func=lambda m: m.text == "👥 ইউজার লিস্ট" and m.from_user.id == ADMIN_ID)
def user_list(message):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id, first_name, username FROM users ORDER BY joined_at DESC")
    users = cur.fetchall()
    conn.close()
    text = "👥 <b>ইউজার লিস্ট</b>\n\n"
    for uid, fname, uname in users[:200]:
        text += f"🆔 <code>{uid}</code> | {fname} | @{uname or 'N/A'}\n"
    bot.send_message(message.chat.id, text)

# ================= RUN =================
print("✅ Bot Running Successfully...")
while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(e)
        time.sleep(5)
        