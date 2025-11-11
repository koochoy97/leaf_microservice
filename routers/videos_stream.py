from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import os

router = APIRouter(prefix="/videos", tags=["Video Streaming"])

CHUNK_SIZE = 1024 * 1024  # 1 MB

@router.get("/{video_name}")
def stream_video(video_name: str, request: Request):
    video_path = os.path.join("videos", video_name)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video no encontrado")

    file_size = os.path.getsize(video_path)
    range_header = request.headers.get("range")

    if range_header is None:
        # 🟡 Si no hay cabecera Range, devolvemos el archivo completo (caso raro)
        def iterfile():
            with open(video_path, "rb") as f:
                yield from f
        return StreamingResponse(iterfile(), media_type="video/mp4")

    # 🧩 Parsear cabecera Range: "bytes=start-end"
    range_value = range_header.strip().lower().replace("bytes=", "")
    range_start, range_end = range_value.split("-") if "-" in range_value else (0, None)

    try:
        range_start = int(range_start)
        range_end = int(range_end) if range_end else file_size - 1
    except ValueError:
        raise HTTPException(status_code=400, detail="Cabecera Range inválida")

    if range_start >= file_size:
        raise HTTPException(status_code=416, detail="Range no satisfactoria")

    chunk_size = (range_end - range_start) + 1

    def iterfile(start: int, end: int):
        with open(video_path, "rb") as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                data = f.read(min(CHUNK_SIZE, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {range_start}-{range_end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
    }

    return StreamingResponse(iterfile(range_start, range_end), status_code=206, headers=headers, media_type="video/mp4")
