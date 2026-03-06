#!/data/data/com.termux/files/usr/bin/bash
# Felix Optimized State Tracker - Ultra-fast hash comparison with thumbnail
# Exit codes: 0=no change, 1=new signal, 2=error/recovery needed

set -euo pipefail

# ===== KONFIGURĀCIJA =====
STATE_DIR="${HOME}/.felix"
STATE_FILE="${STATE_DIR}/state.json"
HASH_FILE="${STATE_DIR}/last.hash"
SCREENSHOT_PATH="/sdcard/.felix_thumb.png"
LOCAL_PATH="${STATE_DIR}/.check.png"
THUMB_PATH="${STATE_DIR}/.thumb.jpg"
TELEGRAM_PACKAGE="org.telegram.messenger.web"
FELIX_CHANNEL="felix vip room"

# Thumbnail izmērs hash ģenerēšanai (ātrāk, mazāk atmiņas)
THUMB_SIZE="160x284"
HASH_ALGO="xxh128"  # xxHash ir ātrāks par MD5, fallback uz md5

# ===== INIT =====
mkdir -p "$STATE_DIR" 2>/dev/null || { echo "❌ Cannot create state dir"; exit 2; }

# Pārbaudām vai ir xxhash (ātrāks), fallback uz md5
if command -v xxh128sum &>/dev/null; then
    HASH_CMD="xxh128sum"
elif command -v xxhsum &>/dev/null; then
    HASH_CMD="xxhsum -H128"
else
    HASH_CMD="md5sum"
fi

# ===== FUNKCIJAS =====

# Ātrs hash no thumbnail - daudz ātrāk par head -c 10240
create_thumb_hash() {
    # Screenshot uz SD kartes (ātrāks write)
    su -c "screencap -p '$SCREENSHOT_PATH'" 2>/dev/null || return 1
    
    # Pārbaudām vai ImageMagick ir pieejams (thumbnail ģenerēšanai)
    if command -v convert &>/dev/null; then
        # Konvertējam uz mazu thumbnail - ātrāka hash ģenerēšana
        convert "$SCREENSHOT_PATH" -resize "$THUMB_SIZE" -quality 30 "$THUMB_PATH" 2>/dev/null || {
            # Fallback - kopējam kā ir
            cp "$SCREENSHOT_PATH" "$THUMB_PATH" 2>/dev/null
        }
    else
        # Fallback - izmantojam pilnu attēlu
        cp "$SCREENSHOT_PATH" "$THUMB_PATH" 2>/dev/null
    fi
    
    # Hash no thumbnail (daudz mazāks fails = ātrāk)
    $HASH_CMD "$THUMB_PATH" 2>/dev/null | cut -d' ' -f1
}

# Vecā hash nolasīšana
get_last_hash() {
    [[ -f "$HASH_FILE" ]] && cat "$HASH_FILE" 2>/dev/null || echo ""
}

# Jauna hash saglabāšana
save_state() {
    local hash="$1"
    local timestamp=$(date +%s)
    echo "$hash" > "$HASH_FILE"
    echo "{\"hash\":\"$hash\",\"ts\":$timestamp,\"algo\":\"${HASH_ALGO}\"}" > "$STATE_FILE"
}

# Pārbaudām vai Telegram ir foregroundā un uz pareizā ekrāna
is_telegram_ready() {
    # Ātra pārbaude - vai Telegram ir top activity
    local top_app=$(su -c "dumpsys activity activities | grep -E 'mResumedActivity|mFocusedApp' | head -1" 2>/dev/null | grep -o "$TELEGRAM_PACKAGE" || echo "")
    
    # Pārbaudām arī vai ir "felix" logā
    local has_felix=$(su -c "dumpsys window windows | grep -i 'felix'" 2>/dev/null | head -1 || echo "")
    
    [[ -n "$top_app" ]] && [[ -n "$has_felix" ]]
}

# Atver Telegram un navigē uz Felix kanālu (tikai ja nepieciešams)
ensure_telegram() {
    if is_telegram_ready; then
        # Jau ir pareizajā vietā - tikai scroll uz leju
        su -c "input swipe 540 2200 540 300 50" 2>/dev/null || true
        sleep 0.2
        return 0
    fi
    
    # Nav pareizajā vietā - atveram
    echo "📱 Navigating to Felix..."
    
    # Ja Telegram ir atvērts citur - force-stop, ja ir pilnīgi jāpārlādē
    if su -c "dumpsys activity activities | grep -q '$TELEGRAM_PACKAGE'" 2>/dev/null; then
        # Telegram ir atvērts, bet ne felix kanālā - tap search
        su -c "input keyevent KEYCODE_HOME" 2>/dev/null || true
        sleep 0.3
    fi
    
    # Atveram Telegram
    su -c "am start -n $TELEGRAM_PACKAGE/org.telegram.ui.LaunchActivity" > /dev/null 2>&1 || \
        su -c "monkey -p $TELEGRAM_PACKAGE -c android.intent.category.LAUNCHER 1" > /dev/null 2>&1
    sleep 2
    
    # Meklējam kanālu (ātrāka metode)
    su -c "input tap 540 280" 2>/dev/null || true
    sleep 0.3
    su -c "input text 'felix'" 2>/dev/null || true
    sleep 0.5
    su -c "input tap 540 550" 2>/dev/null || true
    sleep 1
    
    # Scroll uz leju
    su -c "input swipe 540 2200 540 300 50" 2>/dev/null || true
    sleep 0.2
}

# ===== GALVENĀ LOĢIKA =====
main() {
    local CURRENT_HASH LAST_HASH
    
    # Ātrs check - pārliecināmies ka Telegram ir gatavs
    ensure_telegram
    
    # Izveidojam hash no thumbnail
    CURRENT_HASH=$(create_thumb_hash) || {
        echo "❌ Screenshot failed"
        exit 2
    }
    
    LAST_HASH=$(get_last_hash)
    
    # Salīdzinām
    if [[ "$CURRENT_HASH" == "$LAST_HASH" ]]; then
        echo "⏸️ NO_CHANGE:${CURRENT_HASH:0:12}"
        exit 0
    else
        echo "🆕 NEW_SIGNAL:${CURRENT_HASH:0:12}"
        [[ -n "$LAST_HASH" ]] && echo "   prev:${LAST_HASH:0:12}"
        save_state "$CURRENT_HASH"
        
        # Saglabājam "evidence" - tikai hash kā ID
        cp "$THUMB_PATH" "${STATE_DIR}/sig_$(date +%s)_${CURRENT_HASH:0:8}.jpg" 2>/dev/null || true
        
        exit 1
    fi
}

# Izpildām
main "$@"
