from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from llama_index.llms.ollama import Ollama
import os
from config import OLLAMA_URL, OLLAMA_MODEL, TEMPERATURE

router = APIRouter()

@router.get("/health")
async def health_check():
    """Check the health of the application and Ollama connection"""
    try:
        # Test Ollama connection
        llm = Ollama(
            model=OLLAMA_MODEL,
            temperature=TEMPERATURE,
            base_url=OLLAMA_URL,
            request_timeout=10.0,
        )
        
        # Quick test
        result = llm.complete("ping", timeout=5)
        
        return {
            "status": "healthy",
            "ollama": {
                "status": "connected",
                "url": OLLAMA_URL,
                "model": OLLAMA_MODEL
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "ollama": {
                    "status": "disconnected",
                    "url": OLLAMA_URL,
                    "model": OLLAMA_MODEL,
                    "error": str(e)
                },
                "message": "Ollama service is not available. AI features will be limited."
            }
        )

@router.get("/health/ollama")
async def ollama_health():
    """Specifically check Ollama health"""
    try:
        llm = Ollama(
            model=OLLAMA_MODEL,
            temperature=TEMPERATURE,
            base_url=OLLAMA_URL,
            request_timeout=5.0,
        )
        
        result = llm.complete("test", timeout=3)
        
        return {
            "status": "ok",
            "model": OLLAMA_MODEL,
            "response": result.text[:50] + "..." if len(result.text) > 50 else result.text
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "model": OLLAMA_MODEL,
                "url": OLLAMA_URL,
                "error": str(e),
                "suggestion": "Make sure Ollama is running with 'ollama serve' and model is pulled"
            }
        )
