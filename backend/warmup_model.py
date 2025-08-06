#!/usr/bin/env python3
"""
Model warmup script to ensure fast first responses
"""

import sys
import time
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import configure_settings, OLLAMA_MODEL, OLLAMA_URL
from llama_index.core import Settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def warmup_model():
    """Warm up the model for faster responses"""
    print("🔥 Starting model warmup...")
    
    try:
        # Configure settings
        if not configure_settings():
            print("❌ Failed to configure settings")
            return False
        
        llm = Settings.llm
        if not llm:
            print("❌ LLM not available")
            return False
        
        # Perform multiple warmup queries
        warmup_queries = [
            "Hi",
            "Hello, how are you?",
            "What is electronics?",
            "Tell me about resistors",
            "Explain capacitors briefly"
        ]
        
        print(f"🔥 Warming up with {len(warmup_queries)} queries...")
        
        total_time = 0
        successful_queries = 0
        
        for i, query in enumerate(warmup_queries, 1):
            print(f"   Query {i}/{len(warmup_queries)}: {query[:30]}...", end=" ")
            
            try:
                start_time = time.time()
                response = llm.complete(query, timeout=60)
                elapsed = time.time() - start_time
                
                if response and response.text:
                    total_time += elapsed
                    successful_queries += 1
                    print(f"✅ {elapsed:.2f}s")
                else:
                    print("❌ Empty response")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}...")
        
        if successful_queries > 0:
            avg_time = total_time / successful_queries
            print(f"\n🎉 Warmup completed!")
            print(f"   Successful queries: {successful_queries}/{len(warmup_queries)}")
            print(f"   Average response time: {avg_time:.2f}s")
            print(f"   Model should now respond faster!")
            return True
        else:
            print("\n❌ No successful warmup queries")
            return False
            
    except Exception as e:
        print(f"❌ Warmup failed: {e}")
        return False

def main():
    """Main warmup function"""
    print("🚀 Model Warmup Tool")
    print("=" * 40)
    print(f"Model: {OLLAMA_MODEL}")
    print(f"URL: {OLLAMA_URL}")
    print("=" * 40)
    
    success = warmup_model()
    
    if success:
        print("\n✅ Model is warmed up and ready for fast responses!")
    else:
        print("\n⚠️ Warmup had issues. First responses may be slower.")

if __name__ == "__main__":
    main()