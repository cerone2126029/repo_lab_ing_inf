# Immagine Python ufficiale
FROM python:3.10-slim

# Directory di lavoro per coerenza dei path relativi
WORKDIR /progetto

# Copiamo i requisiti e li installiamo
COPY frontend/requirements.txt ./frontend/
RUN pip install --no-cache-dir -r frontend/requirements.txt

# Copiamo tutto il codice del frontend (inclusa la cartella templates)
COPY frontend/ ./frontend/

# Copiamo i file condivisi (servono per popolare il menù a tendina!)
COPY domains.json .
COPY gs_data/ ./gs_data/

# Esponiamo la porta esatta richiesta dalla slide
EXPOSE 8004

# Comando per avviare il frontend
CMD ["python", "-m", "uvicorn", "frontend.src.frontend:app", "--host", "0.0.0.0", "--port", "8004"]