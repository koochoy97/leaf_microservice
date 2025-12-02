FROM python:3.11-slim

# ----------------------------------------
# 🔥 Instalar FFmpeg (tu parte original)
# ----------------------------------------
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# ----------------------------------------
# 🔥 Dependencias necesarias para Chromium + Playwright
# ----------------------------------------
RUN apt-get update && apt-get install -y \
    chromium \
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
# 🐍 Instalar Playwright (solo API, sin navegadores)
# ----------------------------------------
RUN pip install playwright

# ----------------------------------------
# 📁 Directorio de trabajo
# ----------------------------------------
WORKDIR /app

# Copiar código
COPY . /app

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto
EXPOSE 8000

# Arrancar FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
