#!/bin/bash

# ===== SETUP =====
termux-setup-storage
pkg install -y lua53 sqlite expect

# ===== PINDAH KE FOLDER DOWNLOAD =====
cd /sdcard/Download
echo "[*] Sekarang di direktori: $(pwd)"

# ===== DOWNLOAD auto.lua =====
echo "[*] Downloading auto.lua..."
curl -L -o auto.lua "https://raw.githubusercontent.com/Zhesty/dandandan/refs/heads/main/auto.lua"
echo "[*] Download selesai, menjalankan auto.lua..."

# ===== JALANKAN auto.lua DENGAN INPUT OTOMATIS =====
expect <<'EOF'
set timeout -1

spawn lua /sdcard/Download/auto.lua

sleep 5
send "1\r"
sleep 5
send "4\r"
sleep 5
send "1-6\r"

expect eof
EOF

echo "[*] auto.lua selesai!"

# ===== DOWNLOAD & JALANKAN winter-rejoin.lua =====
echo "[*] Downloading winter-rejoin.lua..."
curl -L -o winter-rejoin.lua "https://raw.githubusercontent.com/FnDXueyi/roblog/refs/heads/main/winter-rejoin.lua"
echo "[*] Menjalankan winter-rejoin.lua..."
lua winter-rejoin.lua </dev/null