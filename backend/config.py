from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
import os
from dotenv import load_dotenv
 
load_dotenv()
 
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4_K_M")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.3))
 
def configure_settings():
    """Configure global settings for embeddings and LLM with streaming support"""
    try:
        # Initialize embedding model
        embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        Settings.embed_model = embed_model
 
        # Initialize streaming-compatible LLM
        llm = Ollama(
            model=OLLAMA_MODEL,
            temperature=TEMPERATURE,
            base_url=OLLAMA_URL,
            request_timeout=120.0,  # Increased timeout for streaming
        )
 
        # 🔍 Perform a small test to confirm model validity
        try:
            result = llm.complete("Hello, are you working?")
            if not result:
                raise ValueError("Empty response from LLM.")
        except Exception as llm_error:
            raise ValueError(f"LLM object for {OLLAMA_MODEL} at {OLLAMA_URL} is not valid.\nError: {llm_error}")
 
        Settings.llm = llm
        Settings.callback_manager = CallbackManager([LlamaDebugHandler()])
 
        print(f"✅ Settings configured with streaming-enabled Ollama LLM ({OLLAMA_MODEL}) at {OLLAMA_URL} and Hugging Face embeddings.")
    except Exception as e:
        print(f"❌ Error configuring settings: {str(e)}")
        raise
