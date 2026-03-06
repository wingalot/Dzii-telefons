#!/data/data/com.termux/files/usr/bin/bash
# Device Input Tool

ACTION="$1"
shift 2>/dev/null || true

case "$ACTION" in
  tap)
    X="${1:-540}"
    Y="${2:-1200}"
    su -c "input tap $X $Y" 2>/dev/null
    echo "👆 Tapped at ($X, $Y)"
    ;;
  swipe)
    X1="${1:-540}"
    Y1="${2:-1600}"
    X2="${3:-540}"
    Y2="${4:-600}"
    DURATION="${5:-300}"
    su -c "input swipe $X1 $Y1 $X2 $Y2 $DURATION" 2>/dev/null
    echo "👆 Swiped ($X1,$Y1)→($X2,$Y2) in ${DURATION}ms"
    ;;
  text)
    TEXT="${1:-}"
    if [[ -n "$TEXT" ]]; then
      # URL encode spaces for Android input
      ENCODED=$(echo "$TEXT" | sed 's/ /%s/g')
      su -c "input text '$ENCODED'" 2>/dev/null
      echo "⌨️ Typed: $TEXT"
    fi
    ;;
  key)
    CODE="${1:-3}"
    su -c "input keyevent $CODE" 2>/dev/null
    echo "🔘 Key event: $CODE"
    ;;
  home)
    su -c "input keyevent 3" 2>/dev/null
    echo "🏠 Home pressed"
    ;;
  back)
    su -c "input keyevent 4" 2>/dev/null
    echo "◀️ Back pressed"
    ;;
  recent)
    su -c "input keyevent 187" 2>/dev/null
    echo "📋 Recent apps"
    ;;
  *)
    echo "Usage: device-input.sh {tap|swipe|text|key|home|back|recent} [args]"
    echo ""
    echo "Examples:"
    echo "  device-input.sh tap 540 1200"
    echo "  device-input.sh swipe 540 1600 540 600 300"
    echo "  device-input.sh text 'Hello World'"
    echo "  device-input.sh key 66    # ENTER"
    echo "  device-input.sh home"
    exit 1
    ;;
esac
