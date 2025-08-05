#!/usr/bin/env python3
"""
Streaming Fix Implementation for THZ Application
This provides the corrected streaming endpoints with proper SSE implementation
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
from typing import AsyncGenerator

app = FastAPI()

@app.post("/api/stream-chat")
async def stream_chat(request: Request):
    """
    Proper SSE streaming endpoint for chat functionality
    """
    data = await request.json()
    message = data.get("message", "")
    
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    async def generate_sse_stream() -> AsyncGenerator[str, None]:
        """Generate Server-Sent Events for streaming response"""
        try:
            # Send initial response start
            yield "data: {\"choices\":[{\"delta\":{\"role\":\"assistant\"},\"index\":0}]}\n\n"
            
            # Simulate streaming response (replace with actual AI streaming)
            response_text = "This is a streaming response from the AI assistant..."
            
            # Stream tokens character by character
            for char in response_text:
                if char:
                    sse_data = {
                        "choices": [{
                            "delta": {"content": char},
                            "index": 0
                        }]
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"
                    await asyncio.sleep(0.02)  # Small delay for smooth streaming
            
            # Send completion
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.post("/api/stream-query")
async def stream_query(request: Request):
    """
    Streaming query endpoint with proper SSE
    """
    data = await request.json()
    query = data.get("query", "")
    
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    async def generate_sse_stream() -> AsyncGenerator[str, None]:
        """Generate Server-Sent Events for streaming response"""
        try:
            # Send initial response
            yield "data: {\"choices\":[{\"delta\":{\"role\":\"assistant\"},\"index\":0}]}\n\n"
            
            # Stream response tokens
            response = "This is a streaming response for your query..."
            
            for char in response:
                sse_data = {
                    "choices": [{
                        "delta": {"content": char},
                        "index": 0
                    }]
                }
                yield f"data: {json.dumps(sse_data)}\n\n"
                await asyncio.sleep(0.01)
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)
