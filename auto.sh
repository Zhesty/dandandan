#!/bin/bash

# ===== FUNGSI LOADING ANIMASI =====
loading() {
    local pid=$1
    local msg=$2
    local spin=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    local i=0
    while kill -0 $pid 2>/dev/null; do
        printf "\r[${spin[$i]}] $msg"
        i=$(( (i+1) % 10 ))
        sleep 0.1
    done
    printf "\r[✓] $msg\n"
}

# ===== FIX MIRROR OTOMATIS =====
sed -i 's|https://mirror.textcord.xyz/termux/termux-main|https://packages.termux.dev/apt/termux-main|g' $PREFIX/etc/apt/sources.list
pkg update -y > /dev/null 2>&1 &
loading $! "Memperbaiki mirror Termux..."

# ===== FUNGSI CEK & INSTALL PACKAGE =====
check_and_install() {
    local pkg_name=$1
    if pkg list-installed 2>/dev/null | grep -q "^$pkg_name/"; then
        echo "[✓] $pkg_name sudah terinstall, skip"
    else
        pkg install -y $pkg_name > /dev/null 2>&1 &
        loading $! "Menginstall $pkg_name..."
    fi
}

# ===== CEK STORAGE ACCESS =====
if [ ! -d "/sdcard/Download" ]; then
    termux-setup-storage > /dev/null 2>&1 &
    loading $! "Meminta izin akses storage..."
    sleep 3
else
    echo "[✓] Storage sudah bisa diakses, skip"
fi

# ===== CEK & INSTALL PACKAGES =====
echo ""
echo "[*] Mengecek package..."
check_and_install lua53
check_and_install sqlite
check_and_install expect

# ===== CEK DIREKTORI =====
if [ "$(pwd)" != "/sdcard/Download" ]; then
    cd /sdcard/Download
    echo "[✓] Pindah ke /sdcard/Download"
else
    echo "[✓] Sudah di /sdcard/Download, skip"
fi

# ===== INPUT DARI USER =====
echo ""
echo "==============================="
echo " Masukkan range akun (contoh: 1-6, 2-10, 1-20)"
echo "==============================="
read -p " Range akun: " RANGE_AKUN
echo "[✓] Range akun: $RANGE_AKUN"
echo ""

# ===== DOWNLOAD auto.lua =====
curl -L -o auto.lua "https://raw.githubusercontent.com/Zhesty/dandandan/refs/heads/main/auto.lua" > /dev/null 2>&1 &
loading $! "Downloading auto.lua..."

# ===== JALANKAN auto.lua DENGAN INPUT OTOMATIS =====
echo "[*] Menjalankan auto.lua..."
expect <<EOF
set timeout -1

spawn lua /sdcard/Download/auto.lua

sleep 5
send "1\r"
sleep 5
send "4\r"
sleep 5
send "$RANGE_AKUN\r"

expect eof
EOF

echo "[✓] auto.lua selesai!"

# ===== DOWNLOAD winter-rejoin.lua =====
curl -L -o winter-rejoin.lua "https://raw.githubusercontent.com/FnDXueyi/roblog/refs/heads/main/winter-rejoin.lua" > /dev/null 2>&1 &
loading $! "Downloading winter-rejoin.lua..."

# ===== JALANKAN winter-rejoin.lua =====
echo "[*] Menjalankan winter-rejoin.lua..."
lua winter-rejoin.lua </dev/null
