#!/bin/bash
# Dato skrevet: 23.06.2026
# Forfatter: William Berg Steffenak - copyright
# Launcher for Lokal CRM V3.2 Layout

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_FILE="$SCRIPT_DIR/app_v32_layout.py"
LOG_FILE="$SCRIPT_DIR/Start_CRM.log"

{
  echo "================================================="
  echo "Starter Lokal CRM V3.2"
  echo "Dato skrevet: 23.06.2026"
  echo "Forfatter: William Berg Steffenak - copyright"
  echo "Katalog: $SCRIPT_DIR"
  echo "App-fil: $APP_FILE"
  echo "Tidspunkt: $(date)"
  echo "================================================="

  if [ ! -f "$APP_FILE" ]; then
    echo "FEIL: Fant ikke app_v32_layout.py i samme mappe som launcheren."
    echo "Legg Start_CRM.command i samme mappe som app_v32_layout.py."
    read -n 1 -s -r -p "Trykk en tast for å lukke..."
    exit 1
  fi

  cd "$SCRIPT_DIR" || {
    echo "FEIL: Klarte ikke å gå til prosjektmappen."
    read -n 1 -s -r -p "Trykk en tast for å lukke..."
    exit 1
  }

  echo "Sjekker Python ..."
  if ! command -v python3 >/dev/null 2>&1; then
    echo "FEIL: python3 ble ikke funnet på systemet."
    read -n 1 -s -r -p "Trykk en tast for å lukke..."
    exit 1
  fi

  echo "Python funnet: $(command -v python3)"
  echo "Starter Streamlit ..."
  python3 -m streamlit run "$APP_FILE"

  EXIT_CODE=$?
  echo ""
  echo "Streamlit avsluttet med kode: $EXIT_CODE"
  if [ $EXIT_CODE -ne 0 ]; then
    echo "Sjekk feilmeldingen over. Logg er lagret i: $LOG_FILE"
  fi
  read -n 1 -s -r -p "Trykk en tast for å lukke..."
} 2>&1 | tee "$LOG_FILE"
