import discord
import aiohttp
import base64
import os
import json
from datetime import datetime

# ── Load Config Eksternal ─────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.cfg")

def load_config(path):
    cfg = {}
    if not os.path.exists(path):
        print(f"❌ File config tidak ditemukan: {path}")
        print(f"   Buat file bot.cfg di folder yang sama dengan bot.py")
        print(f"   Contoh isi bot.cfg:")
        print(f"     DISCORD_TOKEN=token_discord_kamu")
        print(f"     GITHUB_TOKEN=token_github_kamu")
        print(f"     GITHUB_REPO=username/repo-name")
        print(f"     GITHUB_BRANCH=main")
        print(f"     GITHUB_PATH=auto.lua")
        print(f"     ALLOWED_CHANNEL=")
        exit(1)
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg

def require_cfg(cfg, key):
    val = cfg.get(key, "")
    if not val:
        print(f"❌ '{key}' tidak ditemukan atau kosong di bot.cfg!")
        exit(1)
    return val

CFG             = load_config(CONFIG_FILE)
DISCORD_TOKEN   = require_cfg(CFG, "DISCORD_TOKEN")
GITHUB_TOKEN    = require_cfg(CFG, "GITHUB_TOKEN")
GITHUB_REPO     = require_cfg(CFG, "GITHUB_REPO")
GITHUB_BRANCH   = CFG.get("GITHUB_BRANCH", "main")
ALLOWED_CHANNEL = CFG.get("ALLOWED_CHANNEL", "")
PREFIX          = CFG.get("PREFIX", "!")

# ── Discord setup ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

GITHUB_API = "https://api.github.com"

async def get_file_sha(session, repo, path, branch):
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}?ref={branch}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    async with session.get(url, headers=headers) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("sha")
        return None

async def push_to_github(file_bytes, github_path, commit_msg):
    async with aiohttp.ClientSession() as session:
        sha = await get_file_sha(session, GITHUB_REPO, github_path, GITHUB_BRANCH)
        content_b64 = base64.b64encode(file_bytes).decode("utf-8")
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{github_path}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        payload = {
            "message": commit_msg,
            "content": content_b64,
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha

        async with session.put(url, headers=headers, data=json.dumps(payload)) as resp:
            resp_data = await resp.json()
            if resp.status in (200, 201):
                action = "diperbarui" if sha else "dibuat baru"
                commit_url = resp_data.get("commit", {}).get("html_url", "")
                return True, action, commit_url
            else:
                err = resp_data.get("message", "Unknown error")
                return False, err, ""

async def download_attachment(attachment):
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as resp:
            if resp.status == 200:
                return await resp.read()
            return None

async def handle_push(message, attachment, github_path, mode):
    filename = attachment.filename
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    mode_label = "Upload File Baru" if mode == "upload" else "Edit File"
    commit_msg = f"{mode}: {filename} via Discord by {message.author.name} [{now}]"

    status_msg = await message.reply(f"⏳ **Sedang memproses `{filename}`...**")
    try:
        file_bytes = await download_attachment(attachment)
        if not file_bytes:
            await status_msg.edit(content="❌ Gagal mengunduh file dari Discord.")
            return

        success, info, commit_url = await push_to_github(file_bytes, github_path, commit_msg)

        if success:
            embed = discord.Embed(title=f"✅ {mode_label} Berhasil!", color=0x00C853)
            embed.add_field(name="📄 File",   value=f"`{filename}`",        inline=True)
            embed.add_field(name="📁 Repo",   value=f"`{GITHUB_REPO}`",     inline=True)
            embed.add_field(name="🌿 Branch", value=f"`{GITHUB_BRANCH}`",   inline=True)
            embed.add_field(name="📂 Path",   value=f"`{github_path}`",     inline=True)
            embed.add_field(name="📝 Status", value=f"File {info}",         inline=True)
            embed.add_field(name="👤 Oleh",   value=message.author.mention, inline=True)
            if commit_url:
                embed.add_field(name="🔗 Commit", value=f"[Lihat di GitHub]({commit_url})", inline=False)
            embed.set_footer(text=now)
            await status_msg.edit(content=None, embed=embed)
        else:
            await status_msg.edit(content=f"❌ **Push gagal!**\n```{info}```")
    except Exception as e:
        await status_msg.edit(content=f"❌ **Error:** ```{str(e)}```")

HELP_TEXT = """**📦 Daftar Command Bot GitHub**

`!upload` + lampirkan file
→ Upload file ke GitHub (path default sesuai config)
→ Support semua jenis file: `.lua` `.py` `.txt` `.json` dll

`!upload scripts/beta.lua` + lampirkan file
→ Upload ke path custom di repo

`!edit` + lampirkan file
→ Perbarui file yang sudah ada di repo

`!edit src/main.py` + lampirkan file
→ Edit file di path custom

`!help` → tampilkan pesan ini"""

@client.event
async def on_ready():
    print(f"✅ Bot online: {client.user}")
    print(f"   Repo    : {GITHUB_REPO}")
    print(f"   Branch  : {GITHUB_BRANCH}")
    print(f"   Channel : {ALLOWED_CHANNEL or 'Semua channel'}")
    print(f"   Config  : {CONFIG_FILE}")

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if ALLOWED_CHANNEL and str(message.channel.id) != str(ALLOWED_CHANNEL):
        return

    content = message.content.strip()

    if content.lower() == f"{PREFIX}help":
        await message.reply(HELP_TEXT)
        return

    if content.lower().startswith(f"{PREFIX}upload"):
        all_files = [a for a in message.attachments]
        if not all_files:
            await message.reply(f"⚠️ Lampirkan file bersama command `{PREFIX}upload`")
            return
        parts = content.split(None, 1)
        custom_path = parts[1].strip() if len(parts) > 1 else None
        for attachment in all_files:
            github_path = custom_path if custom_path else attachment.filename
            await handle_push(message, attachment, github_path, mode="upload")
        return

    if content.lower().startswith(f"{PREFIX}edit"):
        all_files = [a for a in message.attachments]
        if not all_files:
            await message.reply(f"⚠️ Lampirkan file bersama command `{PREFIX}edit`")
            return
        parts = content.split(None, 1)
        custom_path = parts[1].strip() if len(parts) > 1 else None
        for attachment in all_files:
            github_path = custom_path if custom_path else attachment.filename
            await handle_push(message, attachment, github_path, mode="edit")
        return

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)