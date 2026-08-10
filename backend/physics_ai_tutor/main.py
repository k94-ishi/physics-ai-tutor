from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from physics_ai_tutor.api.router import router
from physics_ai_tutor.core.exceptions import EmbeddingGenerationError

app = FastAPI(title="Physics AI Tutor", version="0.1.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.exception_handler(EmbeddingGenerationError)
async def embedding_generation_error_handler(
    request: Request, exc: EmbeddingGenerationError
):
    return JSONResponse(
        status_code=503,
        content={"detail": "Embedding generation failed. Please try again later."},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"detail": "Failed to save data."},
    )
