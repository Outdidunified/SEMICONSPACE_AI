import os
import uuid
import logging
import json
import time
from functools import lru_cache
from pathlib import Path
from llama_index.core.query_engine import RetrieverQueryEngine
from .index import load_or_build_index
from llama_index.core import Settings
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import TextNode
from llama_index.core import StorageContext
from llama_index.core.vector_stores.simple import SimpleVectorStore
from llama_index.core import VectorStoreIndex

# Speed optimizations
Settings.chunk_size = 512  # Reduce chunk size for faster processing
Settings.chunk_overlap = 50  # Reduce overlap
Settings.embed_batch_size = 10  # Batch processing

# Required files and directories
REQUIRED_FILES = ["vector_store.json"]
REQUIRED_DIRS = ["data/simple", "data/datasheets/learned", "data/docs"]

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Consolidated storage directory for all index files
STORAGE_DIR = Path(__file__).parent.parent / "data" / "simple"

# Enhanced caching with TTL
_cache = {}
_cache_timestamps = {}
_CACHE_TTL = 3600  # 1 hour

def _is_cache_valid(key):
    """Check if cached item is still valid"""
    if key not in _cache_timestamps:
        return False
    return time.time() - _cache_timestamps[key] < _CACHE_TTL

def ask_ai_optimized(query: str) -> str:
    """Process a query using the index with caching and optimizations"""
    try:
        # Enhanced caching with TTL
        cache_key = f"query:{hash(query)}"
        if cache_key in _cache and _is_cache_valid(cache_key):
            logger.debug("Cache hit for query")
            return _cache[cache_key]

        index = load_or_build_index()
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=5,  # Reduced from 10 for faster response
            vector_store_query_mode="default",
            alpha=0.9
        )
        
        # Prepend instruction for casual, human-like response
        prompt = "Respond in a casual, friendly, and human-like manner. Do not be formal or explanatory. Answer directly and naturally.\n\n"
        full_query = prompt + query
        
        query_engine = RetrieverQueryEngine.from_args(
            retriever,
            response_mode="compact",
            timeout=10  # Reduced from 15 seconds
        )
        
        response = query_engine.query(full_query)
        
        if not response or not str(response).strip():
            logger.warning("Empty response from query engine")
            return "I couldn't find relevant information to answer your question."
            
        result = str(response)
        
        # Cache the result with timestamp
        _cache[cache_key] = result
        _cache_timestamps[cache_key] = time.time()
        
        return result
        
    except Exception as e:
        logger.error(f"Query processing error: {str(e)}", exc_info=True)
        return "I encountered an error while processing your request. Please try again."

# Backward compatibility - use optimized version
ask_ai = ask_ai_optimized
