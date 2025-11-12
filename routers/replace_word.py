from fastapi import APIRouter, UploadFile, Form, File, HTTPException, Request
from fastapi.responses import JSONResponse
import os, uuid, time, subprocess, math, requests

router = APIRouter(prefix="/extract_frames", tags=["Video Processing"])

# === Directorios ===
UPLOAD_DIR = "uploads"
FRAMES_DIR = "frames"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)


# ==========================
#  Funciones auxiliares
# ==========================
def _ffprobe_duration_seconds(path: str) -> float:
    """Obtiene la duración del video en segundos usando ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=nk=1:nw=1", path],
            capture_output=True, text=True, check=True
        )
        dur = float(result.stdout.strip())
        if not math.isfinite(dur) or dur <= 0:
            raise ValueError("Duración inválida")
        return dur
    except Exception as e:
        raise RuntimeError(f"No se pudo obtener la duración: {e}")


def _extract_frames_ffmpeg(video_path: str, upload_id: str):
    """Extrae 1 frame cada 5 segundos con timestamps exactos usando -ss."""
    print("🎞️ Extrayendo frames cada 5s con FFmpeg...")

    duration = _ffprobe_duration_seconds(video_path)
    print(f"⏱️ Duración detectada: {duration:.2f}s")

    times = [t for t in range(5, int(duration) + 1, 5)]
    frame_info = []
    index = 1

    for t in times:
        frame_name = f"{upload_id}_frame_{index:04d}.jpg"
        frame_path = os.path.join(FRAMES_DIR, frame_name)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(t),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            frame_path,
            "-loglevel", "error"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"⚠️ Error extrayendo frame en t={t}s: {result.stderr.strip()}")
            continue

        frame_info.append({
            "frame": frame_name,
            "time_sec": float(t),
            "path": f"/frames/{frame_name}"
        })
        print(f"🧩 Frame {index} @ {t}s → {frame_name}")
        index += 1

    if not frame_info:
        raise RuntimeError("No se generó ningún frame")

    print(f"✅ {len(frame_info)} frames extraídos correctamente.")
    return frame_info


# ==========================
#  1️⃣ Upload por chunks
# ==========================
@router.post("/")
async def extract_frames(
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
    """Recibe video en chunks, lo ensambla, extrae los frames y elimina el video al final."""

    print("\n🟦 --- NUEVO REQUEST ---")
    print(f"🧩 uploadId: {uploadId}")
    print(f"📦 Chunk recibido: {chunkIndex + 1}/{totalChunks}")
    print(f"📁 Nombre original: {originalName}")

    start_time = time.time()
    temp_chunk_path = os.path.join(UPLOAD_DIR, f"{uploadId}_part{chunkIndex}")

    # Guardar chunk temporalmente
    try:
        with open(temp_chunk_path, "wb") as f:
            while content := await chunk.read(1024 * 1024):
                f.write(content)
        print(f"✅ Chunk {chunkIndex} guardado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando chunk {chunkIndex}: {e}")

    if chunkIndex + 1 < totalChunks:
        return {"status": "chunk_received", "chunkIndex": chunkIndex}

    # Ensamblar el video final temporal
    final_filename = f"{uploadId}_{originalName}"
    final_path = os.path.join(UPLOAD_DIR, final_filename)

    try:
        with open(final_path, "wb") as final_file:
            for i in range(totalChunks):
                part_path = os.path.join(UPLOAD_DIR, f"{uploadId}_part{i}")
                if not os.path.exists(part_path):
                    raise RuntimeError(f"Falta chunk {i}")
                with open(part_path, "rb") as p:
                    final_file.write(p.read())
                os.remove(part_path)
        print(f"✅ Video ensamblado: {final_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ensamblando video: {e}")

    # Extraer frames
    frames = _extract_frames_ffmpeg(final_path, uploadId)

    # Eliminar video temporal
    os.remove(final_path)
    print(f"🗑️ Video temporal eliminado: {final_path}")

    print(f"✅ Proceso completo ({len(frames)} frames) en {time.time() - start_time:.1f}s")

    return {
        "status": "complete",
        "uploadId": uploadId,
        "frames_extracted": len(frames),
        "frames": frames
    }


# ==========================
#  2️⃣ Eliminar frames por uploadId
# ==========================
@router.post("/cleanup")
async def cleanup_files(request: Request):
    """Elimina todos los frames generados para un uploadId (por ejemplo, al cerrar el navegador)."""
    data = await request.json()
    upload_id = data.get("uploadId")

    if not upload_id:
        raise HTTPException(status_code=400, detail="uploadId requerido")

    deleted = 0
    for file in os.listdir(FRAMES_DIR):
        if file.startswith(upload_id):
            os.remove(os.path.join(FRAMES_DIR, file))
            deleted += 1

    print(f"🧹 Cleanup: {deleted} frames eliminados para uploadId={upload_id}")
    return {"status": "ok", "deleted": deleted}


# ==========================
#  3️⃣ Extraer frames desde URL
# ==========================
@router.post("/from_url")
async def extract_frames_from_url(video_url: str = Form(...)):
    """
    Descarga un video desde una URL (ej. Dropbox raw) y extrae 1 frame cada 5 segundos.
    No guarda el video completo, solo los frames.
    """
    start = time.time()
    upload_id = str(uuid.uuid4())
    tmp_video_path = os.path.join(UPLOAD_DIR, f"{upload_id}.mp4")

    print(f"⬇️ Descargando video desde: {video_url}")
    try:
        r = requests.get(video_url, stream=True)
        r.raise_for_status()
        with open(tmp_video_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Video descargado temporalmente en {tmp_video_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo descargar el video: {e}")

    try:
        frames = _extract_frames_ffmpeg(tmp_video_path, upload_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_video_path):
            os.remove(tmp_video_path)
            print(f"🗑️ Video temporal eliminado: {tmp_video_path}")

    print(f"✅ Extracción finalizada ({len(frames)} frames) en {time.time() - start:.1f}s")

    return {
        "status": "complete",
        "uploadId": upload_id,
        "frames_extracted": len(frames),
        "frames": frames
    }
