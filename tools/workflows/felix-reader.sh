#!/data/data/com.termux/files/usr/bin/bash
# Felix Signal Reader - OCR versija, teksta izvade

set -e

TELEGRAM_PACKAGE="org.telegram.messenger.web"
TESSDATA_PREFIX="$HOME/tessdata"
TIMESTAMP=$(date +%s)
SCREENSHOT_PATH="/sdcard/felix_${TIMESTAMP}.png"
LOCAL_PATH="/data/data/com.termux/files/home/downloads/felix_${TIMESTAMP}.png"
OCR_OUTPUT="$HOME/.felix_last_signal.txt"

echo "🚀 Felix Signal Reader (OCR)"
echo "============================"

# 1. Pārbaudām OCR
echo "🔍 Pārbauda OCR..."
if [[ ! -f "$TESSDATA_PREFIX/eng.traineddata" ]]; then
    echo "📥 Lejuplādē OCR datus..."
    mkdir -p "$TESSDATA_PREFIX"
    curl -sL -o "$TESSDATA_PREFIX/eng.traineddata" \
        https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
fi

# 2. Aizver Telegram
echo "🔒 Aizver Telegram..."
su -c "am force-stop $TELEGRAM_PACKAGE" 2>/dev/null || true
sleep 1

# 3. Atver Telegram
echo "📱 Atver Telegram..."
su -c "monkey -p $TELEGRAM_PACKAGE -c android.intent.category.LAUNCHER 1" > /dev/null 2>&1
sleep 4

# 4. Meklē kanālu
echo "🔍 Meklē kanālu..."
su -c "input tap 540 280"
sleep 1
su -c "input text 'felix Vip room'"
sleep 2

# 5. Atver kanālu
echo "👉 Atver kanālu..."
su -c "input tap 540 550"
sleep 3

# 6. Skrollē līdz apakšai
echo "⬇️ Skrollē uz jaunāko ziņu..."
for i in $(seq 1 20); do
    su -c "input swipe 540 2200 540 300 100"
    sleep 0.1
done

# 7. Screenshot
echo "📸 Taisa screenshot..."
su -c "screencap -p '$SCREENSHOT_PATH'"
cp "$SCREENSHOT_PATH" "$LOCAL_PATH" 2>/dev/null

# 8. OCR - nolasa tekstu
echo "📖 OCR nolasa..."
export TESSDATA_PREFIX
tesseract "$LOCAL_PATH" - > "$OCR_OUTPUT" 2>/dev/null

echo ""
echo "============================"
echo "📋 NOLASAIS TEKSTS:"
echo "============================"
cat "$OCR_OUTPUT"
echo ""
echo "============================"
echo "✅ Screenshot: $LOCAL_PATH"
echo "✅ OCR teksts: $OCR_OUTPUT"
echo "============================"
