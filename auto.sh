#!/bin/bash

# ===== CEK STORAGE ACCESS =====
if [ ! -d "/sdcard/Download" ]; then
    echo "[*] Meminta izin akses storage..."
    termux-setup-storage
    sleep 3
else
    echo "[✓] Storage sudah bisa diakses, skip termux-setup-storage"
fi

# ===== INSTALL PACKAGES =====
pkg install -y lua53 sqlite expect

# ===== CEK DIREKTORI SAAT INI =====
if [ "$(pwd)" != "/sdcard/Download" ]; then
    echo "[*] Pindah ke /sdcard/Download..."
    cd /sdcard/Download
    echo "[✓] Sekarang di direktori: $(pwd)"
else
    echo "[✓] Sudah di /sdcard/Download, skip cd"
fi

# ===== DOWNLOAD auto.lua =====
echo "[*] Downloading auto.lua..."
curl -L -o auto.lua "https://raw.githubusercontent.com/Zhesty/dandandan/refs/heads/main/auto.lua"
echo "[✓] Download auto.lua selesai!"

# ===== JALANKAN auto.lua DENGAN INPUT OTOMATIS =====
echo "[*] Menjalankan auto.lua..."
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

echo "[✓] auto.lua selesai!"

# ===== DOWNLOAD & JALANKAN winter-rejoin.lua =====
echo "[*] Downloading winter-rejoin.lua..."
curl -L -o winter-rejoin.lua "https://raw.githubusercontent.com/FnDXueyi/roblog/refs/heads/main/winter-rejoin.lua"
echo "[✓] Download winter-rejoin.lua selesai!"
echo "[*] Menjalankan winter-rejoin.lua..."
lua winter-rejoin.lua </dev/null
