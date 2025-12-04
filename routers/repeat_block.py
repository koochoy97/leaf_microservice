from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from io import BytesIO
from docx import Document
from copy import deepcopy
import tempfile
import os

# ============================================================
#  ROUTER
# ============================================================
router = APIRouter(prefix="/repeat-fase", tags=["Word Repeat"])


# ============================================================
#  UTILIDADES XML
# ============================================================
def xml_replace(element, old, new):
    """
    Reemplaza texto dentro de nodos <w:t> del XML sin alterar runs.
    """
    for node in element.iter():
        if node.tag.endswith("}t") and isinstance(node.text, str):
            if old in node.text:
                node.text = node.text.replace(old, new)


def xml_get_text(element):
    """
    Retorna el texto concatenado de los nodos <w:t>.
    """
    out = []
    for node in element.iter():
        if node.tag.endswith("}t") and isinstance(node.text, str):
            out.append(node.text)
    return "".join(out)


# ============================================================
#  ENDPOINT PRINCIPAL
# ============================================================
@router.post("/")
async def repeat_fase(file: UploadFile = File(...), cantidad: int = Form(...)):
    """
    Duplica bloques contenidos entre [[INI_BLOQUE]] y [[FIN_BLOQUE]].
    Reemplaza 'Fase xx' por 'Fase 1', 'Fase 2', ..., hasta la cantidad solicitada.
    Elimina los marcadores y mantiene intactos los placeholders {{...}}.
    """

    # Guardar archivo temporal
    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        doc = Document(tmp_path)
        body = doc._element.body

        ini_positions = []
        fin_positions = []

        # ============================================================
        #  DETECTAR MARCADORES (AUNQUE WORD LOS PARTA EN RUNS)
        # ============================================================
        for i, el in enumerate(body):
            text = xml_get_text(el)
            if "[[INI_BLOQUE]]" in text:
                ini_positions.append(i)
            if "[[FIN_BLOQUE]]" in text:
                fin_positions.append(i)

        # Validación estricta
        if len(ini_positions) != len(fin_positions):
            return {
                "error": f"Marcadores desbalanceados INI={len(ini_positions)}, FIN={len(fin_positions)}"
            }

        # ============================================================
        #  PROCESAR CADA BLOQUE EN ORDEN REVERSO
        # ============================================================
        for idx in reversed(range(len(ini_positions))):

            ini = ini_positions[idx]
            fin = fin_positions[idx]

            # Extraer bloque original
            original_block = [deepcopy(el) for el in body[ini + 1 : fin]]

            # ============================================================
            #  ELIMINAR EL BLOQUE COMPLETO (INI + CONTENIDO + FIN)
            # ============================================================
            for _ in range(fin - ini + 1):
                body.remove(body[ini])

            # Punto donde insertaremos los nuevos bloques
            insert_pos = ini

            # ============================================================
            #  INSERTAR FASES 1 .. N
            # ============================================================
            for fase in range(1, cantidad + 1):
                for el in original_block:
                    clone = deepcopy(el)

                    # Reemplazar frase dentro del XML
                    xml_replace(clone, "Fase xx", f"Fase {fase}")

                    # Insertar el clon
                    body.insert(insert_pos, clone)
                    insert_pos += 1

        # ============================================================
        #  EXPORTAR RESULTADO
        # ============================================================
        output = BytesIO()
        doc.save(output)
        output.seek(0)

    finally:
        os.remove(tmp_path)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": "attachment; filename=repeated.docx"
        }
    )
