# Imagem do dashboard (FastAPI) usada no Cloudflare Containers e em qualquer host com Docker.
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "fastapi>=0.115,<1" "uvicorn>=0.30,<1" "numpy>=1.24" "pyproj>=3.6,<4" "requests>=2.31"
COPY backend ./backend
COPY frontend ./frontend
COPY dados/processados ./dados/processados
COPY dados/originais/ana_metadados_coleta.csv ./dados/originais/
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
