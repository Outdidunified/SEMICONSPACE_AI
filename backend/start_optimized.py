#!/usr/bin/env python3
"""
Optimized startup script that warms up the model and starts the server
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

def run_warmup():
    """Run the model warmup"""
    print("🔥 Starting model warmup...")
    try:
        from warmup_model import warmup_model
        success = warmup_model()
        if success:
            print("✅ Model warmup completed successfully!")
            return True
        else:
            print("⚠️ Model warmup had issues, but continuing...")
            return False
    except Exception as e:
        print(f"❌ Warmup failed: {e}")
        return False

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting optimized server...")
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=9001,
            reload=False,  # Disable reload for better performance
            access_log=False,  # Disable access logs for better performance
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")

def main():
    """Main startup function"""
    print("🚀 Optimized AI Streaming Server")
    print("=" * 50)
    
    # Check if Ollama is running
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            print("❌ Ollama service is not responding")
            print("   Please start Ollama: ollama serve")
            return
    except Exception:
        print("❌ Cannot connect to Ollama service")
        print("   Please start Ollama: ollama serve")
        return
    
    print("✅ Ollama service is running")
    
    # Run warmup
    warmup_success = run_warmup()
    
    if warmup_success:
        print("\n🎉 System is optimized and ready!")
    else:
        print("\n⚠️ Starting server without full optimization...")
    
    print("\n📡 Server will be available at:")
    print("   - Health check: http://localhost:9001/health")
    print("   - Streaming API: http://localhost:9001/api/chat")
    print("   - Standard API: http://localhost:9001/ask")
    print("\n🔥 Optimizations active:")
    print("   - Extended timeouts (300-600s)")
    print("   - Connection pooling")
    print("   - Model keep-alive (10m)")
    print("   - Direct LLM streaming")
    print("   - Zero artificial delays")
    
    print("\n" + "=" * 50)
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()