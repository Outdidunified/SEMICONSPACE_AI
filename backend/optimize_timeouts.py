#!/usr/bin/env python3
"""
Script to help optimize timeout settings based on your system performance
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import OLLAMA_URL, OLLAMA_MODEL, TEMPERATURE
from llama_index.llms.ollama import Ollama
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)

def benchmark_response_time(llm, query="What is electronics?", iterations=3):
    """Benchmark response time for a given query"""
    times = []
    
    for i in range(iterations):
        print(f"   Test {i+1}/{iterations}...", end=" ")
        try:
            start_time = time.time()
            response = llm.complete(query)
            elapsed = time.time() - start_time
            
            if response and response.text:
                times.append(elapsed)
                print(f"{elapsed:.2f}s")
            else:
                print("Failed (empty response)")
        except Exception as e:
            print(f"Failed ({str(e)[:50]}...)")
    
    return times

def benchmark_streaming_time(llm, query="What is electronics?", iterations=3):
    """Benchmark streaming response time"""
    times = []
    
    for i in range(iterations):
        print(f"   Test {i+1}/{iterations}...", end=" ")
        try:
            start_time = time.time()
            response = llm.stream_complete(query)
            
            token_count = 0
            for token in response:
                token_count += 1
                if token_count > 50:  # Limit for benchmarking
                    break
            
            elapsed = time.time() - start_time
            
            if token_count > 0:
                times.append(elapsed)
                print(f"{elapsed:.2f}s ({token_count} tokens)")
            else:
                print("Failed (no tokens)")
        except Exception as e:
            print(f"Failed ({str(e)[:50]}...)")
    
    return times

def calculate_recommended_timeouts(regular_times, streaming_times):
    """Calculate recommended timeout values based on benchmark results"""
    if not regular_times and not streaming_times:
        return None
    
    # Calculate statistics
    if regular_times:
        avg_regular = sum(regular_times) / len(regular_times)
        max_regular = max(regular_times)
    else:
        avg_regular = max_regular = 30  # Default fallback
    
    if streaming_times:
        avg_streaming = sum(streaming_times) / len(streaming_times)
        max_streaming = max(streaming_times)
    else:
        avg_streaming = max_streaming = 60  # Default fallback
    
    # Calculate recommended timeouts with safety margins
    recommended = {
        'OLLAMA_TIMEOUT': max(60, int(max_regular * 3)),  # 3x max regular time, min 60s
        'OLLAMA_STREAMING_TIMEOUT': max(120, int(max_streaming * 4)),  # 4x max streaming time, min 120s
        'OLLAMA_CONNECTION_TIMEOUT': 30,  # Fixed connection timeout
        'OLLAMA_READ_TIMEOUT': max(90, int(max_streaming * 2))  # 2x max streaming time, min 90s
    }
    
    return recommended, {
        'avg_regular': avg_regular,
        'max_regular': max_regular,
        'avg_streaming': avg_streaming,
        'max_streaming': max_streaming
    }

def update_env_file(recommended_timeouts):
    """Update .env file with recommended timeout values"""
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        print("❌ .env file not found")
        return False
    
    try:
        # Read current .env file
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update timeout values
        updated_lines = []
        timeout_keys = set(recommended_timeouts.keys())
        found_keys = set()
        
        for line in lines:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key = line.split('=')[0].strip()
                if key in timeout_keys:
                    updated_lines.append(f"{key}={recommended_timeouts[key]}\n")
                    found_keys.add(key)
                else:
                    updated_lines.append(line + '\n')
            else:
                updated_lines.append(line + '\n')
        
        # Add missing timeout keys
        missing_keys = timeout_keys - found_keys
        if missing_keys:
            updated_lines.append('\n# Optimized timeout settings\n')
            for key in missing_keys:
                updated_lines.append(f"{key}={recommended_timeouts[key]}\n")
        
        # Write updated .env file
        with open(env_path, 'w') as f:
            f.writelines(updated_lines)
        
        print(f"✅ Updated .env file with optimized timeout settings")
        return True
        
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False

def main():
    """Main optimization function"""
    print("🚀 Ollama Timeout Optimization Tool")
    print("=" * 50)
    
    # Check if Ollama is available
    try:
        llm = Ollama(
            model=OLLAMA_MODEL,
            temperature=TEMPERATURE,
            base_url=OLLAMA_URL,
            request_timeout=30,
        )
        
        # Quick connection test
        print("🔍 Testing connection...")
        test_response = llm.complete("Hello", timeout=10)
        if not test_response or not test_response.text:
            print("❌ Connection test failed")
            return
        print("✅ Connection successful")
        
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("   Make sure Ollama is running: ollama serve")
        return
    
    # Benchmark regular responses
    print("\n🔍 Benchmarking regular responses...")
    regular_times = benchmark_response_time(llm)
    
    # Benchmark streaming responses
    print("\n🔍 Benchmarking streaming responses...")
    streaming_times = benchmark_streaming_time(llm)
    
    # Calculate recommendations
    if not regular_times and not streaming_times:
        print("❌ No successful benchmarks. Cannot provide recommendations.")
        return
    
    result = calculate_recommended_timeouts(regular_times, streaming_times)
    if not result:
        print("❌ Could not calculate recommendations")
        return
    
    recommended, stats = result
    
    # Display results
    print("\n" + "=" * 50)
    print("📊 Benchmark Results:")
    if regular_times:
        print(f"   Regular responses: avg={stats['avg_regular']:.2f}s, max={stats['max_regular']:.2f}s")
    if streaming_times:
        print(f"   Streaming responses: avg={stats['avg_streaming']:.2f}s, max={stats['max_streaming']:.2f}s")
    
    print("\n🎯 Recommended Timeout Settings:")
    for key, value in recommended.items():
        print(f"   {key}={value}")
    
    # Ask user if they want to update .env file
    print("\n" + "=" * 50)
    response = input("Would you like to update your .env file with these settings? (y/N): ")
    
    if response.lower() in ['y', 'yes']:
        if update_env_file(recommended):
            print("\n🎉 Optimization complete! Restart your application to use the new settings.")
        else:
            print("\n⚠️ Could not update .env file. Please update manually.")
    else:
        print("\n💡 You can manually add these settings to your .env file.")

if __name__ == "__main__":
    main()