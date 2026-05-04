# 🚀 Quick Start - Vercel experimentalServices

## ¿Qué pasó?

Tu app ahora corre **TODO en Vercel**:
- Frontend Next.js + Backend FastAPI = **Un solo deploy**
- Sin CORS, sin servicios externos, sin complicaciones

## 3 Pasos para Probar

### 1️⃣ Configura las Variables de Entorno

Ve a **Settings** (engranaje 🔧 arriba a la derecha) → **Vars**

Agrega estas variables:

| Variable | Valor |
|----------|-------|
| `DATABASE_URL` | Tu URL de Neon PostgreSQL |
| `VERCEL_AI_GATEWAY_KEY` | Tu API key del AI Gateway |
| `MODEL_NAME` | `anthropic/claude-sonnet-4-6` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` |
| `FRONTEND_URL` | `http://localhost:3000` (en dev) |

### 2️⃣ Prueba en la Vista Previa

La vista previa ya está ejecutando ambos servicios.

**El frontend llamará a `/api/chat` → Vercel lo rutea al backend Python → Tu LangGraph agent responde**

### 3️⃣ Haz Deploy

Cuando esté listo:
1. Haz push a GitHub
2. Vercel detecta automáticamente `vercel.json`
3. Click "Publish" ✨

## Cómo Funciona

```
Tu Browser
    ↓
Frontend Next.js (Puerto 3000)
    ↓
fetch("/api/chat")
    ↓
Vercel detecta /api/* → Rutea al backend
    ↓
Backend FastAPI (Puerto 3001+, interno)
    ↓
LangGraph Agent
    ↓
PostgreSQL (Neon)
```

## Estructura

```
frontend/          ← Next.js
  ├── app/api/chat/route.ts   (llamada a /api/chat)
  └── package.json
backend/           ← FastAPI + LangGraph
  ├── main.py      (nuevo entrypoint)
  ├── app/
  └── pyproject.toml
vercel.json        (configuración de servicios)
```

## Variables en la Preview

En la vista previa v0, **Vercel automáticamente**:
- ✅ Corre el frontend en puerto 3000
- ✅ Corre el backend en un puerto interno
- ✅ Comparte todas las variables de entorno
- ✅ Rutea `/api/*` al backend

## Debugging

Si algo no funciona:

1. **Backend no inicia**: Revisa que `backend/pyproject.toml` sea válido
2. **API no responde**: Verifica que `DATABASE_URL` y `VERCEL_AI_GATEWAY_KEY` estén en Variables
3. **CORS error**: Usa `/api/chat`, NO URLs externas

## Comandos Útiles

```bash
# Ver estructura
./verify-structure.sh

# Si necesitas correr localmente (requiere Vercel CLI)
# vercel dev
```

---

¿Preguntas? Todo está en un solo lugar ahora.
