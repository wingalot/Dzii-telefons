#!/data/data/com.termux/files/usr/bin/bash
# Felix Signal Extractor v2 - Optimized one-shot signal extraction
# Izmanto smart detection, minimālu I/O

set -euo pipefail

# ===== KONFIGURĀCIJA =====
STATE_DIR="${HOME}/.felix"
TESSDATA_PREFIX="${HOME}/tessdata"
TELEGRAM_PACKAGE="org.telegram.messenger.web"
DOWNLOAD_DIR="${HOME}/downloads"
TIMESTAMP=$(date +%s)

SCREENSHOT_PATH="/sdcard/felix_sig_${TIMESTAMP}.png"
LOCAL_PATH="${DOWNLOAD_DIR}/felix_sig_${TIMESTAMP}.png"
OCR_TEMP="${STATE_DIR}/.ocr_temp.txt"
SIGNAL_JSON="${STATE_DIR}/signal.json"

# ===== INIT =====
mkdir -p "$DOWNLOAD_DIR" "$STATE_DIR" "$TESSDATA_PREFIX"

# Krāsas (tikai TTY)
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    GREEN='' YELLOW='' RED='' CYAN='' NC=''
fi

# ===== FUNKCIJAS =====

# Ātra OCR datu pārbaude
ensure_ocr() {
    local tessdata="${TESSDATA_PREFIX}/eng.traineddata"
    [[ -f "$tessdata" ]] && return 0
    
    echo -e "${YELLOW}📥 Downloading OCR data...${NC}"
    curl -sL -o "$tessdata" "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata" || {
        echo -e "${RED}❌ OCR download failed${NC}"
        exit 1
    }
}

# Ātrs Telegram atvēršana (vienmēr force-stop first - one-shot mode)
open_telegram_fast() {
    echo -e "${YELLOW}📱 Opening Telegram...${NC}"
    
    su -c "am force-stop $TELEGRAM_PACKAGE" 2>/dev/null || true
    sleep 0.5
    
    su -c "am start -n ${TELEGRAM_PACKAGE}/org.telegram.ui.LaunchActivity" > /dev/null 2>&1 || \
        su -c "monkey -p $TELEGRAM_PACKAGE -c android.intent.category.LAUNCHER 1" > /dev/null 2>&1
    sleep 2
}

# Ātra navigācija uz kanālu
navigate_to_channel() {
    echo -e "${YELLOW}🔍 Finding channel...${NC}"
    
    su -c "input tap 540 280"
    sleep 0.3
    su -c "input text 'felix vip'"
    sleep 0.5
    su -c "input tap 540 550"
    sleep 1
}

# Optimizēts scroll
scroll_to_latest() {
    echo -e "${YELLOW}⬇️ Scrolling...${NC}"
    
    # 12 ātri swipes
    for i in {1..12}; do
        su -c "input swipe 540 2200 540 300 80" 2>/dev/null || true
        echo -n "."
    done
    echo ""
}

# OCR ar timeout
run_ocr_fast() {
    local img="$1"
    export TESSDATA_PREFIX
    timeout 20 tesseract "$img" - --oem 1 --psm 6 -l eng 2>/dev/null || echo ""
}

# Signāla parsēšana
parse_signal_v2() {
    local text="$1"
    
    # Meklējam signal markerus
    local has_signal=$(echo "$text" | grep -iE "(SIGNAL|BUY|SELL|ENTRY|TP|SL|XAU|GOLD)" | head -1 || echo "")
    
    if [[ -z "$has_signal" ]]; then
        echo "NO_SIGNAL"
        return 1
    fi
    
    # Tips
    local type=$(echo "$text" | grep -ioE "\b(BUY|SELL)\b" | tail -1 | tr '[:lower:]' '[:upper:]' || echo "UNKNOWN")
    
    # Pāris
    local pair=$(echo "$text" | grep -oE "\b(XAUUSD|XAU/USD|EURUSD|EUR/USD|GBPUSD|GBP/USD|USDJPY|USD/JPY|US30|NAS100|NASDAQ|GOLD)\b" | tail -1 || echo "N/A")
    [[ "$pair" == "GOLD" ]] && pair="XAUUSD"
    [[ -n "${pair//\//}" ]] && pair="${pair//\//}"
    
    # Cenas
    local all_prices=$(echo "$text" | grep -oE "[0-9]+\.[0-9]{2,5}" | head -10)
    
    # Entry
    local entry=$(echo "$text" | grep -iE "(entry|@|price)" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
    [[ -z "$entry" ]] && entry=$(echo "$all_prices" | head -1 || echo "N/A")
    
    # Take Profits
    local tp1=$(echo "$text" | grep -i "tp1" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
    local tp2=$(echo "$text" | grep -i "tp2" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
    local tp3=$(echo "$text" | grep -i "tp3" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
    
    # Ja nav TP1-3, ņemam pirmās 3 cenas pēc entry
    if [[ -z "$tp1" ]]; then
        tp1=$(echo "$all_prices" | sed -n '2p' || echo "")
        tp2=$(echo "$all_prices" | sed -n '3p' || echo "")
        tp3=$(echo "$all_prices" | sed -n '4p' || echo "")
    fi
    
    # Stop Loss
    local sl=$(echo "$text" | grep -iE "sl[^a-z]" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
    [[ -z "$sl" ]] && sl=$(echo "$text" | grep -i "stop loss" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "")
    [[ -z "$sl" ]] && sl=$(echo "$all_prices" | tail -1 || echo "N/A")
    
    # Pips
    local pips=$(echo "$text" | grep -oiE "[0-9]+\s*pips?" | grep -oE "[0-9]+" | head -1 || echo "")
    
    # Izvade
    cat << EOF

${GREEN}🎯 SIGNAL DETECTED${NC}
${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
  📊 Action: ${GREEN}$type${NC}
  💱 Pair:   $pair
  💰 Entry:  $entry
  
  🎯 Take Profits:
     TP1: $tp1
     TP2: $tp2
     TP3: $tp3
  
  🛡️ Stop Loss: $sl
  ${pips:+📊 Risk: $pips pips}
${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

EOF
    
    # Saglabājam JSON
    cat > "$SIGNAL_JSON" << EOF
{
    "timestamp": $TIMESTAMP,
    "signal": {
        "type": "$type",
        "pair": "$pair",
        "entry": "$entry",
        "tp1": "$tp1",
        "tp2": "$tp2",
        "tp3": "$tp3",
        "sl": "$sl",
        "pips": "$pips"
    },
    "source": "felix-signal"
}
EOF
    
    return 0
}

# ===== GALVENĀ LOĢIKA =====
echo -e "${GREEN}🚀 Felix Signal Extractor v2${NC}"
echo "=============================="

# 1. OCR
echo -e "${YELLOW}🔍 Checking OCR...${NC}"
ensure_ocr

# 2. Telegram
echo ""
open_telegram_fast

# 3. Navigācija
navigate_to_channel

# 4. Scroll
scroll_to_latest

# 5. Screenshot
echo -e "${YELLOW}📸 Capturing...${NC}"
su -c "screencap -p '$SCREENSHOT_PATH'"
cp "$SCREENSHOT_PATH" "$LOCAL_PATH" 2>/dev/null || true

# 6. OCR
echo -e "${YELLOW}🔍 Reading text...${NC}"
OCR_TEXT=$(run_ocr_fast "$LOCAL_PATH")
echo "$OCR_TEXT" > "$OCR_TEMP"

# 7. Parādām tekstu (ja verbose)
if [[ "${VERBOSE:-0}" == "1" ]]; then
    echo ""
    echo "=============================="
    echo -e "${CYAN}📝 RAW OCR TEXT:${NC}"
    echo "=============================="
    echo "$OCR_TEXT"
    echo ""
fi

# 8. Parsējam signālu
echo "=============================="
parse_signal_v2 "$OCR_TEXT"
result=$?

echo "=============================="
echo -e "${GREEN}✅ Screenshot:${NC} $LOCAL_PATH"
echo -e "${GREEN}✅ JSON:${NC}      $SIGNAL_JSON"
echo "=============================="

exit $(( result == 0 ? 0 : 1 ))
