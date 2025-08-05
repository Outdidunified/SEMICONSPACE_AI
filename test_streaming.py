#!/usr/bin/env python3
"""
Test script to verify the streaming functionality works correctly
"""

import requests
import json
import time

def test_chat_endpoint():
    """Test the chat endpoint with streaming"""
    print("🔍 Testing chat endpoint streaming...")
    
    url = "http://localhost:9001/api/chat"
    payload = {"message": "What is a semiconductor?"}
    
    try:
        response = requests.post(url, json=payload, stream=True)
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Streaming response received:")
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data = decoded_line[6:]
                        if data != '[DONE]':
                            try:
                                parsed = json.loads(data)
                                content = parsed.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                if content:
                                    print(content, end='', flush=True)
                            except json.JSONDecodeError:
                                pass
            print("\n✅ Stream completed successfully!")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")

def test_health_check():
    """Test health endpoint"""
    print("\n🔍 Testing health endpoint...")
    try:
        response = requests.get("http://localhost:9001/health")
        print(f"✅ Health check: {response.status_code}")
        print(f"✅ Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Testing Electronics AI Streaming API")
    print("=" * 50)
    
    test_health_check()
    test_chat_endpoint()
    
    print("\n✅ All tests completed!")
