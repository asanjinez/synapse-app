from fastapi import APIRouter, UploadFile, File, Form

router = APIRouter()


# With routePrefix "/backend", this will be accessible at /backend/upload
@router.post("/upload")
async def upload(user_id: str = Form(...), file: UploadFile = File(...)):
    # Phase 3: docling-mcp → chunks → pgvector
    return {"status": "received", "filename": file.filename, "user_id": user_id}
