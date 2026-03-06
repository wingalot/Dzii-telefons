#!/data/data/com.termux/files/usr/bin/bash
# ============================================
# IG Trading - Orders Tab Navigation
# ============================================

set -e

# IG App package
IG_PACKAGE="com.iggroup.android.cfd"

# Screen coordinates (1080x2400)
TRADES_X=450
TRADES_Y=2140
ORDERS_TAB_X=200
ORDERS_TAB_Y=400

# Screenshot path
SCREENSHOT_FILE="/sdcard/ig_orders_$(date +%s).png"

echo "🚀 Starting IG Orders Tab navigation..."

# 1. Force-stop IG app
echo "📱 Force-stopping IG app..."
su -c "am force-stop $IG_PACKAGE" 2>/dev/null || am force-stop $IG_PACKAGE 2>/dev/null || echo "Could not force-stop (may not be running)"
sleep 1

# 2. Open IG app
echo "📱 Opening IG app..."
su -c "monkey -p $IG_PACKAGE -c android.intent.category.LAUNCHER 1" 2>/dev/null || monkey -p $IG_PACKAGE -c android.intent.category.LAUNCHER 1 2>/dev/null
echo "⏳ Waiting 8 seconds for app to load..."
sleep 8

# 3. Navigate to Trades section (bottom navigation)
echo "📍 Clicking Trades tab (x=$TRADES_X, y=$TRADES_Y)..."
su -c "input tap $TRADES_X $TRADES_Y" 2>/dev/null || input tap $TRADES_X $TRADES_Y
sleep 2

# 4. Click on Orders tab
echo "📋 Clicking Orders tab (x=$ORDERS_TAB_X, y=$ORDERS_TAB_Y)..."
su -c "input tap $ORDERS_TAB_X $ORDERS_TAB_Y" 2>/dev/null || input tap $ORDERS_TAB_X $ORDERS_TAB_Y
sleep 2

# 5. Take screenshot
echo "📸 Taking screenshot..."
su -c "screencap '$SCREENSHOT_FILE'" 2>/dev/null || screencap '$SCREENSHOT_FILE'
echo "✅ Screenshot saved: $SCREENSHOT_FILE"

# 6. Try to OCR or extract text
echo "🔍 Analyzing screen content..."
sleep 1

# Try to get window content text
WINDOW_TEXT=$(su -c "dumpsys window windows | grep -i 'orders\|pending'" 2>/dev/null || echo "")
if [ -n "$WINDOW_TEXT" ]; then
    echo "📄 Found text: $WINDOW_TEXT"
fi

# Alternative: use uiautomator if available
UI_TEXT=$(su -c "uiautomator dump /sdcard/ui_orders.xml 2>/dev/null && cat /sdcard/ui_orders.xml | grep -oE 'text=\"[^\"]*\"' | head -20" 2>/dev/null || echo "")
if [ -n "$UI_TEXT" ]; then
    echo "📝 UI Elements:"
    echo "$UI_TEXT" | head -10
fi

echo ""
echo "✅ IG Orders tab navigation complete!"
echo "📸 Screenshot: $SCREENSHOT_FILE"

# Pull screenshot to local if requested
if [ "$1" == "--pull" ]; then
    LOCAL_FILE="/data/data/com.termux/files/home/ig_orders_$(date +%s).png"
    cp "$SCREENSHOT_FILE" "$LOCAL_FILE" 2>/dev/null || su -c "cp '$SCREENSHOT_FILE' '$LOCAL_FILE'" 2>/dev/null
    echo "📁 Copied to: $LOCAL_FILE"
fi
