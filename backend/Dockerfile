FROM python:3.12-slim

# Installa dipendenze sistema per WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    libcairo2 \
    libgobject-2.0-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Cartella di lavoro
WORKDIR /app

# Installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice
COPY . .

# Avvia il server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
