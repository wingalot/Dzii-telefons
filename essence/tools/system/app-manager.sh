#!/data/data/com.termux/files/usr/bin/bash
# App Manager Tool

ACTION="$1"
PACKAGE="$2"
FILTER="${3:-third-party}"

case "$ACTION" in
  list)
    echo "📱 Installed packages:"
    case "$FILTER" in
      system)
        su -c "pm list packages -s" 2>/dev/null | sed 's/package:/  /'
        ;;
      third-party)
        su -c "pm list packages -3" 2>/dev/null | sed 's/package:/  /'
        ;;
      all)
        su -c "pm list packages" 2>/dev/null | sed 's/package:/  /'
        ;;
    esac
    ;;
  launch)
    if [[ -z "$PACKAGE" ]]; then
      echo "❌ Package name required"
      exit 1
    fi
    su -c "monkey -p $PACKAGE -c android.intent.category.LAUNCHER 1" 2>/dev/null
    echo "📱 Launched: $PACKAGE"
    ;;
  stop)
    if [[ -z "$PACKAGE" ]]; then
      echo "❌ Package name required"
      exit 1
    fi
    su -c "am force-stop $PACKAGE" 2>/dev/null
    echo "🛑 Stopped: $PACKAGE"
    ;;
  info)
    if [[ -z "$PACKAGE" ]]; then
      echo "❌ Package name required"
      exit 1
    fi
    echo "📋 Package info: $PACKAGE"
    su -c "dumpsys package $PACKAGE" 2>/dev/null | head -30
    ;;
  clear-data)
    if [[ -z "$PACKAGE" ]]; then
      echo "❌ Package name required"
      exit 1
    fi
    su -c "pm clear $PACKAGE" 2>/dev/null
    echo "🧹 Cleared data: $PACKAGE"
    ;;
  *)
    echo "Usage: app-manager.sh {list|launch|stop|info|clear-data} [package] [filter]"
    echo ""
    echo "Examples:"
    echo "  app-manager.sh list third-party"
    echo "  app-manager.sh launch com.whatsapp"
    echo "  app-manager.sh stop com.facebook.katana"
    exit 1
    ;;
esac
