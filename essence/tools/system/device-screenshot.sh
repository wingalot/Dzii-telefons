#!/data/data/com.termux/files/usr/bin/bash
# Device Screenshot Tool

OUTPUT_PATH="${1:-/sdcard/screenshot_$(date +%s).png}"
PULL="${2:-false}"

echo "📸 Taking screenshot..."
su -c "screencap -p '$OUTPUT_PATH'" 2>/dev/null

if [[ $? -eq 0 ]]; then
  echo "✅ Screenshot saved: $OUTPUT_PATH"
  
  # Get file size
  SIZE=$(su -c "stat -c%s '$OUTPUT_PATH'" 2>/dev/null)
  echo "📊 Size: $SIZE bytes"
  
  if [[ "$PULL" == "true" && "$OUTPUT_PATH" == /sdcard/* ]]; then
    LOCAL_PATH="/data/data/com.termux/files/home/downloads/$(basename $OUTPUT_PATH)"
    cp "$OUTPUT_PATH" "$LOCAL_PATH" 2>/dev/null
    echo "📥 Pulled to: $LOCAL_PATH"
  fi
else
  echo "❌ Screenshot failed"
  exit 1
fi
