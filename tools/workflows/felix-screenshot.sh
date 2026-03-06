#!/data/data/com.termux/files/usr/bin/bash
# Felix Signal Screenshot - Vienkāršs screenshot grabber

set -e

TELEGRAM_PACKAGE="org.telegram.messenger.web"
TIMESTAMP=$(date +%s)
SCREENSHOT_PATH="/sdcard/felix_${TIMESTAMP}.png"
LOCAL_PATH="/data/data/com.termux/files/home/downloads/felix_${TIMESTAMP}.png"

echo "🚀 Felix Signal Screenshot"
echo "=========================="

# 1. Aizveram Telegram pilnībā (force stop)
echo "🔒 Aizver Telegram..."
su -c "am force-stop $TELEGRAM_PACKAGE" 2>/dev/null || true
sleep 1

# 2. Atveram Telegram no jauna
echo "📱 Atver Telegram..."
su -c "monkey -p $TELEGRAM_PACKAGE -c android.intent.category.LAUNCHER 1" > /dev/null 2>&1
sleep 4

# 3. Meklēšana
echo "🔍 Meklē kanālu..."
su -c "input tap 540 280"
sleep 1
su -c "input text 'felix Vip room'"
sleep 2

# 4. Ieiet kanālā
echo "👉 Atver kanālu..."
su -c "input tap 540 550"
sleep 3

# 5. Skrollē līdz apakšai (jaunākajai ziņai)
echo "⬇️ Skrollē uz jaunāko ziņu..."
for i in $(seq 1 20); do
    su -c "input swipe 540 2200 540 300 100"
    sleep 0.1
done

# 6. Screenshot
echo "📸 Taisa screenshot..."
su -c "screencap -p '$SCREENSHOT_PATH'"
cp "$SCREENSHOT_PATH" "$LOCAL_PATH" 2>/dev/null

echo ""
echo "✅ GATAVS!"
echo "📁 Screenshot: $LOCAL_PATH"
echo "=========================="
