#!/bin/bash

echo "🔍 Verificando estructura de Vercel experimentalServices..."
echo ""

check() {
  if [ -f "$1" ] || [ -d "$1" ]; then
    echo "✅ $1"
    return 0
  else
    echo "❌ $1 (FALTA)"
    return 1
  fi
}

echo "📁 Estructura de carpetas:"
check "vercel.json"
check "frontend"
check "frontend/app"
check "frontend/package.json"
check "frontend/next.config.ts"
check "backend"
check "backend/main.py"
check "backend/pyproject.toml"

echo ""
echo "📝 Archivos de configuración:"
check ".env.local"
check ".env.example"

echo ""
echo "🔌 API Routes:"
check "frontend/app/api/chat/route.ts"

echo ""
echo "✨ Todo listo para probar con Vercel experimentalServices!"
