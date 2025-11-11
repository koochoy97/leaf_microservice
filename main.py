from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import replace_word, upload_videos, extract_frames
from routers import videos_stream

app = FastAPI(title="Leaf Services API")

# ✅ Habilitar CORS (incluye tu front local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*"  # opcional: para permitir cualquier origen durante pruebas
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Montar carpetas estáticas (para servir los recursos)
app.mount("/frames", StaticFiles(directory="frames"), name="frames")
app.include_router(videos_stream.router)


# ✅ Incluir routers
app.include_router(replace_word.router)
app.include_router(upload_videos.router)
app.include_router(extract_frames.router)

# ✅ Endpoint raíz (útil para probar que el servidor corre)
@app.get("/")
def root():
    return {
        "message": "🌿 Leaf Services API running",
        "routes": [
            "/replace_word",
            "/upload_videos",
            "/extract_frames",
            "/frames",
            "/videos"
        ]
    }

