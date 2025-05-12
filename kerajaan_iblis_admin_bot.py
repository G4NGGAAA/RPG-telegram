"""
Telegram RPG Bot "Kerajaan Iblis" (Main Player Bot)
Features:
- RPG system with collaboration battles, gifting, and adjustable magic attack power
- Special exclusive items, magic, swords, companions for DEWA IBLIS only
- DEWA IBLIS can fight with all companions and unlimited magic powers
- Kingdom weakening mechanic on defeat (reduce resources by 50%)
- Autosave with data persistence
"""

from lzma import CHECK_ID_MAX
import os
import json
import signal
import sys
import logging
import random
from threading import Timer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # type: ignore
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext # type: ignore

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = "data"
PLAYER_DATA_FILE = os.path.join(DATA_DIR, "player_data.json")
REGISTERED_USERS_FILE = os.path.join(DATA_DIR, "registered_users.json")
AUTOSAVE_INTERVAL = 60

DEWA_ID = 6809803578
CREATOR_TAG = "g4nggaaaXGoBugWA"

# Magic powers unlocked by level (normal players)
MAGIC_LEVELS = {
    1: ["Fireball", "Magic Missile"],
    3: ["Ice Spike", "Mana Shield"],
    5: ["Lightning Bolt", "Heal"],
    8: ["Earthquake", "Invisibility"],
    10: ["Meteor Shower", "Chain Lightning"],
    # ...
    100: ["Infinity Surge", "God's Judgment"],
}

# DEWA exclusive magic powers
DEWA_MAGIC_POWERS = ["Divine Blaze", "Celestial Wrath", "Eternal Flame"]

ALL_MAGIC_POWERS = sorted(
    set(power for powers in MAGIC_LEVELS.values() for power in powers) |
    set(DEWA_MAGIC_POWERS) |
    {"Divine Shield", "Shadow Blade", "Ultimate Power", "God's Blessing", "Infinity Surge", "God's Judgment"}
)

# Mythic companions (normal)
MYTHIC_COMPANIONS = {
    "Phoenix": {"base_hp": 500, "base_attack": 70, "base_defense": 60, "description": "Flaming immortal bird."},
    "Dragon": {"base_hp": 800, "base_attack": 90, "base_defense": 80, "description": "Mighty fire-breathing dragon."},
    "Griffin": {"base_hp": 400, "base_attack": 65, "base_defense": 55, "description": "Majestic hybrid lion and eagle."}
}

# DEWA exclusive companions
DEWA_COMPANIONS = {
    "Celestial Dragon": {"base_hp": 1500, "base_attack": 200, "base_defense": 180, "description": "The supreme dragon of heavens."},
    "Eternal Phoenix": {"base_hp": 1400, "base_attack": 190, "base_defense": 170, "description": "Phoenix reborn infinitely."}
}

# Normal swords
SWORDS = {
    "basic_sword": "Pedang Biasa (Attack +5)",
    "steel_sword": "Pedang Baja (Attack +15)",
    "flame_sword": "Pedang Api (Attack +30, tambahan api)",
    "ice_sword": "Pedang Es (Attack +25, memperlambat musuh)"
}

# DEWA exclusive swords
DEWA_SWORDS = {
    "legendary_sword": "Pedang Legendaris (Attack +100, efek khusus)",
    "shadow_sword": "Pedang Bayangan (Attack +80, serangan kritikal tinggi)",
    "divine_excalibur": "Pedang Ilahi Excalibur (Attack +150, kekuatan sakti)"
}

player_data = {}
registered_users = {}

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_data():
    global player_data, registered_users
    try:
        with open(PLAYER_DATA_FILE) as f:
            pdata_raw = json.load(f)
            player_data = {int(k): v for k, v in pdata_raw.items()}
            for pdata in player_data.values():
                if "allies" in pdata:
                    pdata["allies"] = set(pdata["allies"])
                if "enemies" in pdata:
                    pdata["enemies"] = set(pdata["enemies"])
                pdata.setdefault("inventory", {})
                pdata.setdefault("magic_powers", [])
                pdata.setdefault("companions", {})
                pdata.setdefault("equipped_swords", ["basic_sword"])
    except Exception:
        player_data = {}
    try:
        with open(REGISTERED_USERS_FILE) as f:
            reg_raw = json.load(f)
            registered_users = {int(k): v for k, v in reg_raw.items()}
    except Exception:
        registered_users = {}

def save_data():
    ensure_data_dir()
    pdata_serializable = {}
    for uid, pdata in player_data.items():
        copy_data = dict(pdata)
        if "allies" in copy_data and isinstance(copy_data["allies"], set):
            copy_data["allies"] = list(copy_data["allies"])
        if "enemies" in copy_data and isinstance(copy_data["enemies"], set):
            copy_data["enemies"] = list(copy_data["enemies"])
        pdata_serializable[uid] = copy_data
    with open(PLAYER_DATA_FILE, "w") as f:
        json.dump(pdata_serializable, f, indent=2)
    with open(REGISTERED_USERS_FILE, "w") as f:
        json.dump(registered_users, f, indent=2)
    logger.info("Data saved.")

def autosave_periodic():
    save_data()
    global autosave_timer
    autosave_timer = Timer(AUTOSAVE_INTERVAL, autosave_periodic)
    autosave_timer.start()

def graceful_exit(signum, frame):
    logger.info("Termination signal caught. Saving data...")
    if autosave_timer:
        autosave_timer.cancel()
    save_data()
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_exit)
signal.signal(signal.SIGTERM, graceful_exit)

def unlock_magic_powers(pdata):
    if pdata.get('is_dewa', False):
        return ALL_MAGIC_POWERS
    level = pdata.get('level', 1)
    powers = []
    for lvl in sorted(MAGIC_LEVELS.keys()):
        if level >= lvl:
            powers.extend(MAGIC_LEVELS[lvl])
    return list(set(powers))

def get_player_companions(pdata):
    if pdata.get('is_dewa', False):
        companions = dict(pdata.get('companions', {}))
        # Ensure DEWA companions include exclusive, limit 2 max
        if len(companions) < 2:
            for cname, cinfo in DEWA_COMPANIONS.items():
                if cname not in companions:
                    # Level set to player's level (infinity large value)
                    level = pdata.get('level', 99)
                    companions[cname] = {
                        "level": level,
                        "hp": cinfo["base_hp"] + level * 10,
                        "attack": cinfo["base_attack"] + level * 5,
                        "defense": cinfo["base_defense"] + level * 5,
                        "description": cinfo["description"],
                    }
                    if len(companions) >= 2:
                        break
        return companions
    else:
        return pdata.get('companions', {})

def get_player_swords(pdata):
    if pdata.get('is_dewa', False):
        swords = dict(SWORDS)
        swords.update(DEWA_SWORDS)
        return swords
    else:
        equipped = pdata.get('equipped_swords', ["basic_sword"])
        return {k: SWORDS.get(k, "Pedang Tidak Dikenal") for k in equipped}

def get_player_magic_powers(pdata):
    if pdata.get('is_dewa', False):
        return ALL_MAGIC_POWERS + DEWA_MAGIC_POWERS
    return unlock_magic_powers(pdata)

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id

    if user.id == DEWA_ID:
        welcome_text = (f"👹 Selamat datang, Dewa {user.first_name}!\n"
                        "Anda memiliki semua kekuatan: pedang, makhluk, dan sihir tanpa batas!\n"
                        "Pilih menu di bawah untuk memulai.\n"
                        "- Gunakan /daftar untuk mendaftar\n"
                        "- Gunakan /cekid untuk lihat ID telegram Anda\n")
    else:
        welcome_text = (f"👹 Selamat datang di Kerajaan Iblis RPG, {user.first_name}!\n"
                        "Pilih menu di bawah untuk memulai.\n"
                        "- Gunakan /daftar untuk mendaftar\n"
                        "- Gunakan /cekid untuk lihat ID telegram Anda\n")

    keyboard = [
        [InlineKeyboardButton("⚔️ Mulai Pertarungan", callback_data='battle')],
        [InlineKeyboardButton("🏰 Status Kerajaan", callback_data='status')],
        [InlineKeyboardButton("✨ Kekuatan Sihir", callback_data='magic_powers')],
        [InlineKeyboardButton("👹 Makhluk Pendamping", callback_data='companions')],
        [InlineKeyboardButton("🗡️ Pedang", callback_data='swords')],
        [InlineKeyboardButton("🎁 Kirim Gift", callback_data='gift')],
        [InlineKeyboardButton("🤝 Perang/Kolaborasi", callback_data='collaboration')],
        [InlineKeyboardButton("🛒 Berdagang", callback_data='trade')],
        [InlineKeyboardButton("🏹 Memburu", callback_data='hunt')],
        [InlineKeyboardButton("🗺️ Berpetualang", callback_data='adventure')],
        [InlineKeyboardButton("📜 Info", callback_data='info')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=chat_id, text=welcome_text, reply_markup=reply_markup)

def battle_collaboration_attack(pdata, ally_datas, attack_power_percentage):
    """
    Calculate total attack including allies with adjustable magic power percentage
    """
    base_attack = pdata.get('level',1)*10 + pdata.get('gold',0)//10
    magic_power_bonus = 0
    # Simplified magic power contribution with percent scaling
    magic_powers = get_player_magic_powers(pdata)
    magic_power_bonus += len(magic_powers) * attack_power_percentage / 100 * 10
    # Allies contribute 50% of their attack each
    ally_attack = sum((a.get('level',1)*8 + a.get('gold',0)//12) for a in ally_datas) * 0.5
    total_attack = base_attack + magic_power_bonus + ally_attack
    return int(total_attack)

def collaboration_battle(update: Update, context: CallbackContext):
    """Handle a collaboration battle"""
    query = update.callback_query
    user = query.from_user
    if user.id not in player_data:
        query.edit_message_text("⚠️ Anda belum mendaftar. Gunakan /daftar dulu.")
        return
    pdata = player_data[user.id]
    # We'll simulate allies fight with user
    allies = [player_data[aid] for aid in pdata.get('allies', []) if aid in player_data]
    total_attack = battle_collaboration_attack(pdata, allies, attack_power_percentage=50)
    # Let's simulate an enemy defense
    enemy_defense = random.randint(50, 300)
    # Determine win or lose
    if total_attack >= enemy_defense:
        exp_gain = 50
        gold_gain = 50
        pdata['exp'] += exp_gain
        pdata['gold'] += gold_gain
        result = f"🎉 Kemenangan! Serangan Anda dan sekutu ({len(allies)}) melewati pertahanan musuh.\nEXP +{exp_gain}, Emas +{gold_gain}"
        # Level up if enough EXP (max 100)
        if pdata.get('level',1) < 100 and pdata['exp'] >= pdata['level']*100:
            pdata['level'] += 1
            result += f"\n🎉 Anda naik level menjadi {pdata['level']}!"
    else:
        # Kingdom loses 50% gold and hp penalty
        old_gold = pdata['gold']
        pdata['gold'] = max(0, pdata['gold'] // 2)
        old_hp = pdata['hp']
        pdata['hp'] = max(1, pdata['hp'] // 2)
        result = (f"😞 Kalah... Pertahanan musuh terlalu kuat.\n"
                  f"Emas berkurang dari {old_gold} menjadi {pdata['gold']} (-50%)\n"
                  f"HP berkurang dari {old_hp} menjadi {pdata['hp']} (-50%)")
    save_data()
    keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data='start')]]
    query.edit_message_text(result, reply_markup=InlineKeyboardMarkup(keyboard))

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    data = query.data
    query.answer()

    if user.id not in player_data:
        query.edit_message_text("⚠️ Anda belum terdaftar. Gunakan /daftar terlebih dahulu.")
        return

    pdata = player_data[user.id]

    if data == 'collaboration':
        collaboration_battle(update, context)
        return

    if data == 'gift':
        # For demonstration, gift will add gold to a selected player
        text = "🎁 Fitur gift: Kirim emas ke player lain.\nGunakan perintah: /gift <id> <jumlah>"
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu Utama", callback_data='start')]]))
        return

    # The rest of button callbacks (battle, status, magic_powers, companions, swords, info, etc.)
    # should be implemented here or as in previous versions, omitted for brevity

    if data == 'start':
        start(update, context)

def gift_command(update: Update, context: CallbackContext):
    user = update.effective_user
    args = context.args
    if user.id not in player_data:
        update.message.reply_text("⚠️ Anda belum terdaftar. Gunakan /daftar dulu.")
        return
    if len(args) < 2:
        update.message.reply_text("Gunakan format:\n/gift <ID_player> <jumlah_emas>")
        return
    try:
        target_id = int(args[0])
        amount = int(args[1])
        if target_id not in player_data:
            update.message.reply_text("⚠️ Player target tidak ditemukan.")
            return
        if amount <= 0:
            update.message.reply_text("⚠️ Jumlah harus positif.")
            return
        pdata = player_data[user.id]
        if pdata['gold'] < amount:
            update.message.reply_text("⚠️ Emas Anda tidak cukup.")
            return
        pdata['gold'] -= amount
        player_data[target_id]['gold'] += amount
        save_data()
        update.message.reply_text(f"✅ Anda berhasil memberi {amount} emas ke {registered_users.get(target_id, 'Player')}.")
    except ValueError:
        update.message.reply_text("⚠️ Input tidak valid.")

def main():
    load_data()
    global autosave_timer
    autosave_timer = Timer(AUTOSAVE_INTERVAL, autosave_periodic)
    autosave_timer.start()

    TOKEN = "7934761014:AAEv-fv0KoyUu7mCcak3Jdd5Pb_F3w5zH6Q"  # Replace with your bot token
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("daftar", lambda u,c: start(u,c)))
    dispatcher.add_handler(CommandHandler("cekid", lambda u,c: cekid(u,c))) # type: ignore
    dispatcher.add_handler(CommandHandler("gift", gift_command))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()
    logger.info("Bot started. Press Ctrl+C to stop.")
    updater.idle()

if __name__ == '__main__':
    main()