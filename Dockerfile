FROM python:3.11-slim

# ----------------------------------------
# 🔥 Instalar FFmpeg (tu parte original)
# ----------------------------------------
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# ----------------------------------------
# 🔥 Instalar dependencias del sistema para Playwright + Chromium
# ----------------------------------------
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libpangocairo-1.0-0 \
    fonts-liberation \
    libpango-1.0-0 \
    libgtk-3-0 \
    libxshmfence1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ----------------------------------------
# 🔥 Instalar Playwright (solo Python API)
# ----------------------------------------
RUN pip install playwright

# ----------------------------------------
# 🔥 Instalar Chromium dentro del contenedor
# ----------------------------------------
RUN playwright install --with-deps chromium

# ----------------------------------------
# Directorio de trabajo (tu parte original)
# ----------------------------------------
WORKDIR /app

# Copiar código (tu parte original)
COPY . /app

# Instalar dependencias Python (tu parte original)
RUN pip install --no-cache-dir -r requirements.txt

# Exponer puerto (tu parte original)
EXPOSE 8000

# Comando de arranque (tu parte original)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
