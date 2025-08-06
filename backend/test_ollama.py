#!/usr/bin/env python3
"""
Test script to diagnose Ollama connection issues
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    OLLAMA_URL, OLLAMA_MODEL, TEMPERATURE, 
    OLLAMA_TIMEOUT, OLLAMA_STREAMING_TIMEOUT,
    test_ollama_connection
)
from llama_index.llms.ollama import Ollama
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_basic_connection():
    """Test basic Ollama connection"""
    print("🔍 Testing basic Ollama connection...")
    print(f"   URL: {OLLAMA_URL}")
    print(f"   Model: {OLLAMA_MODEL}")
    print(f"   Timeout: {OLLAMA_TIMEOUT}s")
    
    try:
        llm = Ollama(
            model=OLLAMA_MODEL,
            temperature=TEMPERATURE,
            base_url=OLLAMA_URL,
            request_timeout=10,  # Short timeout for testing
        )
        
        if test_ollama_connection(llm, max_retries=1, timeout=10):
            print("✅ Basic connection successful")
            return llm
        else:
            print("❌ Basic connection failed")
            return None
    except Exception as e:
        print(f"❌ Basic connection error: {e}")
        return None

def test_streaming_connection(llm):
    """Test streaming functionality"""
    print("\n🔍 Testing streaming connection...")
    
    try:
        # Test streaming with a simple query
        test_query = "Hello, how are you?"
        print(f"   Query: {test_query}")
        
        response = llm.stream_complete(test_query)
        
        tokens = []
        start_time = time.time()
        
        for token in response:
            tokens.append(str(token))
            if len(tokens) > 10:  # Limit for testing
                break
        
        elapsed = time.time() - start_time
        
        if tokens:
            print(f"✅ Streaming successful")
            print(f"   Tokens received: {len(tokens)}")
            print(f"   Time elapsed: {elapsed:.2f}s")
            print(f"   Sample response: {''.join(tokens[:5])}...")
            return True
        else:
            print("❌ No tokens received from streaming")
            return False
            
    except Exception as e:
        print(f"❌ Streaming error: {e}")
        return False

async def test_async_streaming():
    """Test async streaming functionality"""
    print("\n🔍 Testing async streaming...")
    
    try:
        from ai_engine.ai_engine import ask_ai_streaming
        
        test_query = "What is electronics?"
        print(f"   Query: {test_query}")
        
        tokens = []
        start_time = time.time()
        
        async for token in ask_ai_streaming(test_query):
            tokens.append(token)
            if len(tokens) > 20:  # Limit for testing
                break
        
        elapsed = time.time() - start_time
        
        if tokens:
            print(f"✅ Async streaming successful")
            print(f"   Tokens received: {len(tokens)}")
            print(f"   Time elapsed: {elapsed:.2f}s")
            print(f"   Sample response: {''.join(tokens[:10])}...")
            return True
        else:
            print("❌ No tokens received from async streaming")
            return False
            
    except Exception as e:
        print(f"❌ Async streaming error: {e}")
        return False

def check_ollama_service():
    """Check if Ollama service is running"""
    print("🔍 Checking Ollama service status...")
    
    import requests
    try:
        # Try to reach Ollama API
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Ollama service is running")
            print(f"   Available models: {len(models)}")
            
            # Check if our model is available
            model_names = [m.get('name', '') for m in models]
            if OLLAMA_MODEL in model_names:
                print(f"✅ Model '{OLLAMA_MODEL}' is available")
            else:
                print(f"⚠️ Model '{OLLAMA_MODEL}' not found")
                print(f"   Available models: {model_names}")
                print(f"   Run: ollama pull {OLLAMA_MODEL}")
            
            return True
        else:
            print(f"❌ Ollama service returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama service")
        print("   Make sure Ollama is running: ollama serve")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama service: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Ollama Connection Diagnostic Tool")
    print("=" * 50)
    
    # Check service status
    service_ok = check_ollama_service()
    if not service_ok:
        print("\n❌ Ollama service is not available. Please start it first.")
        return
    
    # Test basic connection
    llm = test_basic_connection()
    if not llm:
        print("\n❌ Basic connection failed. Cannot proceed with further tests.")
        return
    
    # Test streaming
    streaming_ok = test_streaming_connection(llm)
    
    # Test async streaming
    print("\n🔍 Testing async streaming (this may take a moment)...")
    async_ok = asyncio.run(test_async_streaming())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Service Status: {'✅' if service_ok else '❌'}")
    print(f"   Basic Connection: {'✅' if llm else '❌'}")
    print(f"   Streaming: {'✅' if streaming_ok else '❌'}")
    print(f"   Async Streaming: {'✅' if async_ok else '❌'}")
    
    if service_ok and llm and streaming_ok and async_ok:
        print("\n🎉 All tests passed! Your Ollama setup is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the errors above for troubleshooting.")

if __name__ == "__main__":
    main()