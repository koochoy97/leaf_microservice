from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uuid, os
from playwright.async_api import async_playwright

router = APIRouter(prefix="/html-to-png", tags=["html_to_png"])

# 🔥 Montamos la carpeta aquí mismo SIN tocar main.py
if not os.path.exists("generated_png"):
    os.makedirs("generated_png")

router.mount("/generated_png", StaticFiles(directory="generated_png"), name="generated_png")


class HTMLPayload(BaseModel):
    html: str


@router.post("/")
async def convert_html_to_png(payload: HTMLPayload, request: Request):
    output_dir = "generated_png"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}.png"
    output_path = os.path.join(output_dir, filename)

    html = payload.html

    async with async_playwright() as p:
        # Usar chromium instalado por apt
        browser = await p.chromium.launch(
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        page = await browser.new_page(
            viewport={"width": 1070, "height": 1239},
            device_scale_factor=2
        )

        await page.set_content(html)

        width = await page.evaluate("document.documentElement.scrollWidth")
        height = await page.evaluate("document.documentElement.scrollHeight")
        await page.set_viewport_size({"width": width, "height": height})

        await page.screenshot(path=output_path)

        await browser.close()

    # 👇 Construimos el link accesible desde Notion
    base = str(request.base_url).rstrip("/")
    download_url = f"{base}/html-to-png/generated_png/{filename}"

    return {"url": download_url}

