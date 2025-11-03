from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from io import BytesIO
from docx import Document
import json
import unicodedata
import re

app = FastAPI(title="Leaf Services API")

@app.post("/replace-word/")
async def replace_word(
    file: UploadFile = File(...),
    replacements: str = Form(...)
):
    """
    Recibe un archivo Word (.docx) y reemplaza placeholders con valores.
    Ejemplo replacements:
    {"{{nombre}}": "Jaime", "{{pais}}": "México"}
    """

    # 1️⃣ Validar tipo de archivo
    if not file.filename.endswith(".docx"):
        return JSONResponse(
            status_code=400,
            content={"error": "El archivo debe ser un .docx válido"}
        )

    # 2️⃣ Convertir el texto del form en JSON (diccionario)
    try:
        replacements_dict = json.loads(replacements)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"error": "El campo 'replacements' debe ser un JSON válido"}
        )

    # 3️⃣ Leer contenido binario
    content = await file.read()

    # 4️⃣ Cargar documento Word desde memoria
    doc = Document(BytesIO(content))

    # --- 🔁 Reemplazar texto en párrafos ---
    for p in doc.paragraphs:
        for key, value in replacements_dict.items():
            if key in p.text:
                for run in p.runs:
                    run.text = run.text.replace(key, value)

    # --- 🔁 Reemplazar texto dentro de tablas ---
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for key, value in replacements_dict.items():
                    if key in cell.text:
                        cell.text = cell.text.replace(key, value)

    # 5️⃣ Guardar documento modificado en memoria
    output = BytesIO()
    doc.save(output)
    output.seek(0)

    # 6️⃣ Sanitizar nombre del archivo para evitar errores de codificación
    safe_filename = unicodedata.normalize("NFKD", f"modified_{file.filename}")
    safe_filename = safe_filename.encode("ascii", "ignore").decode("ascii")
    safe_filename = re.sub(r'[^A-Za-z0-9_.-]', '_', safe_filename)

    # 👀 Mostrar en consola información del proceso
    print("\n📄 Archivo procesado correctamente:")
    print(f"Reemplazos aplicados: {replacements_dict}")
    print(f"Archivo devuelto: {safe_filename}")

    # 7️⃣ Devolver archivo como descarga
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename={safe_filename}"
        }
    )
