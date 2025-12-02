from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid, os
from playwright.async_api import async_playwright

router = APIRouter(prefix="/html-to-png", tags=["html_to_png"])

class HTMLPayload(BaseModel):
    html: str

@router.post("/")
async def convert_html_to_png(payload: HTMLPayload):
    output_dir = "generated_png"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}.png"
    output_path = os.path.join(output_dir, filename)

    html = payload.html

    async with async_playwright() as p:
        # 🔥 Usar chromium instalado por apt
        browser = await p.chromium.launch(
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        page = await browser.new_page(
            viewport={"width": 1070, "height": 1239},
            device_scale_factor=2  # MÁS NITIDEZ
        )

        await page.set_content(html)

        # Ajustar viewport al tamaño del contenido real
        width = await page.evaluate("document.documentElement.scrollWidth")
        height = await page.evaluate("document.documentElement.scrollHeight")

        await page.set_viewport_size({"width": width, "height": height})

        # Captura PNG
        await page.screenshot(path=output_path)

        await browser.close()

    return FileResponse(output_path, media_type="image/png", filename=filename)
