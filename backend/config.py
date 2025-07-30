from langchain_ollama import OllamaLLM
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
import os
from dotenv import load_dotenv
 
load_dotenv()
 
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4_K_M")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.5))
 
def configure_settings():
    """Configure global settings for embeddings and LLM"""
    try:
        # Initialize embedding model
        embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        Settings.embed_model = embed_model
 
        # Initialize and validate LLM
        llm = OllamaLLM(
            model=OLLAMA_MODEL,
            temperature=TEMPERATURE,
            base_url=OLLAMA_URL,
        )
 
        # 🔍 Perform a small test to confirm model validity
        try:
            result = llm.invoke("Hello, are you working?")
            if not result:
                raise ValueError("Empty response from LLM.")
        except Exception as llm_error:
            raise ValueError(f"LLM object for {OLLAMA_MODEL} at {OLLAMA_URL} is not valid.\nError: {llm_error}")
 
        Settings.llm = llm
        Settings.callback_manager = CallbackManager([LlamaDebugHandler()])
 
        print(f"✅ Settings configured with Ollama LLM ({OLLAMA_MODEL}) at {OLLAMA_URL} and Hugging Face embeddings.")
    except Exception as e:
        print(f"❌ Error configuring settings: {str(e)}")
        raise