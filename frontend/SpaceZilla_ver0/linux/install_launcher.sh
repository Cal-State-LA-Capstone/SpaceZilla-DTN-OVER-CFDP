#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$SCRIPT_DIR/spacezilla.desktop.template"
OUTPUT="$HOME/.local/share/applications/spacezilla.desktop"
RUN_SCRIPT="$APP_DIR/run_spacezilla.sh"
ICON_PATH="$APP_DIR/icons/SpaceZillaLogo.png"

mkdir -p "$HOME/.local/share/applications"

sed \
  -e "s|__RUN_SCRIPT_PATH__|$RUN_SCRIPT|g" \
  -e "s|__ICON_PATH__|$ICON_PATH|g" \
  "$TEMPLATE" > "$OUTPUT"

chmod +x "$OUTPUT"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" || true
fi

echo "Installed SpaceZilla launcher to: $OUTPUT"
echo "You can now search for SpaceZilla in the Ubuntu app menu."
