# Immagine Python ufficiale
FROM python:3.10-slim

# Directory di lavoro chiamata come la root del progetto
WORKDIR /progetto

# Copiamo prima solo il file dei requisiti (per ottimizzare la cache di Docker)
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Installiamo i browser virtuali necessari per Crawl4AI
RUN playwright install chromium
RUN playwright install-deps

# Ora copiamo il codice del backend
COPY backend/ ./backend/

# Copiamo i file condivisi dalla root (domains e gold standard)
COPY domains.json .
COPY gs_data/ ./gs_data/

# Esponiamo la porta esatta richiesta dalla slide
EXPOSE 8003

# Comando per avviare il server (eseguito dalla root /progetto)
CMD ["python", "-m", "uvicorn", "backend.src.server:app", "--host", "0.0.0.0", "--port", "8003"]
