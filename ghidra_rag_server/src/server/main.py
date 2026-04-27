from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database.connection import DatabaseConnection
from .routers import api_query, doc_search, version

db = DatabaseConnection()

app = FastAPI(
    title="Ghidra RAG Server",
    description="A normalized RAG system for Ghidra API documentation",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_query.router)
app.include_router(doc_search.router)
app.include_router(version.router)


@app.get("/")
def root():
    return {
        "service": "Ghidra RAG Server",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
