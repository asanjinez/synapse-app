# Setup de Synapse App con Vercel experimentalServices

## Cambios Realizados

Tu proyecto ahora está configurado para ejecutar el **frontend Next.js y backend FastAPI en una sola plataforma Vercel** usando `experimentalServices`.

### Estructura Nueva

```
synapse-app/
├── vercel.json              # Configura los servicios (nuevo)
├── .env.local              # Variables de entorno
├── frontend/               # Next.js app (movido de raíz)
│   ├── app/
│   ├── components/
│   ├── package.json
│   └── next.config.ts
├── backend/                # FastAPI app (sin cambios)
│   ├── app/
│   ├── main.py
│   └── pyproject.toml
```

### Cambios en el Código

1. **API Route actualizado**: `frontend/app/api/chat/route.ts`
   - Antes: `fetch(`${BACKEND_URL}/api/chat`)`
   - Ahora: `fetch("/api/chat")`
   - Vercel rutea automáticamente `/api/*` al backend Python

2. **vercel.json creado**:
   - Define que `/api/*` va al backend FastAPI
   - Todo lo demás va al frontend Next.js
   - Las variables de entorno se comparten automáticamente

## Pruebas

### Opción 1: En la vista previa de v0

La vista previa ejecutará ambos servicios automáticamente gracias a Vercel experimentalServices. Deberías ver:
- Puerto 3000: Frontend Next.js
- Puerto 3001+: Backend FastAPI (interno)

Para probar, **necesitas las variables de entorno**:
1. Haz clic en Settings (engranaje arriba a la derecha)
2. Seccion **Vars**
3. Agrega:
   - `DATABASE_URL`: Tu URL de Neon PostgreSQL
   - `VERCEL_AI_GATEWAY_KEY`: Tu API key del AI Gateway

Una vez configuradas, la vista previa debería funcionar automáticamente.

### Opción 2: Deploy a Vercel

1. **Pushea el código a GitHub**:
   ```bash
   git add .
   git commit -m "Configure Vercel experimentalServices for Python backend"
   git push
   ```

2. **En Vercel**:
   - Ve a tu proyecto
   - Settings > Build and Deployment
   - Cambia "Framework Preset" a "Services" (o "Other")
   - Vercel detectará `vercel.json` automáticamente

3. **Configura las variables de entorno** en Vercel:
   - `DATABASE_URL`: URL de Neon
   - `VERCEL_AI_GATEWAY_KEY`: Tu API key

4. **Deploy**: El botón "Publish" o espera a que GitHub Actions haga auto-deploy

## Variables de Entorno Necesarias

### Para Desarrollo Local

Crea o actualiza `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
VERCEL_AI_GATEWAY_KEY=tu-api-key-aqui
MODEL_NAME=anthropic/claude-sonnet-4-6
EMBEDDING_MODEL=text-embedding-3-small
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
FRONTEND_URL=http://localhost:3000
```

### Para Vercel (Settings > Vars)

```
DATABASE_URL = postgresql+asyncpg://...
VERCEL_AI_GATEWAY_KEY = tu-api-key-aqui
MODEL_NAME = anthropic/claude-sonnet-4-6
EMBEDDING_MODEL = text-embedding-3-small
FRONTEND_URL = https://tu-app.vercel.app
```

## Cómo Funciona

```
Cliente Browser (Puerto 3000)
         ↓
    Next.js Frontend
         ↓
  /api/* requests
         ↓
   Vercel Router
         ↓
  FastAPI Backend (interno)
         ↓
   PostgreSQL (Neon)
```

- **Sin CORS**: Mismo dominio automáticamente
- **Un solo deploy**: Todo en Vercel
- **Variables compartidas**: Accesibles en frontend y backend

## Verificación

Para verificar que todo está bien configurado:

1. **Frontend debe poder llamar al backend**:
   ```typescript
   // En frontend/app/api/chat/route.ts
   const res = await fetch("/api/chat", { ... })
   ```

2. **Backend puede recibir la request**:
   ```python
   # En backend/main.py
   @app.post("/chat")
   async def chat(request: Request):
       # Esto recibe la request de /api/chat
   ```

3. **Variables están disponibles en ambos**:
   - `process.env.DATABASE_URL` (Next.js)
   - `os.environ["DATABASE_URL"]` (FastAPI)

## Próximos Pasos

1. **Configura las variables de entorno en v0 Settings**
2. **Prueba en la vista previa** (debería funcionar si todo está correcto)
3. **Si hay errores**, revisa los logs en Vercel
4. **Haz el deploy** cuando esté listo

---

¿Preguntas? Todo está en un solo proyecto ahora, sin necesidad de servicios externos.
