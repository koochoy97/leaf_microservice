FROM python:3.11-slim

# Instalar FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Dependencias Playwright/Chromium
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

# Instalar solo playwright (python)
RUN pip install playwright

# Instalar solo el navegador Chromium (SIN deps)
RUN playwright install chromium

# Directorio de trabajo
WORKDIR /app

# Copiar código
COPY . /app

# Instalar requirements
RUN pip install --no-cache-dir -r requirements.txt

# Exponer puerto
EXPOSE 8000

# Comando de arranque
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
