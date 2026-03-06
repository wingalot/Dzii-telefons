#!/data/data/com.termux/files/usr/bin/bash
# Felix Smart Screenshot - Optimized OCR, reuses check state
# Exit codes: 0=success, 1=no signal found, 2=error

set -euo pipefail

# ===== KONFIGURĀCIJA =====
STATE_DIR="${HOME}/.felix"
TESSDATA_PREFIX="${HOME}/tessdata"
TELEGRAM_PACKAGE="org.telegram.messenger.web"
DOWNLOAD_DIR="${HOME}/downloads"
TIMESTAMP=$(date +%s)

SCREENSHOT_PATH="/sdcard/felix_${TIMESTAMP}.png"
LOCAL_PATH="${DOWNLOAD_DIR}/felix_${TIMESTAMP}.png"
OCR_OUTPUT="${STATE_DIR}/.last_ocr"
SIGNAL_JSON="${STATE_DIR}/signal.json"

# ===== INIT =====
mkdir -p "$DOWNLOAD_DIR" "$STATE_DIR" 2>/dev/null || true

# Krāsas (tikai ja ir TTY)
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    NC='\033[0m'
else
    GREEN='' YELLOW='' RED='' NC=''
fi

# ===== FUNKCIJAS =====

# OCR datu pārbaude/ielāde (cache līdz 7 dienām)
ensure_ocr_data() {
    local tessdata_file="${TESSDATA_PREFIX}/eng.traineddata"
    
    # Pārbaudām vai dati eksistē un nav vecāki par 7 dienām
    if [[ -f "$tessdata_file" ]]; then
        local age_days=$(( ($(date +%s) - $(stat -c %Y "$tessdata_file" 2>/dev/null || echo 0)) / 86400 ))
        if [[ $age_days -lt 7 ]]; then
            return 0  # Dati ir OK
        fi
    fi
    
    # Lejupielādējam ja vajag
    echo -e "${YELLOW}📥 Loading OCR data...${NC}"
    mkdir -p "$TESSDATA_PREFIX"
    curl -sL -o "$tessdata_file" \
        "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata" || {
        echo -e "${RED}❌ Failed to download OCR data${NC}"
        return 1
    }
}

# Ātra pārbaude vai Telegram joprojām ir uz Felix
check_telegram_state() {
    su -c "dumpsys window windows | grep -qi 'felix'" 2>/dev/null
}

# Optimizēts scroll - mazāk iterāciju, ātrāks swipe
quick_scroll_to_bottom() {
    local i
    echo -e "${YELLOW}⬇️ Scrolling...${NC}"
    
    # 15 ātri swipes ar minimālu sleep
    for i in {1..15}; do
        su -c "input swipe 540 2200 540 300 80" 2>/dev/null || true
        # Progress dots
        [[ $((i % 5)) -eq 0 ]] && echo -n "."
    done
    echo ""
}

# OCR ar timeout (lai neiesprūst)
run_ocr() {
    local image="$1"
    export TESSDATA_PREFIX
    
    # Timeout 30s, tikai angļu valoda, minimāls logging
    timeout 30 tesseract "$image" - --oem 1 --psm 6 -l eng 2>/dev/null || {
        echo "OCR_FAILED"
        return 1
    }
}

# Signāla parsēšana no OCR teksta
parse_signal() {
    local text="$1"
    local json='{}'
    
    # Signal tips (BUY/SELL) - pēdējais match
    local signal_type=$(echo "$text" | grep -ioE "\b(BUY|SELL)\b" | tail -1 | tr '[:lower:]' '[:upper:]' || echo "")
    
    # Valūtu pāris
    local pair=$(echo "$text" | grep -oE "\b(XAUUSD|XAU/USD|EURUSD|EUR/USD|GBPUSD|GBP/USD|USDJPY|USD/JPY|US30|NAS100|NASDAQ)\b" | tail -1 | tr '/' ' ' || echo "")
    [[ -z "$pair" ]] && pair=$(echo "$text" | grep -oE "(GOLD|XAU)" | tail -1 | tr '[:lower:]' '[:upper:]' || echo "")
    [[ "$pair" == "GOLD" ]] && pair="XAUUSD"
    
    # Cenas - visi decimāli skaitļi
    local prices=$(echo "$text" | grep -oE "[0-9]+\.[0-9]{2,5}" | head -10)
    local price_count=$(echo "$prices" | wc -l)
    
    # Meklējam TP/SL markerus
    local has_tp=$(echo "$text" | grep -iE "(tp[123]?|take profit)" | head -1 || echo "")
    local has_sl=$(echo "$text" | grep -iE "(sl|stop loss)" | head -1 || echo "")
    
    # Ja ir TP/SL sekcijas, ņemam cenas no turienes
    local tp1="" tp2="" tp3="" sl="" entry=""
    
    if [[ -n "$has_tp" ]]; then
        # TP cenas - pirmās 3 aiz "TP"
        tp1=$(echo "$text" | grep -i "tp1" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
        [[ -z "$tp1" ]] && tp1=$(echo "$text" | grep -iE "tp[^0-9]*1" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
        
        tp2=$(echo "$text" | grep -i "tp2" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
        tp3=$(echo "$text" | grep -i "tp3" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
    fi
    
    if [[ -n "$has_sl" ]]; then
        sl=$(echo "$text" | grep -iE "sl[^a-z]" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
        [[ -z "$sl" ]] && sl=$(echo "$text" | grep -i "stop loss" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
    fi
    
    # Entry price - meklējam "@" vai "ENTRY" vai pirmo cenu signāla kontekstā
    entry=$(echo "$text" | grep -iE "(@|entry|price)" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
    
    # Ja nav specifiska entry, ņemam pirmo cenu pēc valūtu pāra
    if [[ -z "$entry" ]] && [[ -n "$pair" ]]; then
        entry=$(echo "$text" | grep "$pair" -A 2 | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
    fi
    
    # Ja joprojām nav entry, ņemam pirmo kopējo cenu
    [[ -z "$entry" ]] && entry=$(echo "$prices" | head -1 || echo "")
    
    # Pips skaits (ja minēts)
    local pips=$(echo "$text" | grep -oiE "[0-9]+\s*(pips?|points?)" | grep -oE "[0-9]+" | head -1 || echo "")
    
    # Laika zīmogs (ja minēts)
    local signal_time=$(echo "$text" | grep -oE "[0-9]{1,2}:[0-9]{2}" | head -1 || echo "")
    
    # Saliekam JSON
    jq -n \
        --arg ts "$TIMESTAMP" \
        --arg type "$signal_type" \
        --arg pair "$pair" \
        --arg entry "$entry" \
        --arg tp1 "$tp1" \
        --arg tp2 "$tp2" \
        --arg tp3 "$tp3" \
        --arg sl "$sl" \
        --arg pips "$pips" \
        --arg time "$signal_time" \
        --arg raw "$text" \
        '{
            timestamp: ($ts | tonumber),
            detected_at: now | strftime("%Y-%m-%d %H:%M:%S"),
            signal: {
                type: $type,
                pair: $pair,
                entry_price: $entry,
                take_profit: {
                    tp1: $tp1,
                    tp2: $tp2,
                    tp3: $tp3
                },
                stop_loss: $sl,
                pips: $pips,
                signal_time: $time
            },
            raw_text: $raw
        }' > "$SIGNAL_JSON" 2>/dev/null || {
        # Fallback ja jq nav
        cat > "$SIGNAL_JSON" << EOF
{
    "timestamp": $TIMESTAMP,
    "signal": {
        "type": "$signal_type",
        "pair": "$pair",
        "entry_price": "$entry",
        "tp1": "$tp1",
        "tp2": "$tp2",
        "tp3": "$tp3",
        "sl": "$sl"
    }
}
EOF
    }
    
    # Atgriežam vērtības
    echo "TYPE:$signal_type PAIR:$pair ENTRY:$entry TP1:$tp1 TP2:$tp2 TP3:$tp3 SL:$sl"
}

# ===== GALVENĀ LOĢIKA =====
main() {
    echo -e "${GREEN}🚀 Felix Smart Screenshot${NC}"
    echo "=========================="
    echo "Time: $(date '+%H:%M:%S')"
    echo ""
    
    # 1. OCR dati
    ensure_ocr_data || exit 2
    
    # 2. Pārbaudām vai esam pareizajā vietā (ja nē - atveram)
    if ! check_telegram_state; then
        echo -e "${YELLOW}⚠️ Telegram not on Felix, navigating...${NC}"
        su -c "am start -n ${TELEGRAM_PACKAGE}/org.telegram.ui.LaunchActivity" > /dev/null 2>&1 || true
        sleep 2
        su -c "input tap 540 280" 2>/dev/null || true
        sleep 0.3
        su -c "input text 'felix'" 2>/dev/null || true
        sleep 0.5
        su -c "input tap 540 550" 2>/dev/null || true
        sleep 1
    fi
    
    # 3. Scroll uz apakšu
    quick_scroll_to_bottom
    
    # 4. Screenshot
    echo -e "${YELLOW}📸 Capturing...${NC}"
    su -c "screencap -p '$SCREENSHOT_PATH'" || {
        echo -e "${RED}❌ Screenshot failed${NC}"
        exit 2
    }
    cp "$SCREENSHOT_PATH" "$LOCAL_PATH" 2>/dev/null || true
    
    # 5. OCR
    echo -e "${YELLOW}🔍 OCR processing...${NC}"
    local ocr_text=$(run_ocr "$LOCAL_PATH")
    
    if [[ "$ocr_text" == "OCR_FAILED" ]]; then
        echo -e "${RED}❌ OCR failed${NC}"
        exit 2
    fi
    
    echo "$ocr_text" > "$OCR_OUTPUT"
    
    # 6. Izvade
    echo ""
    echo "=========================="
    echo -e "${GREEN}📋 OCR TEXT:${NC}"
    echo "=========================="
    echo "$ocr_text"
    echo ""
    
    # 7. Signāla parsēšana
    if echo "$ocr_text" | grep -qiE "(SIGNAL|BUY|SELL|XAU|ENTRY|TP|SL)"; then
        echo "=========================="
        echo -e "${GREEN}📊 PARSED SIGNAL:${NC}"
        echo "=========================="
        
        local parsed=$(parse_signal "$ocr_text")
        
        # Izvadām formatētu
        echo "$parsed" | tr ' ' '\n' | while read line; do
            [[ -n "$line" ]] && [[ "$line" != *":" ]] && echo "  $line"
        done
        
        echo ""
        echo -e "${GREEN}✅ Saved:${NC}"
        echo "  Image: $LOCAL_PATH"
        echo "  JSON:  $SIGNAL_JSON"
        echo "=========================="
        
        exit 0
    else
        echo -e "${YELLOW}⚠️ No trading signal detected${NC}"
        echo "=========================="
        exit 1
    fi
}

main "$@"
