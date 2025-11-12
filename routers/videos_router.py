from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import os, re

router = APIRouter(prefix="/videos", tags=["Video Streaming"])

VIDEO_DIR = "videos"
os.makedirs(VIDEO_DIR, exist_ok=True)


@router.get("/{filename}")
async def stream_video(filename: str, request: Request):
    """
    Sirve un video con soporte de Range (para saltar entre posiciones) y CORS abierto.
    Ejemplo de uso en el front:
    <video src="http://localhost:8000/videos/mi_video.mp4" controls crossorigin="anonymous"></video>
    """
    file_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video no encontrado")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")
    start, end = 0, file_size - 1

    if range_header:
        match = re.search(r"bytes=(\d+)-(\d*)", range_header)
        if match:
            start = int(match.group(1))
            if match.group(2):
                end = int(match.group(2))
        if start >= file_size:
            raise HTTPException(status_code=416, detail="Rango fuera de límites")

    def iterfile(start_pos, end_pos):
        with open(file_path, "rb") as f:
            f.seek(start_pos)
            remaining = end_pos - start_pos + 1
            chunk_size = 1024 * 1024
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)

    headers = {
        "Content-Type": "video/mp4",
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges",  # 👈 esta línea nueva
        "Cache-Control": "no-cache",
    }


    return StreamingResponse(iterfile(start, end), status_code=206, headers=headers)
