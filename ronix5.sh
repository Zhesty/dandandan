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

# ===== FUNGSI DELAY =====
delay() {
    local msg=$1
    echo "[*] $msg"
    sleep 3
}

# ===== FUNGSI VERIFIKASI & INSTALL PACKAGE =====
install_pkg() {
    local pkg_name=$1
    local cmd_name=$2
    local max_retry=3
    local attempt=1

    if command -v $cmd_name > /dev/null 2>&1; then
        echo "[✓] $pkg_name sudah terinstall, skip"
        return 0
    fi

    while [ $attempt -le $max_retry ]; do
        echo "[*] Menginstall $pkg_name (percobaan $attempt/$max_retry)..."
        (pkg install -y $pkg_name > /dev/null 2>&1) &
        loading $! "Menginstall $pkg_name..."

        if command -v $cmd_name > /dev/null 2>&1; then
            echo "[✓] $pkg_name berhasil terinstall!"
            return 0
        else
            echo "[✗] $pkg_name gagal terinstall, mencoba ulang..."
            attempt=$((attempt + 1))
            sleep 2
        fi
    done

    echo "[✗] $pkg_name gagal terinstall setelah $max_retry percobaan!"
    echo "[!] Coba jalankan manual: pkg install -y $pkg_name"
    exit 1
}

# ===== FUNGSI INSTALL PKG TANPA CMD CHECK =====
install_pkg_nocheck() {
    local pkg_name=$1
    local max_retry=3
    local attempt=1

    if pkg list-installed 2>/dev/null | grep -q "^$pkg_name/"; then
        echo "[✓] $pkg_name sudah terinstall, skip"
        return 0
    fi

    while [ $attempt -le $max_retry ]; do
        echo "[*] Menginstall $pkg_name (percobaan $attempt/$max_retry)..."
        (pkg install -y $pkg_name > /dev/null 2>&1) &
        loading $! "Menginstall $pkg_name..."

        if pkg list-installed 2>/dev/null | grep -q "^$pkg_name/"; then
            echo "[✓] $pkg_name berhasil terinstall!"
            return 0
        else
            echo "[✗] $pkg_name gagal, mencoba ulang..."
            attempt=$((attempt + 1))
            sleep 2
        fi
    done

    echo "[✗] $pkg_name gagal terinstall setelah $max_retry percobaan!"
    echo "[!] Coba jalankan manual: pkg install -y $pkg_name"
    exit 1
}

# ============================================
echo "==============================="
echo "      MEMULAI SCRIPT AUTO      "
echo "==============================="
sleep 1

# ===== CEK & FIX MIRROR =====
MIRROR_FILE="$PREFIX/etc/apt/sources.list"
CORRECT_MIRROR="https://packages.termux.dev/apt/termux-main"

if grep -q "$CORRECT_MIRROR" "$MIRROR_FILE"; then
    echo "[✓] Mirror sudah benar, skip"
else
    delay "Memperbaiki mirror Termux..."
    sed -i 's|https://mirror.textcord.xyz/termux/termux-main|https://packages.termux.dev/apt/termux-main|g' "$MIRROR_FILE"
    (pkg update -y > /dev/null 2>&1) &
    loading $! "Update package list..."
    echo "[✓] Mirror berhasil diperbaiki!"
fi

delay "Melanjutkan ke cek storage..."

# ===== CEK STORAGE ACCESS =====
if [ ! -d "/sdcard/Download" ]; then
    echo "[*] Meminta izin akses storage..."
    termux-setup-storage
    sleep 3
    echo "[✓] Izin storage diberikan"
else
    echo "[✓] Storage sudah bisa diakses, skip"
fi

delay "Melanjutkan ke install package..."

# ===== CEK & INSTALL PACKAGES =====
echo ""
echo "==============================="
echo "       INSTALL PACKAGES        "
echo "==============================="

install_pkg_nocheck "sqlite"
delay "Melanjutkan install berikutnya..."

install_pkg "lua53" "lua5.3"
delay "Melanjutkan install berikutnya..."

install_pkg "expect" "expect"
delay "Semua package siap, melanjutkan..."

# ===== CEK DIREKTORI =====
if [ "$(pwd)" != "/sdcard/Download" ]; then
    cd /sdcard/Download
    echo "[✓] Pindah ke /sdcard/Download"
else
    echo "[✓] Sudah di /sdcard/Download, skip"
fi

delay "Melanjutkan ke download auto.lua..."

# ===== DOWNLOAD auto.lua =====
curl -L -o auto.lua "https://raw.githubusercontent.com/Zhesty/dandandan/refs/heads/main/auto.lua" > /dev/null 2>&1 &
loading $! "Downloading auto.lua..."

if [ ! -f "/sdcard/Download/auto.lua" ]; then
    echo "[✗] Gagal download auto.lua!"
    exit 1
fi
echo "[✓] auto.lua siap dijalankan!"

delay "Melanjutkan menjalankan auto.lua..."

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
send "7-11\r"

expect eof
EOF

echo "[✓] auto.lua selesai!"

delay "Melanjutkan ke download winter-rejoin.lua..."

# ===== DOWNLOAD winter-rejoin.lua =====
curl -L -o winter-rejoin.lua "https://raw.githubusercontent.com/FnDXueyi/roblog/refs/heads/main/winter-rejoin.lua" > /dev/null 2>&1 &
loading $! "Downloading winter-rejoin.lua..."

if [ ! -f "/sdcard/Download/winter-rejoin.lua" ]; then
    echo "[✗] Gagal download winter-rejoin.lua!"
    exit 1
fi
echo "[✓] winter-rejoin.lua siap dijalankan!"

delay "Melanjutkan menjalankan winter-rejoin.lua..."

# ===== JALANKAN winter-rejoin.lua =====
echo "[*] Menjalankan winter-rejoin.lua..."
lua winter-rejoin.lua </dev/null
