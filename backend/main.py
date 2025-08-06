from fastapi import FastAPI, Request, HTTPException
import random
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Optional
import uvicorn
import asyncio
import json
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

from ai_engine.ai_engine import ask_ai, ask_ai_streaming

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

class QueryRequest(BaseModel):
    query: str
    context: Optional[str] = None

    @validator('query')
    def query_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v[:1000]  # Limit to 1000 characters

class ChatRequest(BaseModel):
    message: str

    @validator('message')
    def message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v[:1000]  # Limit to 1000 characters

app = FastAPI()

# CORS setup - more permissive for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],  # Allow all headers
)

# No Redis client - using in-memory caching only

# --- ROUTES ---

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
        
        # Test Ollama connection
        ollama_status = "unknown"
        try:
            llm = Ollama(
                model=OLLAMA_MODEL,
                base_url=OLLAMA_URL,
                request_timeout=10  # Short timeout for health check
            )
            if test_ollama_connection(llm, max_retries=1, timeout=5):
                ollama_status = "healthy"
            else:
                ollama_status = "unhealthy"
        except Exception as ollama_error:
            logger.warning(f"Ollama health check failed: {ollama_error}")
            ollama_status = "error"
        
        status = {
            "status": "healthy" if ollama_status == "healthy" else "degraded",
            "services": {
                "redis": "disabled",
                "ollama": ollama_status,
                "ollama_url": OLLAMA_URL,
                "ollama_model": OLLAMA_MODEL
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")

def process_response(response: str) -> str:
    """Clean and format the AI response"""
    if not response or not response.strip():
        return "I couldn't find relevant information to answer your question."
    
    # Clean up the response
    response = response.strip()
    
    # Return the response as-is for better accuracy
    return response

@app.post("/ask")
async def ask(request: QueryRequest):
    """
    Fast non-streaming AI query endpoint
    """
    try:
        logger.info(f"Processing query: {request.query}")
        
        # Process query with optimized settings
        result = ask_ai(request.query)
        processed_result = process_response(result)

        return {
            "response": processed_result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Request handling failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing request")

@app.post("/ask-stream")
async def ask_stream(request: Request):
    """Streaming endpoint with proper SSE implementation"""
    data = await request.json()
    query = data.get("query")
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    async def event_stream():
        try:
            yield "data: {\"choices\":[{\"delta\":{\"role\":\"assistant\"},\"index\":0}]}\n\n"
            
            token_count = 0
            async for token in ask_ai_streaming(query):
                if token:
                    token_count += 1
                    sse_data = {
                        "choices": [{
                            "delta": {"content": token},
                            "index": 0
                        }]
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"
                    # No artificial delay for maximum speed
            
            logger.info(f"Fast streaming completed with {token_count} tokens")
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            error_msg = "Service temporarily unavailable"
            if "timeout" in str(e).lower():
                error_msg = "Request timed out - try a shorter query"
            
            error_data = {
                "choices": [{
                    "delta": {"content": f"[Error] {error_msg}"},
                    "index": 0
                }]
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint with Server-Sent Events (SSE) streaming
    """
    try:
        logger.info(f"Processing chat message: {request.message}")
        
        async def generate_sse():
            try:
                yield "data: {\"choices\":[{\"delta\":{\"role\":\"assistant\"},\"index\":0}]}\n\n"
                
                chunk_count = 0
                async for chunk in ask_ai_streaming(request.message):
                    if chunk:
                        chunk_count += 1
                        sse_data = {
                            "choices": [{
                                "delta": {"content": chunk},
                                "index": 0
                            }]
                        }
                        yield f"data: {json.dumps(sse_data)}\n\n"
                        # No delay for maximum speed
                
                logger.info(f"Chat streaming completed with {chunk_count} chunks")
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Chat streaming error: {str(e)}")
                error_msg = "Service temporarily unavailable"
                if "timeout" in str(e).lower():
                    error_msg = "Request timed out - try a shorter message"
                
                error_data = {
                    "choices": [{
                        "delta": {"content": f"[Error] {error_msg}"},
                        "index": 0
                    }]
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing chat request")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9001, reload=True)
