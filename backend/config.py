from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
import os
import time
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4_K_M")
TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", os.getenv("TEMPERATURE", 0.1)))
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", 300.0))
OLLAMA_STREAMING_TIMEOUT = float(os.getenv("OLLAMA_STREAMING_TIMEOUT", 600.0))
OLLAMA_CONNECTION_TIMEOUT = float(os.getenv("OLLAMA_CONNECTION_TIMEOUT", 60.0))
OLLAMA_READ_TIMEOUT = float(os.getenv("OLLAMA_READ_TIMEOUT", 300.0))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", 512))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", 0.9))
SKIP_OLLAMA_VALIDATION = os.getenv("SKIP_OLLAMA_VALIDATION", "false").lower() == "true"

def test_ollama_connection(llm, max_retries=3, timeout=10):
    """Test Ollama connection with retry logic"""
    for attempt in range(max_retries):
        try:
            print(f"🔍 Testing Ollama connection (attempt {attempt + 1}/{max_retries})...")
            result = llm.complete("Hello", timeout=timeout)
            if result and result.text:
                print("✅ Ollama connection successful")
                return True
            else:
                print("⚠️ Empty response from Ollama")
        except Exception as e:
            print(f"⚠️ Ollama connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    return False

def configure_settings():
    """Configure global settings for embeddings and LLM with streaming support"""
    try:
        # Initialize embedding model
        embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        Settings.embed_model = embed_model

        # Initialize streaming-compatible LLM
        import httpx
        http_client = httpx.Client(
            timeout=httpx.Timeout(
                connect=OLLAMA_CONNECTION_TIMEOUT,
                read=OLLAMA_READ_TIMEOUT,
                write=30.0,
                pool=OLLAMA_STREAMING_TIMEOUT
            ),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=300
            )
        )
        
        llm = Ollama(
            model=OLLAMA_MODEL,
            temperature=TEMPERATURE,
            base_url=OLLAMA_URL,
            request_timeout=OLLAMA_STREAMING_TIMEOUT,
            additional_kwargs={
                "keep_alive": OLLAMA_KEEP_ALIVE,
                "num_predict": OLLAMA_NUM_PREDICT,
                "top_p": OLLAMA_TOP_P,
                "stream": True,
                "options": {
                    "temperature": TEMPERATURE,
                    "top_p": OLLAMA_TOP_P,
                    "num_predict": OLLAMA_NUM_PREDICT,
                    "stop": ["<|eot_id|>", "<|end_of_text|>"]
                }
            },
            http_client=http_client
        )

        # Test Ollama connection
        if not SKIP_OLLAMA_VALIDATION:
            if not test_ollama_connection(llm):
                print(f"⚠️ Warning: Ollama at {OLLAMA_URL} is not responding. AI features will be unavailable.")
                print("💡 To skip this validation, set SKIP_OLLAMA_VALIDATION=true in your .env file")
                print("🚀 Ensure Ollama is running with: ollama serve")
                print("📦 Ensure model is available: ollama pull {}".format(OLLAMA_MODEL))
        else:
            print("⚠️ Skipping Ollama validation as requested")

        Settings.llm = llm
        Settings.callback_manager = CallbackManager([LlamaDebugHandler()])

        # Warm up model
        try:
            print("🔥 Warming up model for faster responses...")
            warmup_response = llm.complete("Hi", timeout=30)
            if warmup_response:
                print("✅ Model warmed up successfully")
        except Exception as warmup_error:
            print(f"⚠️ Model warmup failed (continuing anyway): {warmup_error}")

        print(f"✅ Settings configured with Ollama LLM ({OLLAMA_MODEL}) at {OLLAMA_URL}")
        return True
        
    except Exception as e:
        print(f"❌ Error configuring settings: {str(e)}")
        return False