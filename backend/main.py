from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, validator
from typing import Optional
import uvicorn
import asyncio
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from ai_engine.ai_engine import ask_ai_streaming, learn_from_interaction
import os

# Load environment variables
load_dotenv()
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:9000,http://localhost:3000,http://127.0.0.1:9000,http://127.0.0.1:3000,*").split(",")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None

    @validator('message')
    def message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v[:1000]  # Limit to 1000 characters

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Electronics AI API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with AI service status"""
    try:
        from config import OLLAMA_URL, OLLAMA_MODEL, test_ollama_connection
        from llama_index.llms.ollama import Ollama
        ollama_status = "unknown"
        try:
            llm = Ollama(model=OLLAMA_MODEL, base_url=OLLAMA_URL, request_timeout=10)
            if test_ollama_connection(llm, max_retries=1, timeout=5):
                ollama_status = "healthy"
            else:
                ollama_status = "unhealthy"
        except Exception as ollama_error:
            logger.warning(f"Ollama health check failed: {ollama_error}")
            ollama_status = "error"
        return {
            "status": "healthy" if ollama_status == "healthy" else "degraded",
            "services": {
                "redis": "disabled",
                "ollama": ollama_status,
                "ollama_url": OLLAMA_URL,
                "ollama_model": OLLAMA_MODEL
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Streaming chat endpoint with document retrieval and learning"""
    try:
        logger.info(f"Processing chat message: {request.message}")
        prompt = f"In the context of semiconductors: {request.message}"
        if request.context:
            prompt = f"{request.context}\n{prompt}"

        async def generate_sse():
            try:
                yield 'data: {"choices":[{"delta":{"role":"assistant"},"index":0}]}\n\n'
                chunk_count = 0
                response_text = ""
                async for chunk in ask_ai_streaming(prompt):
                    if chunk:
                        chunk_count += 1
                        response_text += chunk
                        sse_data = {
                            "choices": [{
                                "delta": {"content": chunk},
                                "index": 0
                            }]
                        }
                        yield f'data: {json.dumps(sse_data)}\n\n'
                        await asyncio.sleep(0.001)
                        if chunk_count > 150:
                            break
                logger.info(f"Streaming completed with {chunk_count} chunks")
                
                # Learn from interaction
                try:
                    learn_from_interaction(request.message, response_text)
                    logger.info("Successfully learned from interaction")
                except Exception as learn_error:
                    logger.warning(f"Failed to learn from interaction: {learn_error}")
                
                yield 'data: [DONE]\n\n'
            except Exception as e:
                logger.error(f"Streaming error: {str(e)}")
                error_msg = "Service temporarily unavailable"
                if "timeout" in str(e).lower():
                    error_msg = "Request timed out - try a shorter message"
                yield f'data: {json.dumps({"choices": [{"delta": {"content": "[Error] " + error_msg}, "index": 0}]})}\n\n'
                yield 'data: [DONE]\n\n'

        return EventSourceResponse(
            generate_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing chat request")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9001, reload=True)