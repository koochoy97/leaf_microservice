from fastapi import APIRouter, UploadFile, Form, File, HTTPException, Request
import os, uuid, time, subprocess, math, requests, shutil

router = APIRouter(prefix="/extract_frames", tags=["Video Processing"])

# == Version Build ==
BUILD_VERSION = "2025-11-12-1"  # cambia este número cada vez que rebuildes
print(f"🚀 Iniciando API Video Processor - Build {BUILD_VERSION}")
print(f"📁 Ejecutando desde archivo: {__file__}")
print(f"📂 Directorio actual: {os.getcwd()}")

# === Directorios ===
UPLOAD_DIR = "uploads"
FRAMES_DIR = "frames"
VIDEOS_DIR = "videos"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# ==========================
#  Funciones auxiliares
# ==========================
def _ffprobe_duration_seconds(path: str) -> float:
    """Obtiene la duración del video en segundos usando ffprobe."""
    print("📏 [ffprobe] Obteniendo duración del video...")
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=nk=1:nw=1", path
            ],
            capture_output=True, text=True, check=True
        )
        dur = float(result.stdout.strip())
        print(f"✅ [ffprobe] Duración detectada: {dur:.2f} segundos.")
        if not math.isfinite(dur) or dur <= 0:
            raise ValueError("Duración inválida")
        return dur
    except Exception as e:
        print(f"❌ [ffprobe] Error al obtener duración: {e}")
        raise RuntimeError(f"No se pudo obtener la duración: {e}")

def _extract_frames_ffmpeg(video_path: str, upload_id: str):
    """Extrae 1 frame cada 5 segundos usando FFmpeg y devuelve metadatos."""
    print("🎞️ [FFMPEG] Iniciando extracción de frames cada 5 segundos...")
    duration = _ffprobe_duration_seconds(video_path)
    print(f"⏱️ [FFMPEG] Duración total del video: {duration:.2f}s")

    times = [t for t in range(5, int(duration) + 1, 5)]
    frame_info = []
    index = 1

    for t in times:
        frame_name = f"{upload_id}_frame_{index:04d}.jpg"
        frame_path = os.path.join(FRAMES_DIR, frame_name)
        print(f"🧩 [FFMPEG] Extrayendo frame {index} en segundo {t}...")

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
            print(f"⚠️ [FFMPEG] Error extrayendo frame en t={t}s: {result.stderr.strip()}")
            continue

        print(f"✅ [FFMPEG] Frame {index} generado: {frame_path}")
        frame_info.append({
            "frame": frame_name,
            "time_sec": float(t),
            "path": f"/frames/{frame_name}"
        })
        index += 1

    if not frame_info:
        print("❌ [FFMPEG] No se generó ningún frame.")
        raise RuntimeError("No se generó ningún frame")

    print(f"🎉 [FFMPEG] {len(frame_info)} frames extraídos correctamente.")
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
    print("\n🟦 ========================")
    print("🟦 NUEVA PETICIÓN /extract_frames")
    print("🟦 ========================")
    print(f"🧩 uploadId: {uploadId}")
    print(f"📦 Chunk recibido: {chunkIndex + 1}/{totalChunks}")
    print(f"📁 Nombre original: {originalName}")
    print("----------------------------------------")

    start_time = time.time()
    temp_chunk_path = os.path.join(UPLOAD_DIR, f"{uploadId}_part{chunkIndex}")

    # Guardar chunk temporalmente
    try:
        with open(temp_chunk_path, "wb") as f:
            while content := await chunk.read(1024 * 1024):
                f.write(content)
        print(f"✅ Chunk {chunkIndex} guardado en {temp_chunk_path}")
    except Exception as e:
        print(f"❌ Error guardando chunk {chunkIndex}: {e}")
        raise HTTPException(status_code=500, detail=f"Error guardando chunk {chunkIndex}: {e}")

    if chunkIndex + 1 < totalChunks:
        print("⏳ Esperando más chunks...")
        return {"status": "chunk_received", "chunkIndex": chunkIndex}

    # Ensamblar el video final en /videos
    print("🔧 Ensamblando video final...")
    safe_name = os.path.basename(originalName)
    final_filename = f"{uploadId}_{safe_name}"
    final_video_path = os.path.join(VIDEOS_DIR, final_filename)

    try:
        with open(final_video_path, "wb") as final_file:
            for i in range(totalChunks):
                part_path = os.path.join(UPLOAD_DIR, f"{uploadId}_part{i}")
                if not os.path.exists(part_path):
                    print(f"❌ Falta chunk {i}")
                    raise RuntimeError(f"Falta chunk {i}")
                print(f"🧩 Añadiendo chunk {i} al video final...")
                with open(part_path, "rb") as p:
                    final_file.write(p.read())
                os.remove(part_path)
        print(f"✅ Video ensamblado correctamente: {final_video_path}")
    except Exception as e:
        print(f"❌ Error ensamblando video: {e}")
        raise HTTPException(status_code=500, detail=f"Error ensamblando video: {e}")

    # Extraer frames desde el archivo en /videos
    print("🚀 Iniciando extracción de frames...")
    frames = _extract_frames_ffmpeg(final_video_path, uploadId)
    print(f"✅ Extracción completada ({len(frames)} frames).")

    total_time = time.time() - start_time
    print(f"🏁 Proceso completo en {total_time:.1f}s")

    return {
        "status": "complete",
        "uploadId": uploadId,
        "frames_extracted": len(frames),
        "frames": frames,
        "video": {
            "filename": final_filename,
            "path": f"/videos/{final_filename}"
        }
    }

# ==========================
#  2️⃣ Upload URL
# ==========================


@router.post("/from_url")
async def extract_frames_from_url(video_url: str = Form(...)):
    print("\n🌐 ========================")
    print("🌐 NUEVA PETICIÓN /extract_frames/from_url")
    print("🌐 ========================")
    start = time.time()
    upload_id = str(uuid.uuid4())

    # Guardar en VIDEOS_DIR
    final_filename = f"{upload_id}.mp4"
    final_video_path = os.path.join(VIDEOS_DIR, final_filename)

    print(f"⬇️ Descargando video desde: {video_url}")
    try:
        r = requests.get(video_url, stream=True, timeout=60)
        r.raise_for_status()
        with open(final_video_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        print(f"✅ Video guardado en: {final_video_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo descargar el video: {e}")

    # Extraer frames
    frames = _extract_frames_ffmpeg(final_video_path, upload_id)
    print(f"✅ Extracción finalizada ({len(frames)} frames) en {time.time() - start:.1f}s")

    # Retornar con path
    return {
        "status": "complete",
        "uploadId": upload_id,
        "frames_extracted": len(frames),
        "frames": frames,
        "video": {
            "filename": final_filename,
            "path": f"/videos/{final_filename}"
        }
    }



# ==========================
#  3️⃣ Cleanup de frames y video por uploadId
# ==========================
@router.post("/cleanup")
async def cleanup_files(request: Request):
    print("\n🧹 ========================")
    print("🧹 NUEVA PETICIÓN /extract_frames/cleanup")
    print("🧹 ========================")

    data = await request.json()
    upload_id = data.get("uploadId")
    print(f"🧾 uploadId recibido: {upload_id}")

    if not upload_id:
        print("❌ No se proporcionó uploadId")
        raise HTTPException(status_code=400, detail="uploadId requerido")

    deleted_frames = 0
    deleted_videos = 0

    # 🧩 1️⃣ Eliminar frames asociados
    for file in os.listdir(FRAMES_DIR):
        if file.startswith(upload_id):
            file_path = os.path.join(FRAMES_DIR, file)
            try:
                os.remove(file_path)
                print(f"🗑️ Eliminado frame: {file_path}")
                deleted_frames += 1
            except Exception as e:
                print(f"⚠️ Error eliminando frame {file}: {e}")

    # 🧩 2️⃣ Eliminar videos asociados
    for file in os.listdir(VIDEOS_DIR):
        if file.startswith(upload_id):
            file_path = os.path.join(VIDEOS_DIR, file)
            try:
                os.remove(file_path)
                print(f"🎬🗑️ Eliminado video: {file_path}")
                deleted_videos += 1
            except Exception as e:
                print(f"⚠️ Error eliminando video {file}: {e}")

    print("✅ Cleanup completo:")
    print(f"   🖼️ Frames eliminados: {deleted_frames}")
    print(f"   🎥 Videos eliminados: {deleted_videos}")

    return {
        "status": "ok",
        "deleted": {
            "frames": deleted_frames,
            "videos": deleted_videos
        }
    }
