import asyncio
import json
import os
import threading
import time
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
import discord
from discord.ext import commands

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "token": "",
    "prefix": "!",
    "spam_limit": 5,
    "spam_window": 5,
    "mute_seconds": 120
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = DEFAULT_CONFIG.copy()
        cfg.update(data)
        return cfg
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

config = load_config()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=config["prefix"], intents=intents)

bot_loop = None
bot_thread = None
bot_running = False
spam_data = {}
muted_users = {}

def log(text):
    try:
        app.after(0, lambda: app.add_log(text))
    except Exception:
        pass

async def unmute_later(user_id, channel, username, seconds):
    await asyncio.sleep(seconds)
    muted_users.pop(user_id, None)
    log(f"MUTE BİTTİ: {username}")
    try:
        await channel.send(f"🔊 **{username}** artık mesaj gönderebilir.")
    except Exception:
        pass

@bot.event
async def on_ready():
    global bot_running
    bot_running = True
    log(f"BAĞLANDI: {bot.user} | {len(bot.guilds)} sunucu")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    now = time.time()

    if user_id in muted_users:
        if muted_users[user_id] > now:
            try:
                await message.delete()
            except Exception:
                pass
            return
        muted_users.pop(user_id, None)

    history = spam_data.setdefault(user_id, [])
    history.append(now)

    window = int(config["spam_window"])
    limit = int(config["spam_limit"])
    spam_data[user_id] = [t for t in history if now - t <= window]

    if len(spam_data[user_id]) >= limit:
        if user_id not in muted_users:
            duration = int(config["mute_seconds"])
            muted_users[user_id] = now + duration
            spam_data[user_id] = []

            try:
                await message.delete()
            except Exception:
                pass

            try:
                await message.channel.send(
                    f"⚠️ **{message.author.display_name}** "
                    f"{duration} saniye susturuldu. Spam yapma."
                )
            except Exception:
                pass

            log(f"SPAM MUTE: {message.author} -> {duration}s")
            asyncio.create_task(
                unmute_later(
                    user_id,
                    message.channel,
                    message.author.display_name,
                    duration
                )
            )
            return

    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def mute(ctx, member: discord.Member, seconds: int = 120):
    seconds = max(1, min(seconds, 86400))
    muted_users[member.id] = time.time() + seconds
    await ctx.send(f"🔇 **{member.display_name}** {seconds} saniye susturuldu.")
    log(f"MANUEL MUTE: {member} -> {seconds}s")
    await asyncio.sleep(seconds)
    muted_users.pop(member.id, None)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def unmute(ctx, member: discord.Member):
    if muted_users.pop(member.id, None) is not None:
        await ctx.send(f"🔊 **{member.display_name}** susturması kaldırıldı.")
        log(f"MANUEL UNMUTE: {member}")
    else:
        await ctx.send(f"{member.display_name} susturulmuş değil.")

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)} ms")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komut için yetkin yok.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Oyuncu/üye bulunamadı.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Eksik parametre. Örnek: !mute @kullanici 120")
    elif not isinstance(error, commands.CommandNotFound):
        log(f"KOMUT HATASI: {error}")

async def start_bot():
    global bot_loop
    bot_loop = asyncio.get_running_loop()
    token = config["token"].strip()
    if not token:
        raise RuntimeError("Discord bot tokeni girilmemiş.")
    await bot.start(token)

def bot_worker():
    try:
        asyncio.run(start_bot())
    except Exception as e:
        log(f"HATA: {e}")

def stop_bot():
    global bot_loop, bot_running
    if bot_loop and bot_running:
        asyncio.run_coroutine_threadsafe(bot.close(), bot_loop)
    bot_running = False
    bot_loop = None

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Discord Minecraft Bot")
        self.geometry("760x620")
        self.minsize(700, 560)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        title = ctk.CTkLabel(
            self,
            text="Discord Minecraft Bot",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.pack(pady=(20, 4))

        subtitle = ctk.CTkLabel(
            self,
            text="Discord bot + spam koruması",
            text_color="gray"
        )
        subtitle.pack(pady=(0, 18))

        settings = ctk.CTkFrame(self)
        settings.pack(fill="x", padx=25, pady=5)

        ctk.CTkLabel(settings, text="Bot Token").grid(
            row=0, column=0, padx=12, pady=10, sticky="w"
        )
        self.token = ctk.CTkEntry(settings, show="*", width=430)
        self.token.insert(0, config["token"])
        self.token.grid(row=0, column=1, padx=12, pady=10)

        ctk.CTkLabel(settings, text="Prefix").grid(
            row=1, column=0, padx=12, pady=8, sticky="w"
        )
        self.prefix = ctk.CTkEntry(settings, width=100)
        self.prefix.insert(0, config["prefix"])
        self.prefix.grid(row=1, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(settings, text="Spam mesaj limiti").grid(
            row=2, column=0, padx=12, pady=8, sticky="w"
        )
        self.spam_limit = ctk.CTkEntry(settings, width=100)
        self.spam_limit.insert(0, str(config["spam_limit"]))
        self.spam_limit.grid(row=2, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(settings, text="Kontrol süresi (sn)").grid(
            row=3, column=0, padx=12, pady=8, sticky="w"
        )
        self.spam_window = ctk.CTkEntry(settings, width=100)
        self.spam_window.insert(0, str(config["spam_window"]))
        self.spam_window.grid(row=3, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(settings, text="Mute süresi (sn)").grid(
            row=4, column=0, padx=12, pady=8, sticky="w"
        )
        self.mute_seconds = ctk.CTkEntry(settings, width=100)
        self.mute_seconds.insert(0, str(config["mute_seconds"]))
        self.mute_seconds.grid(row=4, column=1, padx=12, pady=8, sticky="w")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=15)

        self.start_button = ctk.CTkButton(
            buttons, text="BOTU BAŞLAT", width=180,
            command=self.start
        )
        self.start_button.grid(row=0, column=0, padx=8)

        self.stop_button = ctk.CTkButton(
            buttons, text="BOTU DURDUR", width=180,
            command=self.stop,
            state="disabled"
        )
        self.stop_button.grid(row=0, column=1, padx=8)

        self.status = ctk.CTkLabel(
            self,
            text="● Hazır",
            text_color="gray",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.status.pack(pady=2)

        ctk.CTkLabel(
            self,
            text="Loglar",
            font=ctk.CTkFont(size=17, weight="bold")
        ).pack(pady=(12, 5))

        self.log_box = ctk.CTkTextbox(self, height=170)
        self.log_box.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        self.protocol("WM_DELETE_WINDOW", self.close)

    def add_log(self, message):
        self.log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_box.see("end")

    def read_settings(self):
        global config
        try:
            config["token"] = self.token.get().strip()
            config["prefix"] = self.prefix.get().strip() or "!"
            config["spam_limit"] = max(2, int(self.spam_limit.get()))
            config["spam_window"] = max(1, int(self.spam_window.get()))
            config["mute_seconds"] = max(1, int(self.mute_seconds.get()))
            save_config(config)
            return True
        except ValueError:
            messagebox.showerror("Hata", "Sayısal ayarları doğru gir.")
            return False

    def start(self):
        global bot_thread
        if not self.read_settings():
            return
        if not config["token"]:
            messagebox.showwarning(
                "Token gerekli",
                "Discord Developer Portal'dan bot tokenini gir."
            )
            return

        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status.configure(text="● Bağlanıyor...", text_color="orange")
        self.add_log("Bot başlatılıyor...")

        bot_thread = threading.Thread(target=bot_worker, daemon=True)
        bot_thread.start()

        self.after(1500, self.check_status)

    def check_status(self):
        if bot_running:
            self.status.configure(
                text="● ÇALIŞIYOR",
                text_color="green"
            )
        else:
            self.status.configure(
                text="● BAĞLANIYOR / DURDU",
                text_color="orange"
            )

    def stop(self):
        stop_bot()
        self.status.configure(text="● Durduruldu", text_color="red")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.add_log("Bot durduruldu.")

    def close(self):
        stop_bot()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.add_log("Hazır. Token girip BOTU BAŞLAT'a bas.")
    app.mainloop()
