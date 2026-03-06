#!/data/data/com.termux/files/usr/bin/bash
# Felix Signal Reader - Lightweight OCR reader (alias for quick text extraction)

set -euo pipefail

# ===== KONFIGURĀCIJA =====
STATE_DIR="${HOME}/.felix"
TESSDATA_PREFIX="${HOME}/tessdata"
TELEGRAM_PACKAGE="org.telegram.messenger.web"
DOWNLOAD_DIR="${HOME}/downloads"
TIMESTAMP=$(date +%s)

SCREENSHOT_PATH="/sdcard/felix_read_${TIMESTAMP}.png"
LOCAL_PATH="${DOWNLOAD_DIR}/felix_read_${TIMESTAMP}.png"
OCR_OUTPUT="${STATE_DIR}/.last_read.txt"

# ===== INIT =====
mkdir -p "$DOWNLOAD_DIR" "$STATE_DIR" 2>/dev/null || true

echo "🚀 Felix Signal Reader"
echo "======================"

# Pārbaudām OCR
if [[ ! -f "${TESSDATA_PREFIX}/eng.traineddata" ]]; then
    echo "📥 Downloading OCR data..."
    mkdir -p "$TESSDATA_PREFIX"
    curl -sL -o "${TESSDATA_PREFIX}/eng.traineddata" \
        "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata"
fi

# Ātrs Telegram atvēršana
echo "📱 Opening Telegram..."
su -c "am force-stop $TELEGRAM_PACKAGE" 2>/dev/null || true
sleep 0.5
su -c "am start -n ${TELEGRAM_PACKAGE}/org.telegram.ui.LaunchActivity" > /dev/null 2>&1 || \
    su -c "monkey -p $TELEGRAM_PACKAGE -c android.intent.category.LAUNCHER 1" > /dev/null 2>&1
sleep 2

# Meklējam kanālu
echo "🔍 Finding channel..."
su -c "input tap 540 280"
sleep 0.5
su -c "input text 'felix vip room'"
sleep 1
su -c "input tap 540 550"
sleep 2

# Scroll
echo "⬇️ Scrolling..."
for i in {1..15}; do
    su -c "input swipe 540 2200 540 300 100" 2>/dev/null || true
done

# Screenshot
echo "📸 Capturing..."
su -c "screencap -p '$SCREENSHOT_PATH'"
cp "$SCREENSHOT_PATH" "$LOCAL_PATH" 2>/dev/null || true

# OCR
echo "🔍 Reading text..."
export TESSDATA_PREFIX
tesseract "$LOCAL_PATH" - --oem 1 --psm 6 -l eng > "$OCR_OUTPUT" 2>/dev/null || true

echo ""
echo "======================"
echo "📋 EXTRACTED TEXT:"
echo "======================"
cat "$OCR_OUTPUT"
echo ""
echo "======================"
echo "✅ Screenshot: $LOCAL_PATH"
echo "✅ Text file:  $OCR_OUTPUT"
echo "======================"
