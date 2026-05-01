import telebot, json, os, time, logging
from telebot.types import *

TOKEN = "8720320122:AAFSF4nFn5yVlUSAtZSwv73iTBsO__59SaM"
OWNER_ID = 5815040020

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

DB_FILE = "data.json"
logging.basicConfig(level=logging.INFO)

# ================= LOAD / SAVE =================
def load():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE) as f:
            return json.load(f)
    except:
        return {}

def save():
    with open(DB_FILE + ".tmp", "w") as f:
        json.dump(DB, f, indent=2)
    os.replace(DB_FILE + ".tmp", DB_FILE)

DB = load()

# ================= DEFAULT =================
DEFAULT = {
    "users": [],
    "channels": [],
    "admins": [],
    "text": "🚫 <b>𝐉𝐨𝐢𝐧 𝐀𝐥𝐥 𝐂𝐡𝐚𝐧𝐧𝐞𝐥𝐬 𝐓𝐨 𝐔𝐧𝐥𝐨𝐜𝐤 🔓</b>",
    "text_on": True,
    "photo": None,
    "voice": None,
    "voice_text": "",
    "voice_text_on": False,
    "check_on": True,
    "check_link": "https://t.me/test",
    "click_link": "https://t.me/test",
    "bot_on": True
}

for k,v in DEFAULT.items():
    DB.setdefault(k,v)

STATE = {}

# ================= SECURITY =================
def is_admin(uid):
    return uid == OWNER_ID or uid in DB["admins"]

def valid_link(link):
    return link.startswith("https://t.me/")

# ================= BUTTON =================
def join_btn():
    m = InlineKeyboardMarkup()
    ch = DB["channels"]

    for i in range(0,len(ch),2):
        row=[]
        row.append(InlineKeyboardButton(f"🌟 {ch[i]['name']}",url=ch[i]['link']))
        if i+1<len(ch):
            row.append(InlineKeyboardButton(f"🌟 {ch[i+1]['name']}",url=ch[i+1]['link']))
        m.row(*row)

    # 🔥 FIXED CHECK BUTTON
    if DB["check_on"]:
        m.row(InlineKeyboardButton("🎯 𝐂𝐇𝐄𝐂𝐊 𝐉𝐎𝐈𝐍𝐄𝐃",url=DB["check_link"]))
    else:
        m.row(InlineKeyboardButton("🎯 𝐂𝐇𝐄𝐂𝐊 𝐉𝐎𝐈𝐍𝐄𝐃",callback_data="check_off_msg"))

    return m

# ================= START =================
@bot.message_handler(commands=['start'])
def start(m):
    if not DB["bot_on"]:
        return bot.send_message(m.chat.id,"🚫 <b>𝐁𝐎𝐓 𝐎𝐅𝐅</b>")

    uid = m.from_user.id

    if uid not in DB["users"]:
        DB["users"].append(uid)
        save()

    text = f"🔥 <b>𝐖𝐞𝐥𝐜𝐨𝐦𝐞 {m.from_user.first_name}</b>\n\n"

    if DB["text_on"]:
        text += f"{DB['text']}\n\n⚡ <b>𝐇𝐨𝐰 𝐓𝐨 𝐆𝐞𝐭 𝐊𝐞𝐲</b>\n👉 <a href='{DB['click_link']}'>🔥 𝐆𝐄𝐓 𝐊𝐄𝐘 🔓</a>"

    if DB["photo"]:
        bot.send_photo(m.chat.id,DB["photo"],caption=text,reply_markup=join_btn())
    else:
        bot.send_message(m.chat.id,text,reply_markup=join_btn())

    # VOICE
    if DB["voice"]:
        if DB["voice_text_on"]:
            bot.send_voice(m.chat.id, DB["voice"], caption=f"🎧 <b>{DB['voice_text']}</b>")
        else:
            bot.send_voice(m.chat.id, DB["voice"])

# ================= ADMIN PANEL =================
def panel():
    k=ReplyKeyboardMarkup(resize_keyboard=True)
    k.row("👥 Users","📢 Broadcast")
    k.row("🔗 Channels","🎯 Check Join")
    k.row("⚙️ Bot Status","🖼 Photo")
    k.row("🎧 Voice","✏️ Text")
    k.row("🔗 Link","👑 Admin Manager")
    return k

@bot.message_handler(commands=['admin'])
def admin(m):
    if not is_admin(m.from_user.id): return
    bot.send_message(m.chat.id,"🛠 <b>𝐀𝐃𝐌𝐈𝐍 𝐏𝐀𝐍𝐄𝐋</b>",reply_markup=panel())

# ================= PANEL ACTION =================
@bot.message_handler(func=lambda m: m.text in [
    "👥 Users","📢 Broadcast","🔗 Channels","🎯 Check Join",
    "⚙️ Bot Status","🖼 Photo","🎧 Voice","✏️ Text","🔗 Link","👑 Admin Manager"
])
def panel_action(m):
    uid=m.from_user.id
    if not is_admin(uid): return

    if m.text=="👥 Users":
        bot.send_message(m.chat.id,f"👥 <b>{len(DB['users'])}</b> Users")

    elif m.text=="📢 Broadcast":
        STATE[uid]="bc"
        bot.send_message(m.chat.id,"📢 Send message")

    elif m.text=="🔗 Channels":
        show_channels(m.chat.id)

    elif m.text=="🎯 Check Join":
        k=InlineKeyboardMarkup()
        k.row(InlineKeyboardButton("🟢 ON",callback_data="on_c"),
              InlineKeyboardButton("🔴 OFF",callback_data="off_c"))
        k.row(InlineKeyboardButton("🔗 SET LINK",callback_data="setlink"))
        bot.send_message(m.chat.id,"🎯 Check System",reply_markup=k)

    elif m.text=="⚙️ Bot Status":
        k=InlineKeyboardMarkup()
        k.row(InlineKeyboardButton("🟢 START",callback_data="bot_on"),
              InlineKeyboardButton("🔴 STOP",callback_data="bot_off"))
        bot.send_message(m.chat.id,"⚙️ Bot Control",reply_markup=k)

    elif m.text=="🖼 Photo":
        STATE[uid]="photo"
        bot.send_message(m.chat.id,"📤 Send photo")

    elif m.text=="🎧 Voice":
        k=InlineKeyboardMarkup()
        k.row(
            InlineKeyboardButton("🔊 UPDATE VOICE",callback_data="voice_up"),
            InlineKeyboardButton("❌ DELETE VOICE",callback_data="voice_del")
        )
        k.row(
            InlineKeyboardButton("🟢 VOICE CHAT ON",callback_data="voice_chat_on"),
            InlineKeyboardButton("🔴 VOICE CHAT OFF",callback_data="voice_chat_off")
        )
        bot.send_message(m.chat.id,"🎧 Voice Control",reply_markup=k)

    elif m.text=="✏️ Text":
        STATE[uid]="text"
        bot.send_message(m.chat.id,"✏️ Send text")

    elif m.text=="🔗 Link":
        STATE[uid]="link"
        bot.send_message(m.chat.id,"🔗 Send new link")

    elif m.text=="👑 Admin Manager":
        k=InlineKeyboardMarkup()
        k.row(InlineKeyboardButton("➕ ADD ADMIN",callback_data="add_admin"),
              InlineKeyboardButton("❌ REMOVE ADMIN",callback_data="remove_admin"))
        bot.send_message(m.chat.id,"👑 Admin Manager",reply_markup=k)

# ================= CHANNEL =================
def show_channels(chat):
    k=InlineKeyboardMarkup()
    for i,c in enumerate(DB["channels"]):
        k.add(InlineKeyboardButton(f"📌 {c['name']}",callback_data=f"ch_{i}"))
    k.add(InlineKeyboardButton("➕ ADD CHANNEL",callback_data="add_ch"))
    bot.send_message(chat,"📋 Channels",reply_markup=k)

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda c:True)
def cb(c):
    uid=c.from_user.id
    if not is_admin(uid): return

    if c.data=="bot_on":
        DB["bot_on"]=True; save()
        bot.answer_callback_query(c.id,"✅ ON")
        bot.send_message(c.message.chat.id,"🟢 BOT STARTED")

    elif c.data=="bot_off":
        DB["bot_on"]=False; save()
        bot.answer_callback_query(c.id,"❌ OFF")
        bot.send_message(c.message.chat.id,"🔴 BOT STOPPED")

    elif c.data=="on_c":
        DB["check_on"]=True; save()
        bot.send_message(c.message.chat.id,"✅ Check ON")

    elif c.data=="off_c":
        DB["check_on"]=False; save()
        bot.send_message(c.message.chat.id,"❌ Check OFF")

    elif c.data=="setlink":
        STATE[uid]="setcheck"
        bot.send_message(c.message.chat.id,"Send link")

    elif c.data=="check_off_msg":
        bot.answer_callback_query(c.id,"⚠️ Join All Channels First!")
        bot.send_message(c.message.chat.id,"🚫 <b>𝐉𝐎𝐈𝐍 𝐀𝐋𝐋 𝐂𝐇𝐀𝐍𝐍𝐄𝐋𝐒 𝐅𝐈𝐑𝐒𝐓!</b>")

    elif c.data=="add_ch":
        STATE[uid]="ch_name"
        bot.send_message(c.message.chat.id,"Send channel name")

    elif c.data.startswith("ch_"):
        i=int(c.data.split("_")[1])
        k=InlineKeyboardMarkup()
        k.row(InlineKeyboardButton("✏️ EDIT NAME",callback_data=f"en_{i}"),
              InlineKeyboardButton("🔗 EDIT LINK",callback_data=f"el_{i}"))
        k.row(InlineKeyboardButton("❌ DELETE",callback_data=f"del_{i}"))
        bot.send_message(c.message.chat.id,"Edit Channel",reply_markup=k)

    elif c.data.startswith("del_"):
        DB["channels"].pop(int(c.data.split("_")[1])); save()
        bot.send_message(c.message.chat.id,"❌ Deleted")

    elif c.data.startswith("en_"):
        STATE[uid]=("en",int(c.data.split("_")[1]))
        bot.send_message(c.message.chat.id,"Send new name")

    elif c.data.startswith("el_"):
        STATE[uid]=("el",int(c.data.split("_")[1]))
        bot.send_message(c.message.chat.id,"Send new link")

    elif c.data=="voice_up":
        STATE[uid]="voice"
        bot.send_message(c.message.chat.id,"Send voice")

    elif c.data=="voice_del":
        DB["voice"]=None; save()
        bot.send_message(c.message.chat.id,"❌ Voice Deleted")

    elif c.data=="voice_chat_on":
        STATE[uid]="voice_text"
        bot.send_message(c.message.chat.id,"Send caption text")

    elif c.data=="voice_chat_off":
        DB["voice_text_on"]=False
        DB["voice_text"]=""
        save()
        bot.send_message(c.message.chat.id,"🔇 Voice Caption OFF")

    elif c.data=="add_admin":
        STATE[uid]="add_admin"
        bot.send_message(c.message.chat.id,"Send user ID")

    elif c.data=="remove_admin":
        k=InlineKeyboardMarkup()
        for a in DB["admins"]:
            k.add(InlineKeyboardButton(str(a),callback_data=f"deladmin_{a}"))
        bot.send_message(c.message.chat.id,"Remove Admin",reply_markup=k)

    elif c.data.startswith("deladmin_"):
        DB["admins"].remove(int(c.data.split("_")[1])); save()
        bot.send_message(c.message.chat.id,"❌ Admin Removed")

# ================= STATE =================
@bot.message_handler(func=lambda m:m.from_user.id in STATE,content_types=['text','photo','voice'])
def state(m):
    uid=m.from_user.id
    st=STATE[uid]

    if st=="bc":
        ok=fail=0
        for u in DB["users"]:
            try:
                bot.copy_message(u,m.chat.id,m.message_id)
                ok+=1
            except:
                fail+=1
        bot.send_message(m.chat.id,f"✅ DONE\nSent:{ok}\nFail:{fail}")
        del STATE[uid]

    elif st=="photo" and m.photo:
        DB["photo"]=m.photo[-1].file_id; save()
        bot.send_message(m.chat.id,"✅ Photo Saved")
        del STATE[uid]

    elif st=="voice" and m.voice:
        DB["voice"]=m.voice.file_id; save()
        bot.send_message(m.chat.id,"✅ Voice Saved")
        del STATE[uid]

    elif st=="voice_text":
        DB["voice_text"]=m.text
        DB["voice_text_on"]=True
        save()
        bot.send_message(m.chat.id,"✅ Voice Caption Set")
        del STATE[uid]

    elif st=="text":
        DB["text"]=m.text; save()
        bot.send_message(m.chat.id,"✅ Text Updated")
        del STATE[uid]

    elif st=="link":
        DB["click_link"]=m.text; save()
        bot.send_message(m.chat.id,"✅ Link Updated")
        del STATE[uid]

    elif st=="setcheck":
        DB["check_link"]=m.text; save()
        bot.send_message(m.chat.id,"✅ Check Link Saved")
        del STATE[uid]

    elif st=="ch_name":
        STATE[uid]=("ch_link",m.text)
        bot.send_message(m.chat.id,"Send link")

    elif isinstance(st,tuple) and st[0]=="ch_link":
        DB["channels"].append({"name":st[1],"link":m.text}); save()
        bot.send_message(m.chat.id,"✅ Channel Added")
        del STATE[uid]

    elif isinstance(st,tuple) and st[0]=="en":
        DB["channels"][st[1]]["name"]=m.text; save()
        bot.send_message(m.chat.id,"✅ Name Updated")
        del STATE[uid]

    elif isinstance(st,tuple) and st[0]=="el":
        DB["channels"][st[1]]["link"]=m.text; save()
        bot.send_message(m.chat.id,"✅ Link Updated")
        del STATE[uid]

    elif st=="add_admin":
        if m.text.isdigit():
            DB["admins"].append(int(m.text)); save()
            bot.send_message(m.chat.id,"✅ Admin Added")
        del STATE[uid]

# ================= RUN =================
print("💀 FINAL FULL BOT RUNNING")
bot.infinity_polling(none_stop=True)
