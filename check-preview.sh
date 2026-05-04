#!/bin/bash

echo "🚀 Verificando configuración para vista previa con experimentalServices"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (FALTA)"
        return 1
    fi
}

echo "📁 Frontend:"
check_file "frontend/package.json"
check_file "frontend/next.config.ts"
check_file "frontend/app/layout.tsx"
check_file "frontend/app/api/chat/route.ts"

echo ""
echo "🐍 Backend:"
check_file "backend/main.py"
check_file "backend/app/main.py"
check_file "backend/app/api/chat.py"
check_file "backend/pyproject.toml"

echo ""
echo "⚙️  Configuración:"
check_file "vercel.json"
check_file ".env.local"

echo ""
echo "📋 Verificación de configuración:"

# Verificar que vercel.json tiene experimentalServices
if grep -q "experimentalServices" vercel.json; then
    echo -e "${GREEN}✓${NC} vercel.json contiene experimentalServices"
else
    echo -e "${RED}✗${NC} vercel.json NO contiene experimentalServices"
fi

# Verificar que frontend/api/chat/route.ts usa /api/chat
if grep -q 'fetch("/api/chat"' frontend/app/api/chat/route.ts; then
    echo -e "${GREEN}✓${NC} frontend/app/api/chat/route.ts usa ruta correcta (/api/chat)"
else
    echo -e "${RED}✗${NC} frontend/app/api/chat/route.ts NO usa ruta correcta"
fi

echo ""
echo "✨ ¡Listo para la vista previa!"
echo ""
echo "Qué sucede cuando haces preview:"
echo "1. Vercel dev inicia frontend (Next.js) en puerto 3000"
echo "2. Vercel dev inicia backend (FastAPI) en puerto 3001 internamente"
echo "3. Las requests a /api/* son ruteadas automáticamente al backend"
echo "4. Todo funciona sin CORS porque está en el mismo dominio"
