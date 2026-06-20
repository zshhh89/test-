#!/bin/bash
set -euo pipefail

# Solo correr en entornos remotos (Claude Code en la web)
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
REQS="$REPO_DIR/requirements.txt"

if [ -f "$REQS" ]; then
  echo "Instalando dependencias de requirements.txt..."
  pip install -r "$REQS" --quiet
  # Fix de conflicto entre cffi del sistema y pdfplumber/cryptography
  pip install --upgrade cffi cryptography --ignore-installed --quiet
  echo "Dependencias instaladas correctamente."
else
  echo "No se encontró requirements.txt, omitiendo instalación."
fi

# Instalar tesseract si no está disponible (para OCR)
if ! command -v tesseract &> /dev/null; then
  echo "Instalando tesseract-ocr..."
  apt-get install -y -q tesseract-ocr 2>/dev/null || true
fi
