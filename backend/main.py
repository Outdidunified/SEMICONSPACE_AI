from fastapi import FastAPI, Request, HTTPException
import random
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Optional
import uvicorn
import asyncio
import redis.asyncio as redis
import json
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

from ai_engine.ai_engine import ask_ai, ask_ai_streaming

# Load environment variables
load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

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

app = FastAPI()

# CORS setup with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Redis client
redis_client: redis.Redis = None

# --- APP LIFECYCLE HOOKS ---

@app.on_event("startup")
async def startup_event():
    global redis_client
    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        await redis_client.ping()
        logger.info("✅ Redis connected successfully.")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {str(e)}")
        redis_client = None  # Fallback to no caching

@app.on_event("shutdown")
async def shutdown_event():
    if redis_client:
        await redis_client.close()
        logger.info("🔌 Redis connection closed.")

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
    """Health check endpoint"""
    try:
        status = {
            "status": "healthy",
            "services": {"redis": "connected" if redis_client and await redis_client.ping() else "disabled"}
        }
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")

def process_response(response: str) -> str:
    """Transform the AI response to be more conversational and extract name greetings"""
    # Keep technical responses as-is
    if any(word in response.lower() for word in ["datasheet", "specification", "technical"]):
        return response
        
    # Detect and extract name greeting (e.g., "Ah, nice to meet [name]!")
    if "Ah, nice to meet" in response:
        start_idx = response.find("Ah, nice to meet") + len("Ah, nice to meet")
        end_idx = response.find("!", start_idx)
        if end_idx != -1:
            return response[start_idx:end_idx + 1].strip()
    
    # Make learned responses more friendly
    if "Q:" in response and "A:" in response:
        answer = response.split("A:")[1].strip()
        if answer.startswith(("Ah,", "Oh,", "Well,")):
            return answer
        return f"Ah, {answer[0].lower() + answer[1:]}"
        
    # Handle AI identity response
    if "I am Semicon AI" in response:
        return "I am Semicon AI, nice to meet you!"
    

    return f" {response}"

@app.post("/ask")
async def ask(request: QueryRequest):
    """
    Process AI query with caching
    
    Args:
        query: Required question string
        context: Optional context for the query
        
    Returns:
        JSON response with answer, cache status, and timestamp
    """
    try:
        logger.info(f"Processing query: {request.query}")
        cache_key = f"query:{hash(request.query + (request.context or ''))}"
        
        # Try cached response first
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.debug("Serving from cache")
                cached_data = json.loads(cached)
                return JSONResponse(content={
                    "response": process_response(cached_data["response"]),
                    "cached": True,
                    "timestamp": datetime.now().isoformat()
                })

        # Process new query with enhanced error handling
        try:
            result = ask_ai(request.query)
            processed_result = process_response(result)
            
            # Learn from successful interaction
            from ai_engine.ai_engine import learn_from_interaction
            try:
                learn_from_interaction(request.query, result)
            except Exception as learn_error:
                logger.error(f"Failed to learn from interaction: {learn_error}")
                # Continue without failing the request

            if redis_client:
                await redis_client.set(cache_key, json.dumps({"response": result}), ex=3600)
                logger.debug("Cached new response")

            return {
                "response": processed_result,
                "cached": False,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as query_error:
            logger.error(f"Query processing failed: {query_error}")
            return JSONResponse(content={
                "response": "I encountered an error processing your request. Please try again.",
                "cached": False,
                "timestamp": datetime.now().isoformat()
            }, status_code=200)

    except Exception as e:
        logger.error(f"Request handling failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing request")

@app.post("/ask-stream")
async def ask_stream(request: Request):
    data = await request.json()
    query = data.get("query")
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    async def event_stream():
        async for token in ask_ai_streaming(query):
            yield token

    return StreamingResponse(event_stream(), media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9001, reload=True)