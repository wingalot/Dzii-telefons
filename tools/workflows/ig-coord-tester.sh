#!/data/data/com.termux/files/usr/bin/bash
# IG Koordināšu Tester - Atrast pareizās Trades pogas koordinātes
# Lietošana: bash ~/tools/workflows/ig-coord-tester.sh

echo "🧪 IG Trading Koordināšu Tester"
echo "==============================="
echo ""
echo "Šis skripts palīdzēs atrast pareizās Trades pogas koordinātes"
echo "tavā ierīcē."
echo ""

IG_PACKAGE="com.iggroup.android.cfd"

# Atver IG app
echo "📱 Atver IG app..."
su -c "am force-stop $IG_PACKAGE" 2>/dev/null || true
sleep 1
su -c "monkey -p $IG_PACKAGE -c android.intent.category.LAUNCHER 1" > /dev/null 2>&1
echo "⏳ Gaida 8 sekundes līdz app ielādējas..."
sleep 8

echo ""
echo "==============================="
echo "🎯 Testējam koordinātes:"
echo "==============================="
echo ""

# Testējamās koordinātes
# Y=2100-2200 ir drošā zona (virs gesture bar)
declare -a COORDS=(
    "350:2160:Markets (kreisā poga)"
    "450:2160:Trades (pareizā)"
    "630:2160:Explore"
    "810:2160:Account"
    "540:2140:Trades (centrs)"
    "450:2120:Trades (augšā)"
)

for coord in "${COORDS[@]}"; do
    IFS=':' read -r x y label <<< "$coord"
    echo "👉 Testing: $label (x=$x, y=$y)"
    echo "   Klikšķis pēc 2 sekundēm..."
    sleep 2
    su -c "input tap $x $y"
    echo "   ✅ Klikšķis veikts! Vai app joprojām atvērts?"
    echo "   ⏳ Gaida 3 sekundes..."
    sleep 3
    
    # Pārbauda vai app nav aizvēries
    APP_RUNNING=$(su -c "dumpsys activity activities | grep -c $IG_PACKAGE" 2>/dev/null || echo "0")
    if [[ "$APP_RUNNING" -eq "0" ]]; then
        echo "   ❌ APP AIZVĒRĀS - šīs koordinātes NAV DROŠAS!"
        echo ""
        # Atver atpakaļ
        su -c "monkey -p $IG_PACKAGE -c android.intent.category.LAUNCHER 1" > /dev/null 2>&1
        sleep 6
    else
        echo "   ✅ App joprojām atvērts"
    fi
    echo ""
done

echo "==============================="
echo "📝 Ieteikumi:"
echo "==============================="
echo ""
echo "Ja Trades neatvērās ar nevienu koordināti:"
echo "1. Pārbaudi vai esi Markets sadaļā pirms testa"
echo "2. Vari mainīt Y vērtību (2160, 2140, 2120, 2100)"
echo "3. Vari mainīt X vērtību (350, 400, 450, 500)"
echo ""
echo "Pareizās koordinātes ieraksti ~/tools/workflows/ig-trades.sh:"
echo '  TRADES_X=TAVA_X'
echo '  TRADES_Y=TAVA_Y'
