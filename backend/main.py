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
    """Health check endpoint"""
    try:
        status = {
            "status": "healthy",
            "services": {"redis": "disabled"}
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
    Process AI query with caching or handle in-chat teaching
    """
    try:
        logger.info(f"Processing query: {request.query}")
        from ai_engine.ai_engine import learn_from_interaction

        # TEACHING MODE: feed corrections via chat
        if request.query.lower().startswith("teach:"):
            try:
                content = request.query[6:].strip()
                if ">>" not in content:
                    raise ValueError("Missing '>>' delimiter.")
                question, answer = content.split(">>", 1)
                learn_from_interaction(question.strip(), answer.strip())
                return {
                    "response": f"✅ Learned: '{question.strip()}'",
                    "cached": False,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as teach_error:
                logger.error(f"Teach mode failed: {teach_error}")
                raise HTTPException(status_code=400, detail="Invalid teach format. Use: teach: question >> answer")

        # Process new query (no Redis caching)
        result = ask_ai(request.query)
        processed_result = process_response(result)

        # Learn from interaction (non-blocking)
        try:
            learn_from_interaction(request.query, result)
        except Exception as learn_error:
            logger.warning(f"Learning failed (non-critical): {learn_error}")

        return {
            "response": processed_result,
            "cached": False,
            "timestamp": datetime.now().isoformat()
        }

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
