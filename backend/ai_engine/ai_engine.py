import os
import uuid
import logging
import json
import time
from functools import lru_cache
from pathlib import Path
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core import Settings
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import TextNode
from .index import load_or_build_index
import asyncio

# Initialize logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Consolidated storage directory
STORAGE_DIR = Path(__file__).parent.parent / "data" / "simple"

def initialize_environment():
    """Create required directories and files at startup"""
    try:
        base_dir = Path(__file__).parent.parent
        data_dir = base_dir / "data"
        if not data_dir.exists():
            os.makedirs(data_dir)
            logger.info(f"Created data directory: {data_dir}")
        for dir_path in ["data/simple", "data/datasheets/learned", "data/docs"]:
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
            similarity_top_k=5,
            vector_store_query_mode="default",
            alpha=0.9
        )
        
        prompt = f"In the context of semiconductors: {query}"
        from config import OLLAMA_TIMEOUT
        query_engine = RetrieverQueryEngine.from_args(
            retriever,
            response_mode="compact",
            timeout=OLLAMA_TIMEOUT
        )
        
        response = query_engine.query(prompt)
        
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
    """Streaming query with document retrieval"""
    try:
        logger.info("Starting streaming query")
        index = load_or_build_index()
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=5,
            vector_store_query_mode="default",
            alpha=0.9
        )
        
        from config import OLLAMA_STREAMING_TIMEOUT
        query_engine = RetrieverQueryEngine.from_args(
            retriever,
            response_mode="compact",
            streaming=True,
            timeout=OLLAMA_STREAMING_TIMEOUT
        )
        
        prompt = f"In the context of semiconductors: {query}"
        streaming_response = query_engine.query(prompt)
        
        chunk_count = 0
        for chunk in streaming_response.response_gen:
            if chunk:
                chunk_count += 1
                yield chunk
                await asyncio.sleep(0.001)
                if chunk_count > 150:
                    break
        logger.info(f"Streaming completed with {chunk_count} chunks")
        
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        error_msg = "Service temporarily unavailable"
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
                    similarity_top_k=5,
                    vector_store_query_mode="default",
                    alpha=0.9
                )
                
                prompt = f"In the context of semiconductors: {query}"
                query_engine = RetrieverQueryEngine.from_args(
                    retriever,
                    response_mode="compact",
                    timeout=timeout
                )
                
                response = query_engine.query(prompt)
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
    """Append Q&A to the index for learning"""
    try:
        if not query.strip() or not answer.strip():
            logger.warning("Empty query or answer provided for learning")
            return
        index = load_or_build_index()
        combined_text = f"Question: {query.strip()}\nAnswer: {answer.strip()}"
        node = TextNode(text=combined_text, id_=str(uuid.uuid4()))
        node.metadata = {
            "type": "learned_interaction",
            "timestamp": str(int(time.time())),
            "source": "user_interaction",
            "query_preview": query[:100] + "..." if len(query) > 100 else query
        }
        index.insert_nodes([node])
        logger.info("Successfully added learned interaction to index")
        try:
            index.storage_context.persist(persist_dir=STORAGE_DIR)
            logger.info(f"Persisted interaction to {STORAGE_DIR}")
        except Exception as e:
            logger.error(f"Failed to persist interaction: {str(e)}")
        _save_interaction_to_file(query, answer)
    except Exception as e:
        logger.error(f"Failed to learn from interaction: {str(e)}")

def _save_interaction_to_file(query: str, answer: str):
    """Save interaction to file"""
    try:
        learned_dir = Path(__file__).parent.parent / "data" / "docs"
        learned_dir.mkdir(exist_ok=True)
        timestamp = int(time.time())
        filename = f"learned_interaction_{timestamp}.txt"
        filepath = learned_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Timestamp: {timestamp}\nQuery: {query}\nAnswer: {answer}\n---\n")
        logger.debug(f"Saved interaction to file: {filepath}")
    except Exception as e:
        logger.warning(f"Failed to save interaction to file: {str(e)}")