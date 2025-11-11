from fastapi import APIRouter, UploadFile, Form, File
import os

router = APIRouter(prefix="/upload_videos", tags=["Uploads"])

# Carpeta donde se guardarán los videos subidos
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/")
async def upload_video(
    uploadId: str = Form(...),
    chunkIndex: int = Form(...),
    totalChunks: int = Form(...),
    chunk: UploadFile = File(...),
    originalName: str = Form(...),
    mimeType: str = Form(...),
    chunkSize: int = Form(...),
    totalSize: int = Form(...),
    title: str = Form(None),
    notes: str = Form(None)
):
    """
    📹 Recibe un fragmento de un video (chunked upload).
    Cuando llega el último fragmento, une todos y devuelve el path final.
    """

    # Guardar cada chunk temporalmente
    temp_chunk_path = os.path.join(UPLOAD_DIR, f"{uploadId}_part{chunkIndex}")

    with open(temp_chunk_path, "wb") as f:
        while content := await chunk.read(1024 * 1024):
            f.write(content)

    # Si aún no es el último fragmento, confirmar recepción
    if chunkIndex < totalChunks - 1:
        return {
            "status": "chunk_received",
            "uploadId": uploadId,
            "chunkIndex": chunkIndex,
            "totalChunks": totalChunks
        }

    # 🔚 Si es el último fragmento, unir todos los pedazos
    final_filename = f"{uploadId}_{originalName}"
    final_path = os.path.join(UPLOAD_DIR, final_filename)

    with open(final_path, "wb") as final_file:
        for i in range(totalChunks):
            part_path = os.path.join(UPLOAD_DIR, f"{uploadId}_part{i}")
            with open(part_path, "rb") as part_file:
                final_file.write(part_file.read())
            os.remove(part_path)

    return {
        "status": "complete",
        "uploadId": uploadId,
        "path": final_path,
        "filename": final_filename,
        "mimeType": mimeType,
        "title": title,
        "notes": notes,
        "size": totalSize
    }
