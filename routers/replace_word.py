from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from io import BytesIO
import tempfile
import json
import unicodedata
import re
import os
from docxtpl import DocxTemplate

router = APIRouter(prefix="/replace-word", tags=["Word Processing"])

@router.post("/")
async def replace_word(
    file: UploadFile = File(...),
    replacements: str = Form(...)
):
    """
    Reemplaza placeholders en un DOCX usando docxtpl, preservando el formato.
    Ejemplo replacements:
    {"{{nombre}}": "Jaime", "{{pais}}": "México"}
    """

    # 1️⃣ Validar tipo de archivo
    if not file.filename.endswith(".docx"):
        return JSONResponse(
            status_code=400,
            content={"error": "El archivo debe ser un .docx válido"}
        )

    # 2️⃣ Leer y parsear replacements
    try:
        replacements_dict = json.loads(replacements)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"error": "El campo 'replacements' debe ser un JSON válido"}
        )

    # Limpieza: convertir {{pais}} → pais para docxtpl
    context = {}
    for k, v in replacements_dict.items():
        clean = re.sub(r"^\{\{\s*|\s*\}\}$", "", k).strip()
        context[clean] = v

    # 3️⃣ Guardar archivo temporal
    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 4️⃣ Cargar plantilla y renderizar con docxtpl
        doc = DocxTemplate(tmp_path)
        doc.render(context)

        # 5️⃣ Guardar el resultado en memoria
        output = BytesIO()
        doc.save(output)
        output.seek(0)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error procesando documento: {str(e)}"}
        )
    finally:
        os.remove(tmp_path)

    # 6️⃣ Nombre limpio
    safe_filename = unicodedata.normalize("NFKD", f"modified_{file.filename}")
    safe_filename = safe_filename.encode("ascii", "ignore").decode("ascii")
    safe_filename = re.sub(r"[^A-Za-z0-9_.-]", "_", safe_filename)

    # 7️⃣ Devolver DOCX como descarga
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
    )
