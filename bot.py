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

# Sesi pending per user
# State: "waiting_file_choice" | "waiting_description"
pending = {}

# ── GitHub Helpers ────────────────────────────────────────────
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

async def list_repo_files():
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return [item["path"] for item in data.get("tree", []) if item["type"] == "blob"]
            return []

async def delete_from_github(github_path):
    """Hapus file dari GitHub repo"""
    async with aiohttp.ClientSession() as session:
        sha = await get_file_sha(session, GITHUB_REPO, github_path, GITHUB_BRANCH)
        if not sha:
            return False, "File tidak ditemukan di repo.", ""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{github_path}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        payload = {
            "message": f"delete: {github_path} [{now}]",
            "sha": sha,
            "branch": GITHUB_BRANCH,
        }
        async with session.delete(url, headers=headers, data=json.dumps(payload)) as resp:
            if resp.status == 200:
                resp_data = await resp.json()
                commit_url = resp_data.get("commit", {}).get("html_url", "")
                return True, "berhasil dihapus", commit_url
            else:
                resp_data = await resp.json()
                return False, resp_data.get("message", "Unknown error"), ""

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

async def do_push(message, session_data):
    """Eksekusi push setelah semua info terkumpul"""
    attachment  = session_data["attachment"]
    github_path = session_data["github_path"]
    mode        = session_data["mode"]
    description = session_data["description"]

    filename   = attachment.filename
    now        = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    mode_label = "Upload File Baru" if mode == "upload" else "Edit File"

    # Commit message: gabung mode + deskripsi user
    commit_msg = description

    status_msg = await message.reply(f"⏳ **Sedang memproses `{filename}` → `{github_path}`...**")
    try:
        file_bytes = await download_attachment(attachment)
        if not file_bytes:
            await status_msg.edit(content="❌ Gagal mengunduh file dari Discord.")
            return

        success, info, commit_url = await push_to_github(file_bytes, github_path, commit_msg)

        if success:
            embed = discord.Embed(title=f"✅ {mode_label} Berhasil!", color=0x00C853)
            embed.add_field(name="📄 File",        value=f"`{filename}`",        inline=True)
            embed.add_field(name="📁 Repo",        value=f"`{GITHUB_REPO}`",     inline=True)
            embed.add_field(name="🌿 Branch",      value=f"`{GITHUB_BRANCH}`",   inline=True)
            embed.add_field(name="📂 Path",        value=f"`{github_path}`",     inline=True)
            embed.add_field(name="📝 Status",      value=f"File {info}",         inline=True)
            embed.add_field(name="👤 Oleh",        value=message.author.mention, inline=True)
            embed.add_field(name="💬 Deskripsi",   value=description,            inline=False)
            if commit_url:
                embed.add_field(name="🔗 Commit", value=f"[Lihat di GitHub]({commit_url})", inline=False)
            embed.set_footer(text=now)
            await status_msg.edit(content=None, embed=embed)
        else:
            await status_msg.edit(content=f"❌ **Push gagal!**\n```{info}```")
    except Exception as e:
        await status_msg.edit(content=f"❌ **Error:** ```{str(e)}```")

async def ask_description(message, session_data):
    """Tanya deskripsi ke user, simpan sesi"""
    user_id = message.author.id
    session_data["state"] = "waiting_description"
    pending[user_id] = session_data
    await message.reply(
        f"💬 **Ketik deskripsi untuk commit ini:**\n"
        f"> File: `{session_data['github_path']}`\n"
        f"> Atau ketik `skip` untuk pakai deskripsi default, `batal` untuk membatalkan."
    )

# ── Help ──────────────────────────────────────────────────────
HELP_TEXT = """**📦 Daftar Command Bot GitHub**

`!upload` + lampirkan file
→ Upload file baru ke repo, lalu bot minta deskripsi commit

`!upload scripts/beta.lua` + lampirkan file
→ Upload ke path custom, lalu bot minta deskripsi

`!edit` + lampirkan file
→ Tampilkan daftar file di repo, pilih nomor, lalu isi deskripsi

`!edit scripts/auto.lua` + lampirkan file
→ Langsung edit file di path tertentu, lalu isi deskripsi

`!delete`
→ Tampilkan daftar file di repo, pilih nomor untuk dihapus

`!delete scripts/auto.lua`
→ Langsung hapus file tertentu (minta konfirmasi dulu)

`!help` → tampilkan pesan ini"""

# ── Events ────────────────────────────────────────────────────
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
    user_id = message.author.id

    # ── Cek sesi pending user ─────────────────────────────────
    if user_id in pending:
        sess  = pending[user_id]
        state = sess.get("state")

        # Batalkan di state manapun
        if content.lower() in ("batal", "cancel", "0"):
            del pending[user_id]
            await message.reply("❌ **Dibatalkan.**")
            return

        # State: pilih nomor file (untuk !edit tanpa argumen)
        if state == "waiting_file_choice":
            files = sess["files"]
            if content.isdigit():
                idx = int(content) - 1
                if 0 <= idx < len(files):
                    sess["github_path"] = files[idx]
                    await ask_description(message, sess)
                else:
                    await message.reply(f"⚠️ Masukkan angka **1–{len(files)}** atau ketik `batal`.")
            else:
                await message.reply(f"⚠️ Masukkan angka **1–{len(files)}** atau ketik `batal`.")
            return

        # State: pilih file untuk dihapus
        if state == "waiting_delete_choice":
            files = sess["files"]
            if content.isdigit():
                idx = int(content) - 1
                if 0 <= idx < len(files):
                    chosen = files[idx]
                    sess["github_path"] = chosen
                    sess["state"] = "waiting_delete_confirm"
                    pending[user_id] = sess
                    await message.reply(
                        f"⚠️ **Yakin ingin menghapus `{chosen}` dari repo?**\n"
                        f"> Ketik `ya` untuk konfirmasi atau `batal` untuk membatalkan."
                    )
                else:
                    await message.reply(f"⚠️ Masukkan angka **1–{len(files)}** atau ketik `batal`.")
            else:
                await message.reply(f"⚠️ Masukkan angka **1–{len(files)}** atau ketik `batal`.")
            return

        # State: konfirmasi hapus
        if state == "waiting_delete_confirm":
            github_path = sess["github_path"]
            if content.lower() in ("ya", "yes", "y"):
                del pending[user_id]
                status_msg = await message.reply(f"⏳ **Menghapus `{github_path}`...**")
                success, info, commit_url = await delete_from_github(github_path)
                if success:
                    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                    embed = discord.Embed(title="🗑️ File Berhasil Dihapus!", color=0xFF5252)
                    embed.add_field(name="📂 Path",   value=f"`{github_path}`",     inline=True)
                    embed.add_field(name="📁 Repo",   value=f"`{GITHUB_REPO}`",     inline=True)
                    embed.add_field(name="🌿 Branch", value=f"`{GITHUB_BRANCH}`",   inline=True)
                    embed.add_field(name="👤 Oleh",   value=message.author.mention, inline=True)
                    if commit_url:
                        embed.add_field(name="🔗 Commit", value=f"[Lihat di GitHub]({commit_url})", inline=False)
                    embed.set_footer(text=now)
                    await status_msg.edit(content=None, embed=embed)
                else:
                    await status_msg.edit(content=f"❌ **Gagal menghapus!**\n```{info}```")
            else:
                del pending[user_id]
                await message.reply("❌ **Penghapusan dibatalkan.**")
            return

        # State: menunggu deskripsi
        if state == "waiting_description":
            if content.lower() == "skip":
                sess["description"] = f"update {sess['github_path']}"
            else:
                sess["description"] = content
            del pending[user_id]
            await do_push(message, sess)
            return

    # ── !help ─────────────────────────────────────────────────
    if content.lower() == f"{PREFIX}help":
        await message.reply(HELP_TEXT)
        return

    # ── !upload ───────────────────────────────────────────────
    if content.lower().startswith(f"{PREFIX}upload"):
        all_files = list(message.attachments)
        if not all_files:
            await message.reply(f"⚠️ Lampirkan file bersama command `{PREFIX}upload`")
            return
        parts = content.split(None, 1)
        custom_path = parts[1].strip() if len(parts) > 1 else None
        for attachment in all_files:
            github_path = custom_path if custom_path else attachment.filename
            sess = {
                "state":       "waiting_description",
                "mode":        "upload",
                "attachment":  attachment,
                "github_path": github_path,
            }
            await ask_description(message, sess)
        return

    # ── !edit ─────────────────────────────────────────────────
    if content.lower().startswith(f"{PREFIX}edit"):
        all_files = list(message.attachments)
        if not all_files:
            await message.reply(f"⚠️ Lampirkan file bersama command `{PREFIX}edit`")
            return

        parts = content.split(None, 1)
        custom_path = parts[1].strip() if len(parts) > 1 else None

        # Jika ada path custom → langsung tanya deskripsi
        if custom_path:
            for attachment in all_files:
                sess = {
                    "state":       "waiting_description",
                    "mode":        "edit",
                    "attachment":  attachment,
                    "github_path": custom_path,
                }
                await ask_description(message, sess)
            return

        # Tanpa argumen → ambil daftar file dari repo dulu
        attachment = all_files[0]
        status_msg = await message.reply("🔍 **Mengambil daftar file dari repo...**")

        files = await list_repo_files()
        if not files:
            await status_msg.edit(content="❌ Gagal mengambil daftar file atau repo kosong.")
            return

        lines = [f"📂 **Pilih file yang ingin diedit di `{GITHUB_REPO}`:**\n"]
        for i, f in enumerate(files, 1):
            lines.append(f"`{i}.` {f}")
        lines.append("\n> Balas dengan **nomor** file, atau ketik `batal`.")

        text = "\n".join(lines)
        if len(text) > 1900:
            text = text[:1900] + "\n... (terlalu banyak, gunakan `!edit path/file` langsung)"

        await status_msg.edit(content=text)

        pending[user_id] = {
            "state":      "waiting_file_choice",
            "mode":       "edit",
            "attachment": attachment,
            "files":      files,
        }
        return


    # ── !delete ───────────────────────────────────────────────
    if content.lower().startswith(f"{PREFIX}delete"):
        parts = content.split(None, 1)
        custom_path = parts[1].strip() if len(parts) > 1 else None

        # Path langsung tanpa daftar
        if custom_path:
            pending[user_id] = {
                "state":       "waiting_delete_confirm",
                "github_path": custom_path,
            }
            await message.reply(
                f"⚠️ **Yakin ingin menghapus `{custom_path}` dari repo?**\n"
                f"> Ketik `ya` untuk konfirmasi atau `batal` untuk membatalkan."
            )
            return

        # Tanpa argumen → tampilkan daftar file
        status_msg = await message.reply("🔍 **Mengambil daftar file dari repo...**")
        files = await list_repo_files()
        if not files:
            await status_msg.edit(content="❌ Gagal mengambil daftar file atau repo kosong.")
            return

        lines = [f"🗑️ **Pilih file yang ingin dihapus dari `{GITHUB_REPO}`:**\n"]
        for i, f in enumerate(files, 1):
            lines.append(f"`{i}.` {f}")
        lines.append("\n> Balas dengan **nomor** file, atau ketik `batal`.")

        text = "\n".join(lines)
        if len(text) > 1900:
            text = text[:1900] + "\n... (terlalu banyak, gunakan `!delete path/file` langsung)"

        await status_msg.edit(content=text)
        pending[user_id] = {
            "state": "waiting_delete_choice",
            "files": files,
        }
        return

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)