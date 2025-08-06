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

# Required files and directories
REQUIRED_FILES = ["vector_store.json"]
REQUIRED_DIRS = ["data/simple", "data/datasheets/learned", "data/docs"]

def initialize_environment():
    """Create all required directories and files at startup"""
    try:
        base_dir = Path(__file__).parent.parent
        # Ensure base data directory exists
        data_dir = base_dir / "data"
        if not data_dir.exists():
            os.makedirs(data_dir)
            logger.info(f"Created data directory: {data_dir}")
            
        # Create all required subdirectories
        for dir_path in REQUIRED_DIRS:
            full_path = base_dir / dir_path
            if not full_path.exists():
                os.makedirs(full_path)
                logger.info(f"Created directory: {full_path}")
        
        vector_store_path = base_dir / "data/simple" / "vector_store.json"
        if not vector_store_path.exists():
            with open(vector_store_path, 'w', encoding="utf-8") as f:
                json.dump({}, f)
            logger.info(f"Created empty vector_store.json at {vector_store_path}")
        else:
            try:
                with open(vector_store_path, 'r', encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupted vector_store.json at {vector_store_path}. Recreating...")
                with open(vector_store_path, 'w', encoding="utf-8") as f:
                    json.dump({}, f)
                logger.info(f"Recreated empty vector_store.json at {vector_store_path}")
        
        logger.info("Environment initialized with required files and directories")
    except Exception as e:
        logger.error(f"Failed to initialize environment: {str(e)}")
        raise

# Consolidated storage directory for all index files
STORAGE_DIR = Path(__file__).parent.parent / "data" / "simple"

# Initialize logging and environment
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
initialize_environment()

def validate_storage_files():
    """Check if storage files exist and are valid JSON"""
    try:
        required_files = ["vector_store.json"]
        for file in required_files:
            file_path = STORAGE_DIR / file
            if not file_path.exists():
                logger.warning(f"Missing storage file: {file}")
                return False
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Corrupted storage file {file}: {str(e)}")
                return False
        return True
    except Exception as e:
        logger.error(f"Storage validation failed: {str(e)}", exc_info=True)
        return False

_cache = {}

def ask_ai(query: str) -> str:
    """Process a query using the index with caching"""
    try:
        if query in _cache:
            logger.debug("Cache hit for query")
            return _cache[query]

        index = load_or_build_index()
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=10,  # Further reduced for faster response
            vector_store_query_mode="default",
            alpha=0.9
        )
        
        # Prepend instruction for casual, human-like response
        prompt = "Respond in a casual, friendly, and human-like manner. Do not be formal or explanatory. Answer directly and naturally.\n\n"
        full_query = prompt + query
        
        from config import OLLAMA_TIMEOUT
        query_engine = RetrieverQueryEngine.from_args(
            retriever,
            response_mode="compact",
            timeout=OLLAMA_TIMEOUT
        )
        
        response = query_engine.query(full_query)
        
        if not response or not str(response).strip():
            logger.warning("Empty response from query engine")
            return "I couldn't find relevant information to answer your question."
            
        result = str(response)
        _cache[query] = result
        return result
        
    except Exception as e:
        logger.error(f"Query processing error: {str(e)}", exc_info=True)
        return "I encountered an error while processing your request. Please try again."

async def ask_ai_streaming(query: str):
    """Optimized streaming implementation for super fast responses"""
    import asyncio
    from config import OLLAMA_STREAMING_TIMEOUT
    from llama_index.core import Settings
    
    try:
        logger.info("Starting optimized streaming query")
        
        # Use direct LLM streaming for maximum speed (bypass index for now)
        llm = Settings.llm
        if not llm:
            yield "[Error] AI service not available"
            return
        
        # Simplified prompt for faster processing
        optimized_prompt = f"Answer briefly and directly: {query}"
        
        # Direct streaming from LLM
        try:
            streaming_response = llm.stream_complete(optimized_prompt)
            
            token_count = 0
            for token in streaming_response:
                if token and token.delta:
                    token_count += 1
                    yield token.delta
                    # Minimal delay for super fast streaming
                    await asyncio.sleep(0.001)
                    
                    # Limit response length for speed
                    if token_count > 200:
                        break
            
            logger.info(f"Fast streaming completed with {token_count} tokens")
            
        except Exception as direct_error:
            logger.warning(f"Direct streaming failed, falling back to index: {direct_error}")
            
            # Fallback to index-based streaming with minimal retrieval
            try:
                index = load_or_build_index()
                retriever = VectorIndexRetriever(
                    index=index,
                    similarity_top_k=2,  # Minimal retrieval for speed
                    vector_store_query_mode="default",
                    alpha=0.9
                )
                
                from llama_index.core.query_engine import RetrieverQueryEngine
                
                query_engine = RetrieverQueryEngine.from_args(
                    retriever,
                    response_mode="compact",
                    streaming=True,
                    timeout=OLLAMA_STREAMING_TIMEOUT
                )
                
                streaming_response = query_engine.query(f"Answer briefly: {query}")
                
                if hasattr(streaming_response, 'response_gen'):
                    token_count = 0
                    for token in streaming_response.response_gen:
                        if token:
                            token_count += 1
                            yield token
                            await asyncio.sleep(0.001)
                            
                            # Limit for speed
                            if token_count > 150:
                                break
                else:
                    # Character-by-character streaming as last resort
                    response_text = str(streaming_response)[:500]  # Limit length
                    for char in response_text:
                        yield char
                        await asyncio.sleep(0.001)
                        
            except Exception as fallback_error:
                logger.error(f"Fallback streaming failed: {fallback_error}")
                yield "[Error] Unable to generate response. Please try again."
                
    except Exception as e:
        logger.error(f"Streaming error: {e}", exc_info=True)
        error_msg = "Service temporarily unavailable. Please try again."
        if "timeout" in str(e).lower():
            error_msg = "Response timed out. Try a shorter question."
        yield f"[Error] {error_msg}"

def ask_ai_with_timeout(query: str, timeout: int = None) -> str:
    """Process a query with timeout and retry mechanism"""
    import concurrent.futures
    from config import OLLAMA_TIMEOUT
    
    if timeout is None:
        timeout = int(OLLAMA_TIMEOUT)
    
    def _query_with_retry():
        max_retries = 3
        for attempt in range(max_retries):
            try:
                index = load_or_build_index()
                retriever = VectorIndexRetriever(
                    index=index,
                    similarity_top_k=8,  # Further reduced for performance
                    vector_store_query_mode="default",
                    alpha=0.9
                )
                
                prompt = "Respond in a casual, friendly, and human-like manner. Do not be formal or explanatory. Answer directly and naturally.\n\n"
                full_query = prompt + query
                
                query_engine = RetrieverQueryEngine.from_args(
                    retriever,
                    response_mode="compact",
                    timeout=timeout
                )
                
                response = query_engine.query(full_query)
                return str(response)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"Query attempt {attempt + 1} failed, retrying...")
                time.sleep(1)
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_query_with_retry)
            return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        return "Request timed out. Please try a simpler query."
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        return "I encountered an error processing your request."

def learn_from_interaction(query: str, answer: str):
    """Append the Q&A to the index so the system learns from interactions."""
    try:
        # Validate inputs
        if not query or not query.strip() or not answer or not answer.strip():
            logger.warning("Empty query or answer provided for learning")
            return

        index = load_or_build_index()
        
        # Create a well-formatted learning text
        combined_text = f"Question: {query.strip()}\nAnswer: {answer.strip()}"
        
        # Create node with proper structure
        node = TextNode(
            text=combined_text,
            id_=str(uuid.uuid4())
        )
        
        # Add metadata for better retrieval
        node.metadata = {
            "type": "learned_interaction",
            "timestamp": str(int(time.time())),
            "source": "user_interaction",
            "query_preview": query[:100] + "..." if len(query) > 100 else query
        }

        # Insert the node into the index
        index.insert_nodes([node])
        logger.info(f"Successfully added learned interaction to index")
        
        # Save to file for backup
        _save_interaction_to_file(query, answer)
        
        # Persist the updated index
        try:
            index.storage_context.persist(persist_dir=STORAGE_DIR)
            logger.info(f"✅ Learned interaction persisted to {STORAGE_DIR}")
        except Exception as persist_error:
            logger.error(f"Failed to persist learned interaction: {persist_error}")
            # Don't raise here as the learning was successful, just persistence failed
            
    except Exception as e:
        logger.error(f"Failed to learn from interaction: {str(e)}", exc_info=True)
        # Don't raise to avoid breaking the main request flow

def _save_interaction_to_file(query: str, answer: str):
    """Save interaction to a file for backup and transparency"""
    try:
        learned_dir = Path(__file__).parent.parent / "data" / "docs"
        learned_dir.mkdir(exist_ok=True)
        
        timestamp = int(time.time())
        filename = f"learned_interaction_{timestamp}.txt"
        filepath = learned_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Query: {query}\n")
            f.write(f"Answer: {answer}\n")
            f.write("---\n")
        
        logger.debug(f"Saved interaction to file: {filepath}")
    except Exception as e:
        logger.warning(f"Failed to save interaction to file: {str(e)}")