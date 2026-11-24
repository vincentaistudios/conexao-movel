#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Script de publicacao automatizada de releases para Conexao Movel
# Repositorio oficial: https://github.com/vincentaistudios/conexao-movel

set -euo pipefail

REPO="vincentaistudios/conexao-movel"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ $# -lt 1 ]; then
    echo "Uso: $0 <versao> [caminho_dos_binarios]"
    echo "Exemplo: $0 0.1.9 /tmp/release_v0.1.9"
    exit 1
fi

RAW_VERSION="$1"
VERSION="${RAW_VERSION#v}"
TAG="v${VERSION}"
ASSETS_DIR="${2:-/tmp/release_${TAG}}"

echo "[1/6] Validando versao ${VERSION} e diretorio de assets..."

if ! [[ "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
    echo "Erro: formato de versao invalido: ${VERSION}. Use SemVer (ex: 0.1.9 ou 0.1.9-rc.1)"
    exit 1
fi

if [ ! -d "${ASSETS_DIR}" ]; then
    echo "Erro: diretorio de assets nao encontrado: ${ASSETS_DIR}"
    exit 1
fi

cd "${ROOT_DIR}"

echo "[2/6] Verificando arquivos mandatorios no diretorio de release..."
APK_FILE="${ASSETS_DIR}/ConexaoMovel-android.apk"
WIN_FILE="${ASSETS_DIR}/ConexaoMovel-Windows-setup.exe"
LINUX_FILE="${ASSETS_DIR}/ConexaoMovel-linux-x86_64"

for f in "${APK_FILE}" "${WIN_FILE}" "${LINUX_FILE}"; do
    if [ ! -f "$f" ]; then
        echo "Erro: arquivo mandatorio nao encontrado: $f"
        exit 1
    fi
done

echo "[3/6] Gerando SHA256SUMS.txt..."
cd "${ASSETS_DIR}"
sha256sum "ConexaoMovel-android.apk" > SHA256SUMS.txt
sha256sum "ConexaoMovel-Windows-setup.exe" >> SHA256SUMS.txt
sha256sum "ConexaoMovel-linux-x86_64" >> SHA256SUMS.txt

APK_SHA="$(sha256sum ConexaoMovel-android.apk | awk '{print $1}')"
WIN_SHA="$(sha256sum ConexaoMovel-Windows-setup.exe | awk '{print $1}')"
LINUX_SHA="$(sha256sum ConexaoMovel-linux-x86_64 | awk '{print $1}')"

APK_SIZE="$(stat -c%s ConexaoMovel-android.apk)"
WIN_SIZE="$(stat -c%s ConexaoMovel-Windows-setup.exe)"
LINUX_SIZE="$(stat -c%s ConexaoMovel-linux-x86_64)"

cd "${ROOT_DIR}"

echo "[4/6] Criando e enviando tag Git ${TAG}..."
if git rev-parse "${TAG}" >/dev/null 2>&1; then
    echo "Aviso: tag ${TAG} ja existe localmente."
else
    git tag -a "${TAG}" -m "Conexao Movel ${TAG}"
fi
git push origin "${TAG}" || true

echo "[5/6] Publicando release no GitHub via gh CLI..."
gh release create "${TAG}" \
    --repo "${REPO}" \
    --title "Conexão Móvel ${TAG}" \
    --notes "Release oficial ${TAG} com instaladores para Android, Windows e Linux, alem de atualizacao automatica OTA." \
    "${APK_FILE}" \
    "${WIN_FILE}" \
    "${LINUX_FILE}" \
    "${ASSETS_DIR}/SHA256SUMS.txt" || {
        echo "Aviso: release ja criada ou erro no upload. Tentando fazer upload dos assets..."
        gh release upload "${TAG}" --repo "${REPO}" --clobber \
            "${APK_FILE}" "${WIN_FILE}" "${LINUX_FILE}" "${ASSETS_DIR}/SHA256SUMS.txt" || true
    }

echo "[6/6] Atualizando feed de auto-update na branch channels (stable.json)..."
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
TEMP_FEED="$(mktemp)"

cat <<EOF > "${TEMP_FEED}"
{
  "schema": 1,
  "channel": "stable",
  "version": "${VERSION}",
  "name": "Conexão Móvel ${TAG}",
  "published": "${TIMESTAMP}",
  "notes": "https://github.com/${REPO}/releases/tag/${TAG}",
  "files": [
    {
      "name": "ConexaoMovel-Windows-setup.exe",
      "url": "https://github.com/${REPO}/releases/download/${TAG}/ConexaoMovel-Windows-setup.exe",
      "sha256": "${WIN_SHA}",
      "size": ${WIN_SIZE}
    },
    {
      "name": "ConexaoMovel-android.apk",
      "url": "https://github.com/${REPO}/releases/download/${TAG}/ConexaoMovel-android.apk",
      "sha256": "${APK_SHA}",
      "size": ${APK_SIZE}
    },
    {
      "name": "ConexaoMovel-linux-x86_64",
      "url": "https://github.com/${REPO}/releases/download/${TAG}/ConexaoMovel-linux-x86_64",
      "sha256": "${LINUX_SHA}",
      "size": ${LINUX_SIZE}
    }
  ]
}
EOF

CHANNELS_TMP="$(mktemp -d)"
git clone --depth 1 --branch channels "https://github.com/${REPO}.git" "${CHANNELS_TMP}" 2>/dev/null || {
    mkdir -p "${CHANNELS_TMP}"
    cd "${CHANNELS_TMP}"
    git init
    git checkout -b channels
    git remote add origin "https://github.com/${REPO}.git"
}

cd "${CHANNELS_TMP}"
cp "${TEMP_FEED}" stable.json
git add stable.json
git commit -m "release: atualizar feed stable para ${TAG}" || true
git push -u origin channels

rm -rf "${TEMP_FEED}" "${CHANNELS_TMP}"

echo "Publicacao da versao ${TAG} concluida com sucesso!"
echo "URL da Release: https://github.com/${REPO}/releases/tag/${TAG}"
echo "URL do Feed: https://raw.githubusercontent.com/${REPO}/channels/stable.json"
