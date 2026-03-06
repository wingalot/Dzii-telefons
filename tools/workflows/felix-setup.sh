#!/data/data/com.termux/files/usr/bin/bash
# Felix Setup - Uzstāda monitoringu

WORKFLOW_DIR="/data/data/com.termux/files/home/.openclaw/workspace-thinker/tools/workflows"

echo "🔧 Felix Signal Monitor Setup"
echo "=============================="
echo ""

# Padarām izpildāmus
chmod +x "$WORKFLOW_DIR"/felix-*.sh

echo "✅ Skripti gatavi:"
echo ""
echo "1️⃣  Lietošana (MANUĀLI):"
echo "   bash tools/workflows/felix-monitor.sh"
echo ""
echo "2️⃣  Lietošana (CRON - ietaupa visvairāk tokenus):"
echo ""
echo "   # Pievieno cron job (katras 20 sekundes):"
echo "   crontab -e"
echo ""
echo "   */1 * * * * bash $WORKFLOW_DIR/felix-check.sh || bash $WORKFLOW_DIR/felix-smart-screenshot.sh >> ~/.felix_cron.log 2>&1"
echo "   * * * * * sleep 20; bash $WORKFLOW_DIR/felix-check.sh || bash $WORKFLOW_DIR/felix-smart-screenshot.sh >> ~/.felix_cron.log 2>&1"
echo "   * * * * * sleep 40; bash $WORKFLOW_DIR/felix-check.sh || bash $WORKFLOW_DIR/felix-smart-screenshot.sh >> ~/.felix_cron.log 2>&1"
echo ""
echo "3️⃣  Lietošana (LOOP):"
echo "   CHECK_INTERVAL=15 bash $WORKFLOW_DIR/felix-monitor.sh"
echo ""
echo "=============================="
echo ""

# Testa palaist
echo "🧪 Palaist testa check? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo ""
    bash "$WORKFLOW_DIR/felix-check.sh"
    
    if [[ $? -eq 1 ]]; then
        echo ""
        echo "🆕 Atrasts jauns signāls! Sūtīt uz AI? (y/n)"
        read -r ai_response
        if [[ "$ai_response" =~ ^[Yy]$ ]]; then
            bash "$WORKFLOW_DIR/felix-smart-screenshot.sh"
        fi
    fi
fi
