from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRoute
from routers import replace_word, upload_videos, extract_frames, videos_router
from routers import html_to_png
from routers.repeat_block import router as repeat_block

app = FastAPI(title="Leaf Services API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Montar solo frames estáticos
app.mount("/frames", StaticFiles(directory="frames"), name="frames")

# ✅ 🔥 AGREGADO: servir imágenes generadas por html-to-png
app.mount("/generated_png", StaticFiles(directory="generated_png"), name="generated_png")

# ✅ Registrar routers en orden (extract_frames antes por prioridad)
app.include_router(extract_frames.router)
app.include_router(videos_router.router)  # streaming con Range
app.include_router(replace_word.router)
app.include_router(upload_videos.router)
app.include_router(html_to_png.router)
app.include_router(repeat_block)

@app.get("/")
def root():
    return {"message": "🌿 Leaf Services API running"}

# Debug opcional
print("\n🧭 RUTAS REGISTRADAS EN FASTAPI:")
for route in app.routes:
    if isinstance(route, APIRoute):
        print(f"➡️ {route.path} | métodos: {route.methods} | módulo: {route.endpoint.__module__}")
print("========================================\n")

