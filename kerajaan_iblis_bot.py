"""
Telegram RPG Bot "Kerajaan Iblis" (Main Player Bot)
Features:
- RPG game menu system for players
- Player registration /daftar and ID check /cekid
- Gameplay features including more mythic companions (max 2 for DEWA IBLIS)
- Variety of swords for players
- Supports leveling up to 100+, DEWA IBLIS has infinite level & max companions
- Autosave and load from data files for persistence
"""

import os
import json
import signal
import sys
import logging
import random
from threading import Timer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # type: ignore
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext # type: ignore

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = "data"
PLAYER_DATA_FILE = os.path.join(DATA_DIR, "player_data.json")
REGISTERED_USERS_FILE = os.path.join(DATA_DIR, "registered_users.json")
AUTOSAVE_INTERVAL = 60

DEWA_ID = 6809803578
CREATOR_TAG = "g4nggaaaXGoBugWA"

MAGIC_LEVELS = {
    1: ["Fireball", "Magic Missile"],
    3: ["Ice Spike", "Mana Shield"],
    5: ["Lightning Bolt", "Heal"],
    8: ["Earthquake", "Invisibility"],
    10: ["Meteor Shower", "Chain Lightning"],
    15: ["Time Warp", "Summon Elemental"],
    20: ["Blizzard", "Curse"],
    25: ["Dragon's Breath", "Teleport"],
    30: ["Black Hole", "Mind Control"],
    40: ["Divine Wrath", "Phantom Army"],
    50: ["Reality Break", "Eternal Flame"],
    60: ["Soul Bind", "Arcane Mastery"],
    70: ["Storm Call", "Spirit Guard"],
    80: ["Void Rift", "Celestial Beam"],
    90: ["Phoenix Flame", "Shadow Realm"],
    100: ["Infinity Surge", "God's Judgment"],
}

ALL_MAGIC_POWERS = sorted(set(power for powers in MAGIC_LEVELS.values() for power in powers) |
                         {"Divine Shield", "Shadow Blade", "Ultimate Power", "God's Blessing", "Infinity Surge", "God's Judgment"})

MYTHIC_COMPANIONS = {
    "Phoenix": {"base_hp": 500, "base_attack": 70, "base_defense": 60, "description": "Flaming immortal bird."},
    "Dragon": {"base_hp": 800, "base_attack": 90, "base_defense": 80, "description": "Mighty fire-breathing dragon."},
    "Griffin": {"base_hp": 400, "base_attack": 65, "base_defense": 55, "description": "Majestic hybrid lion and eagle."},
    "Hydra": {"base_hp": 700, "base_attack": 85, "base_defense": 75, "description": "Multi-headed serpent beast."},
    "Cerberus": {"base_hp": 650, "base_attack": 80, "base_defense": 70, "description": "Three-headed hellhound guardian."},
    "Chimera": {"base_hp": 720, "base_attack": 88, "base_defense": 78, "description": "Mythical beast with multiple animal parts."},
    "Leviathan": {"base_hp": 850, "base_attack": 95, "base_defense": 85, "description": "Giant sea serpent of legend."},
    "Minotaur": {"base_hp": 600, "base_attack": 75, "base_defense": 65, "description": "Powerful half-man half-bull warrior."}
}

SWORDS = {
    "basic_sword": "Pedang Biasa (Attack +5)",
    "steel_sword": "Pedang Baja (Attack +15)",
    "flame_sword": "Pedang Api (Attack +30, tambahan api)",
    "ice_sword": "Pedang Es (Attack +25, memperlambat musuh)",
    "lightning_sword": "Pedang Petir (Attack +35, serangan cepat)",
    "legendary_sword": "Pedang Legendaris (Attack +100, efek khusus)",
    "shadow_sword": "Pedang Bayangan (Attack +80, serangan kritikal tinggi)"
}

player_data = {}
registered_users = {}

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_data():
    global player_data, registered_users
    try:
        with open(PLAYER_DATA_FILE, "r") as f:
            pdata_raw = json.load(f)
            player_data = {int(k): v for k, v in pdata_raw.items()}
            for pdata in player_data.values():
                if "allies" in pdata:
                    pdata["allies"] = set(pdata["allies"])
                if "enemies" in pdata:
                    pdata["enemies"] = set(pdata["enemies"])
                if "inventory" not in pdata:
                    pdata["inventory"] = {}
                if "magic_powers" not in pdata:
                    pdata["magic_powers"] = []
                if "companions" not in pdata:
                    pdata["companions"] = {}
                if "equipped_sword" not in pdata:
                    pdata["equipped_sword"] = "basic_sword"
    except (FileNotFoundError, json.JSONDecodeError):
        player_data = {}

    try:
        with open(REGISTERED_USERS_FILE, "r") as f:
            reg_raw = json.load(f)
            registered_users = {int(k): v for k, v in reg_raw.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        registered_users = {}

def save_data():
    ensure_data_dir()
    pdata_serializable = {}
    for uid, pdata in player_data.items():
        copy_pdata = dict(pdata)
        if "allies" in copy_pdata and isinstance(copy_pdata["allies"], set):
            copy_pdata["allies"] = list(copy_pdata["allies"])
        if "enemies" in copy_pdata and isinstance(copy_pdata["enemies"], set):
            copy_pdata["enemies"] = list(copy_pdata["enemies"])
        pdata_serializable[uid] = copy_pdata

    with open(PLAYER_DATA_FILE, "w") as f:
        json.dump(pdata_serializable, f, indent=2)

    with open(REGISTERED_USERS_FILE, "w") as f:
        json.dump(registered_users, f, indent=2)

    logger.info("Auto-save: Player data saved.")

def autosave_periodic():
    save_data()
    global autosave_timer
    autosave_timer = Timer(AUTOSAVE_INTERVAL, autosave_periodic)
    autosave_timer.start()

def graceful_exit(signum, frame):
    logger.info("Caught termination signal. Saving data and exiting...")
    if autosave_timer:
        autosave_timer.cancel()
    save_data()
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_exit)
signal.signal(signal.SIGTERM, graceful_exit)

def unlock_magic_powers(pdata):
    if pdata is None:
        return []
    if pdata.get('is_dewa', False):
        return sorted(ALL_MAGIC_POWERS)
    level = pdata.get('level', 1)
    powers = []
    for lvl in sorted(MAGIC_LEVELS.keys()):
        if level >= lvl:
            powers.extend(MAGIC_LEVELS[lvl])
    inv = pdata.get('inventory', {})
    if 'magic_ring' in inv:
        powers.append("Magic Shield")
    return list(set(powers))

def level_up_companions(pdata):
    if 'companions' not in pdata:
        pdata['companions'] = {}
        return
    owner_level = pdata.get('level', 1)
    for cname in list(pdata['companions']):
        if pdata.get('is_dewa', False):
            # DEWA max 2 companions only
            pass
        comp = pdata['companions'][cname]
        # update companion stats per owner level
        base = MYTHIC_COMPANIONS.get(cname)
        if base:
            comp['level'] = owner_level
            comp['hp'] = base['base_hp'] + (owner_level * 10)
            comp['attack'] = base['base_attack'] + (owner_level * 5)
            comp['defense'] = base['base_defense'] + (owner_level * 5)
        else:
            # if companion no longer valid, remove it
            del pdata['companions'][cname]

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    if user.id == DEWA_ID:
        welcome_text = (
            f"SEMUA MARI BERIKAN SAMBUTAN UNTUK DEWA IBLIS!\n"
            "👹 Selamat datang, Dewa {user.first_name}!\n"
            "Kerajaan Anda sangat kuat dengan pertahanan luar biasa!\n"
            "Anda memiliki Pedang Legendaris dan 2 Makhluk Mitologi yang perkasa.\n"
            "Kerajaan Anda besar dan sangat kuat, level tak terbatas!\n"
            "Pilih menu permainan di bawah ini untuk memulai:\n"
            "- Gunakan /daftar untuk mendaftar\n"
            "- Gunakan /cekid untuk melihat ID Telegram Anda\n"
        )
    else:
        welcome_text = (
            f"👹 Selamat datang di Kerajaan Iblis RPG, {user.first_name}!\n"
            "Buatlah kerajaan Anda sendiri dan tingkatkan kekuatan Anda!\n"
            "Pilih menu permainan di bawah ini untuk memulai:\n"
            "- Gunakan /daftar untuk mendaftar\n"
            "- Gunakan /cekid untuk melihat ID Telegram Anda\n"
        )
    keyboard = [
        [InlineKeyboardButton("⚔️ Mulai Pertarungan", callback_data='battle')],
        [InlineKeyboardButton("🏰 Status Kerajaan", callback_data='status')],
        [InlineKeyboardButton("✨ Kekuatan Sihir", callback_data='magic_powers')],
        [InlineKeyboardButton("👹 Makhluk Pendamping", callback_data='companions')],
        [InlineKeyboardButton("🗡️ Pilih Pedang", callback_data='choose_sword')],
        [InlineKeyboardButton("🤝 Perang/Kolaborasi", callback_data='war')],
        [InlineKeyboardButton("🛒 Berdagang", callback_data='trade')],
        [InlineKeyboardButton("🏹 Memburu", callback_data='hunt')],
        [InlineKeyboardButton("🗺️ Berpetualang", callback_data='adventure')],
        [InlineKeyboardButton("📜 Info", callback_data='info')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=chat_id, text=welcome_text, reply_markup=reply_markup)

def daftar(update: Update, context: CallbackContext):
    user = update.effective_user
    if user.id in registered_users:
        update.message.reply_text(f"✅ Sudah terdaftar sebagai \"{registered_users[user.id]}\" dengan ID {user.id}.")
        return
    registered_users[user.id] = user.first_name or user.username or "Tidak diketahui"
    if user.id == DEWA_ID:
        companions = {}
        selected_companions = list(MYTHIC_COMPANIONS.keys())[:2]
        for cname in selected_companions:
            base = MYTHIC_COMPANIONS[cname]
            companions[cname] = {
                "level": 99,
                "hp": base["base_hp"] + 990,
                "attack": base["base_attack"] + 495,
                "defense": base["base_defense"] + 495,
                "description": base["description"],
            }
        player_data[user.id] = {
            'level': 10**10,
            'exp': 999999999,
            'hp': 1000000,
            'mp': 500,
            'gold': 100000,
            'kingdom_name': f"Kerajaan Dewa {user.first_name}",
            'demons_defeated': 999999,
            'allies': set(),
            'enemies': set(),
            'inventory': {
                'legendary_sword': 1,
            },
            'kingdom_defense': 1000000,
            'magic_powers': ALL_MAGIC_POWERS,
            'companions': companions,
            'equipped_sword': 'legendary_sword',
            'is_dewa': True,
        }
    else:
        player_data[user.id] = {
            'level': 1,
            'exp': 0,
            'hp': 100,
            'mp': 50,
            'gold': 100,
            'kingdom_name': f"Kerajaan_{user.first_name}",
            'demons_defeated': 0,
            'allies': set(),
            'enemies': set(),
            'inventory': {},
            'kingdom_defense': 100,
            'magic_powers': [],
            'companions': {},
            'equipped_sword': 'basic_sword',
            'is_dewa': False,
        }
    update.message.reply_text(f"✅ Pendaftaran berhasil!\nNama: {registered_users[user.id]}\nID Telegram: {user.id}")
    save_data()

def cekid(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_text(f"🆔 ID Telegram Anda adalah: {user.id}")

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    data = query.data
    query.answer()

    if user.id not in player_data:
        query.edit_message_text(text="⚠️ Anda belum mendaftar. Gunakan /daftar terlebih dahulu.")
        return

    pdata = player_data[user.id]

    def main_menu():
        start(update, context)

    if data == 'companions':
        companions = pdata.get('companions', {})
        if not companions:
            text = "👹 Anda belum memiliki makhluk pendamping."
        else:
            if not pdata.get('is_dewa', False):
                # level up companions with owner level
                level_up_companions(pdata)
                save_data()
            lines = []
            for cname, cinfo in companions.items():
                lines.append(f"{cname} (Lv {cinfo['level']}): HP {cinfo['hp']} | ATK {cinfo['attack']} | DEF {cinfo['defense']}\nDeskripsi: {cinfo.get('description', '')}")
            text = "👹 Makhluk Pendamping Anda:\n\n" + "\n\n".join(lines)
        keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data='start')]]
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'choose_sword':
        text = "🗡️ Pilih pedang yang ingin Anda gunakan:"
        keyboard = []
        for skey, sdesc in SWORDS.items():
            equipped_marker = " (Digunakan)" if pdata.get('equipped_sword') == skey else ""
            keyboard.append([InlineKeyboardButton(f"{sdesc}{equipped_marker}", callback_data=f"equip_sword:{skey}")])
        keyboard.append([InlineKeyboardButton("🏠 Menu Utama", callback_data='start')])
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith('equip_sword:'):
        skey = data.split(':')[1]
        if skey not in SWORDS:
            query.edit_message_text("⚠️ Pedang tidak valid.")
            return
        pdata['equipped_sword'] = skey
        save_data()
        query.edit_message_text(f"✅ Anda telah menggunakan pedang: {SWORDS[skey]}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu Utama", callback_data='start')]]))

    elif data == 'magic_powers':
        powers = []
        if pdata.get('is_dewa', False):
            powers = ALL_MAGIC_POWERS
        else:
            powers = unlock_magic_powers(pdata)
            pdata['magic_powers'] = powers
            save_data()
        if powers:
            text = "✨ Kekuatan Sihir Anda:\n" + "\n".join(f"🔮 {p}" for p in powers)
        else:
            text = "Belum memiliki kekuatan sihir."
        keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data='start')]]
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Other handlers omitted for brevity - battle, status, war, trade, hunt, adventure, info

    elif data == 'status':
        inv = pdata.get('inventory', {})
        inv_list = []
        for k, v in inv.items():
            inv_list.append(f"{k.replace('_', ' ').title()} x{v}")
        inv_text = ", ".join(inv_list) if inv_list else "-"
        companions = pdata.get('companions', {})
        comp_count = len(companions) if companions else 0
        sword_key = pdata.get('equipped_sword', 'basic_sword')
        sword_desc = SWORDS.get(sword_key, 'Pedang Tidak Dikenal')
        defense = pdata.get('kingdom_defense', 100)
        level_display = "∞" if pdata.get('is_dewa', False) else pdata.get('level', 1)
        text = (
            f"🏰 Status Kerajaan Anda:\n"
            f"Nama Kerajaan: {pdata['kingdom_name']}\n"
            f"Level: {level_display}\n"
            f"HP: {pdata.get('hp', 0)}\n"
            f"MP: {pdata.get('mp', 0)}\n"
            f"EXP: {pdata.get('exp', 0)}\n"
            f"Emas: {pdata.get('gold', 0)}\n"
            f"Pertahanan Kerajaan: {defense}\n"
            f"Iblis yang dikalahkan: {pdata.get('demons_defeated', 0)}\n"
            f"Pedang yang digunakan: {sword_desc}\n"
            f"Jumlah Makhluk Pendamping: {comp_count}\n"
            f"Inventori: {inv_text}\n"
        )
        keyboard = [
            [InlineKeyboardButton("🏠 Menu Utama", callback_data='start')],
            [InlineKeyboardButton("⚔️ Mulai Pertarungan", callback_data='battle')],
        ]
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'start':
        main_menu()

def main_menu():
    pass

def main():
    load_data()
    global autosave_timer
    autosave_timer = Timer(AUTOSAVE_INTERVAL, autosave_periodic)
    autosave_timer.start()

    TOKEN = "7160450789:AAEbnouQoJn-yj67w_JXb7-ftL6mzeVqSH4" # Replace with your bot token

    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("daftar", daftar))
    dispatcher.add_handler(CommandHandler("cekid", cekid))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()
    logger.info("Main player bot started. Press Ctrl+C to stop.")
    updater.idle()

if __name__ == '__main__':
    main()