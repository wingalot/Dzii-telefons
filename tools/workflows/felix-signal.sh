#!/data/data/com.termux/files/usr/bin/bash
# Felix Signal Extractor - Automātiski nolasa trading signālus no Felix VIP room

set -e

# Konfigurācija
TELEGRAM_PACKAGE="org.telegram.messenger.web"
SCREENSHOT_PATH="/sdcard/felix_signal_$(date +%s).png"
LOCAL_PATH="/data/data/com.termux/files/home/downloads/$(basename $SCREENSHOT_PATH)"
TESSDATA_PREFIX="$HOME/tessdata"

# Krāsas outputam
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Felix Signal Extractor${NC}"
echo "=============================="

# 1. Pārbaudām vai tesseract ir
echo -e "${YELLOW}📋 Pārbaude: OCR rīks...${NC}"
if ! command -v tesseract &> /dev/null; then
    echo -e "${RED}❌ Tesseract nav instalēts!${NC}"
    echo "Instalē: pkg install tesseract"
    exit 1
fi

# 2. Pārbaudām tessdata
if [[ ! -f "$TESSDATA_PREFIX/eng.traineddata" ]]; then
    echo -e "${YELLOW}📥 Lejuplādē OCR datus...${NC}"
    mkdir -p "$TESSDATA_PREFIX"
    curl -L -o "$TESSDATA_PREFIX/eng.traineddata" \
        https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
fi

# 3. Atveram Telegram
echo -e "${YELLOW}📱 Atver Telegram...${NC}"
su -c "monkey -p $TELEGRAM_PACKAGE -c android.intent.category.LAUNCHER 1" > /dev/null 2>&1
sleep 3

# 4. Kliku uz search jomas
echo -e "${YELLOW}🔍 Meklē 'felix vip room'...${NC}"
su -c "input tap 540 280"
sleep 1

# 5. Ievadam meklējamo
echo -e "${YELLOW}⌨️ Ievada tekstu...${NC}"
su -c "input text 'felix Vip room'"
sleep 2

# 6. Kliku uz pirmā rezultāta
echo -e "${YELLOW}👉 Ieiet kanālā...${NC}"
su -c "input tap 540 550"
sleep 2

# 7. Dziļa skrollēšana uz apakšu
echo -e "${YELLOW}⬇️ Skrollē uz leju...${NC}"
for i in $(seq 1 15); do
    su -c "input swipe 540 2200 540 300 150"
    sleep 0.1
done

# 8. Screenshot
echo -e "${YELLOW}📸 Taisa screenshot...${NC}"
su -c "screencap -p '$SCREENSHOT_PATH'"
cp "$SCREENSHOT_PATH" "$LOCAL_PATH" 2>/dev/null

# 9. OCR - nolasām tekstu
echo -e "${YELLOW}🔍 OCR nolasa tekstu...${NC}"
echo "=============================="
echo ""

export TESSDATA_PREFIX
OCR_TEMP="$HOME/.felix_ocr.txt"
tesseract "$LOCAL_PATH" - 2>/dev/null | tee "$OCR_TEMP"

# 10. Parsējam signālu
echo ""
echo "=============================="
echo -e "${GREEN}📊 IZVĒRTĒTAIS SIGNALS:${NC}"
echo "=============================="

# Meklējam signāla rindas ar elastīgāku matching
if grep -qiE "(SIGNAL|GNAL|ALERT)" "$OCR_TEMP"; then
    # Signal tips (BUY/SELL)
    SIGNAL_TYPE=$(grep -ioE "(BUY|SELL)" "$OCR_TEMP" | tail -1 | tr '[:lower:]' '[:upper:]' || echo "N/A")
    
    # Valūtu pāris (XAUUSD, EURUSD, utt)
    PAIR=$(grep -oE "(XAUUSD|EURUSD|GBPUSD|USDJPY|US30|NASDAQ)" "$OCR_TEMP" | tail -1 || echo "N/A")
    
    # Ieejas cena - meklējam skaitli aiz valūtu pāra
    PRICE=$(grep -E "(XAUUSD|EURUSD|GBPUSD|USDJPY|US30|NASDAQ)" "$OCR_TEMP" | grep -oE "[0-9]+\.[0-9]+" | tail -1 || echo "N/A")
    
    # Take Profits
    TP1=$(grep "TP1" "$OCR_TEMP" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "N/A")
    TP2=$(grep "TP2" "$OCR_TEMP" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "N/A")
    TP3=$(grep "TP3" "$OCR_TEMP" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "N/A")
    
    # Stop Loss
    SL=$(grep "SL" "$OCR_TEMP" | grep -oE "[0-9]+\.[0-9]+" | head -1 || echo "N/A")
    
    # Pips skaits (ja ir)
    PIPS=$(grep -oE "[0-9]+ pips" "$OCR_TEMP" | grep -oE "[0-9]+" | head -1 || echo "N/A")
    
    echo ""
    echo "🎯 Signāls: ${SIGNAL_TYPE}"
    echo "💱 Pāris: ${PAIR}"
    echo "💰 Ieejas cena: ${PRICE}"
    echo ""
    echo "🎯 Take Profits:"
    echo "   TP1: ${TP1}"
    echo "   TP2: ${TP2}"
    echo "   TP3: ${TP3}"
    echo ""
    echo "🛡️ Stop Loss: ${SL}"
    [[ "$PIPS" != "N/A" ]] && echo "📊 Risk: ${PIPS} pips"
    echo ""
else
    echo -e "${RED}❌ Signāls nav atrasts OCR tekstā${NC}"
fi

echo "=============================="
echo -e "${GREEN}✅ Screenshot saglabāts:${NC} $LOCAL_PATH"
echo "=============================="

# Izdrukājam pilnu OCR tekstu vēlreiz
echo ""
echo -e "${YELLOW}📝 Pilns OCR teksts:${NC}"
cat "$OCR_TEMP"
