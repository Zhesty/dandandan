#!/bin/bash

# ===== FUNGSI CEK PACKAGE =====
check_and_install() {
    local pkg_name=$1
    if pkg list-installed 2>/dev/null | grep -q "^$pkg_name/"; then
        echo "[✓] $pkg_name sudah terinstall, skip"
    else
        echo "[*] Menginstall $pkg_name..."
        pkg install -y $pkg_name
        echo "[✓] $pkg_name berhasil diinstall"
    fi
}

# ===== CEK STORAGE ACCESS =====
if [ ! -d "/sdcard/Download" ]; then
    echo "[*] Meminta izin akses storage..."
    termux-setup-storage
    sleep 3
else
    echo "[✓] Storage sudah bisa diakses, skip termux-setup-storage"
fi

# ===== CEK & INSTALL PACKAGES =====
echo "[*] Mengecek package..."
check_and_install lua53
check_and_install sqlite
check_and_install expect

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
send "1-5\r"

expect eof
EOF

echo "[✓] auto.lua selesai!"

# ===== DOWNLOAD & JALANKAN winter-rejoin.lua =====
echo "[*] Downloading winter-rejoin.lua..."
curl -L -o winter-rejoin.lua "https://raw.githubusercontent.com/FnDXueyi/roblog/refs/heads/main/winter-rejoin.lua"
echo "[✓] Download winter-rejoin.lua selesai!"
echo "[*] Menjalankan winter-rejoin.lua..."
lua winter-rejoin.lua </dev/null
