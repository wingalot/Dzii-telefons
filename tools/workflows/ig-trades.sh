#!/data/data/com.termux/files/usr/bin/bash
# IG Trading Trades Navigator - Stabils Trades sadaļas atvēršanas skripts
# Problēma: Klikšķi apakšējā joslā (y > 2200) trāpa uz sistēmas navigāciju un aizver app
# Risinājums: Izmantot pareizas koordinātes un swipe tehniku

set -e

# Konfigurācija
IG_PACKAGE="com.iggroup.android.cfd"
TESSDATA_PREFIX="$HOME/tessdata"
TIMESTAMP=$(date +%s)
SCREENSHOT_PATH="/sdcard/ig_trades_${TIMESTAMP}.png"
LOCAL_PATH="/data/data/com.termux/files/home/downloads/ig_trades_${TIMESTAMP}.png"
OCR_OUTPUT="$HOME/.ig_trades_positions.txt"

# Ekrāna izmēri (POCOPHONE F1)
SCREEN_WIDTH=1080
SCREEN_HEIGHT=2340

# Trades pogas koordinātes - PAREIZĀS
# Bottom nav: Markets | Trades | Explore | Account
# Trades ir 2. poga no kreisās (~x=400-500, y=2100-2180)
# Svarīgi: y < 2200, lai netrāpītu uz gesture bar
TRADES_X=450      # Vidus starp Markets un Explore
TRADES_Y=2140     # Virs gesture bar (virs 2200 ir bīstami)

# Alternatīvās koordinātes (ja app layout atšķiras)
TRADES_ALT_X=540  # Centrs
TRADES_ALT_Y=2100 

echo "🚀 IG Trading Trades Navigator"
echo "=============================="
echo "📱 Package: $IG_PACKAGE"
echo "🎯 Target: Trades tab (x=$TRADES_X, y=$TRADES_Y)"
echo ""

# 1. Pārbauda OCR datus
echo "🔍 Pārbauda OCR..."
if [[ ! -f "$TESSDATA_PREFIX/eng.traineddata" ]]; then
    echo "📥 Lejuplādē OCR datus..."
    mkdir -p "$TESSDATA_PREFIX"
    curl -sL -o "$TESSDATA_PREFIX/eng.traineddata" \
        https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
fi

# 2. Aizver IG app pilnībā
echo "🔒 Aizver IG app..."
su -c "am force-stop $IG_PACKAGE" 2>/dev/null || true
sleep 1

# 3. Atver IG app
echo "📱 Atver IG Trading app..."
su -c "monkey -p $IG_PACKAGE -c android.intent.category.LAUNCHER 1" > /dev/null 2>&1

# 4. Gaida ielādi (ilgāks laigs finanšu app)
echo "⏳ Gaida app ielādi (8 sekundes)..."
sleep 8

# 5. Pārbauda vai app ir atvēries
echo "🔍 Pārbauda vai app ir aktīvs..."
CURRENT_APP=$(su -c "dumpsys window | grep mCurrentFocus" 2>/dev/null || echo "")
if [[ "$CURRENT_APP" != *"$IG_PACKAGE"* ]]; then
    echo "⚠️  App var nebūt pilnībā ielādējies, gaida vēl..."
    sleep 5
fi

echo ""
echo "📍 Mēģina atvērt Trades sadaļu..."
echo "=============================="

# 6. Mēģinājums #1: Direct tap uz Trades (pareizās koordinātēs)
echo "🎯 Mēģinājums #1: Direct tap (x=$TRADES_X, y=$TRADES_Y)..."
su -c "input tap $TRADES_X $TRADES_Y"
sleep 3

# 7. Pārbauda vai app joprojām ir atvērts (nav crashojies)
echo "🔍 Pārbauda vai app nav aizvēries..."
APP_RUNNING=$(su -c "dumpsys activity activities | grep -c $IG_PACKAGE" 2>/dev/null || echo "0")
if [[ "$APP_RUNNING" -eq "0" ]]; then
    echo "❌ App aizvērās! Mēģina vēlreiz..."
    su -c "monkey -p $IG_PACKAGE -c android.intent.category.LAUNCHER 1" > /dev/null 2>&1
    sleep 8
    su -c "input tap $TRADES_ALT_X $TRADES_ALT_Y"
    sleep 3
fi

# 8. Mēģinājums #2: Ja joprojām Markets, mēģina swipe pa labi
echo "🔄 Mēģinājums #2: Swipe no Markets uz Trades..."
su -c "input swipe 800 2100 200 2100 300"
sleep 2

# 9. Mēģinājums #3: Alternatīva - tap zemāk/augstāk
echo "🔄 Mēģinājums #3: Alternatīvās koordinātes..."
su -c "input tap $TRADES_ALT_X $TRADES_ALT_Y"
sleep 2

# 10. Pagaida līdz Trades ielādējas
echo "⏳ Gaida Trades ielādi..."
sleep 4

echo ""
echo "📸 Taisa screenshot..."
echo "=============================="

# 11. Screenshot
su -c "screencap -p '$SCREENSHOT_PATH'"
cp "$SCREENSHOT_PATH" "$LOCAL_PATH" 2>/dev/null
echo "✅ Screenshot saglabāts: $LOCAL_PATH"

# 12. OCR
echo ""
echo "📖 OCR nolasa pozīcijas..."
echo "=============================="
export TESSDATA_PREFIX
# Izmantojam --psm 6 dokumentiem ar daudz teksta
tesseract "$LOCAL_PATH" - --psm 6 -l eng > "$OCR_OUTPUT" 2>/dev/null

# 13. Rezultāti
echo ""
echo "=============================="
echo "📋 NOLASĪTĀS POZĪCIJAS:"
echo "=============================="
cat "$OCR_OUTPUT"
echo ""
echo "=============================="
echo "💾 FAILI:"
echo "   📷 Screenshot: $LOCAL_PATH"
echo "   📝 OCR teksts: $OCR_OUTPUT"
echo "=============================="
echo ""
echo "💡 Padoms: Ja Trades sadaļa nav atvērusies, pārbaudi:"
echo "   1. Vai esi ielogojies IG app?"
echo "   2. Vai Markets sadaļa bija pilnībā ielādējusies?"
echo "   3. Ekrāna izšķirtspēja - pielāgo koordinātes ja vajag"
echo "=============================="
