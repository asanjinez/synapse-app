import uvicorn
from app.main import app

# Para desarrollo local y Vercel experimentalServices
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(__import__("os").getenv("PORT", "3001")),
        reload=False
    )
