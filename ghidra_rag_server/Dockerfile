FROM docker.m.daocloud.io/python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV PYTHONPATH=/app/src
ENV GHIDRA_RAG_DATA_DIR=/app/data
ENV GHIDRA_RAG_DB_PATH=/app/data/ghidra_rag.db
ENV GHIDRA_RAG_VEC_DB_PATH=/app/data/ghidra_vec.db

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
