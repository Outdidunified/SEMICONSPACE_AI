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
REQUIRED_DIRS = ["data/simple", "data/datasheets/learned"]

def initialize_environment():
    """Create all required directories and files at startup"""
    try:
        # Create required directories
        base_dir = Path(__file__).parent.parent
        for dir_path in REQUIRED_DIRS:
            os.makedirs(base_dir / dir_path, exist_ok=True)
        
        # Create or update vector_store.json if not present or invalid
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
logging.basicConfig(level=logging.INFO)
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

@lru_cache(maxsize=128)
def ask_ai(query: str) -> str:
    """Process a query using the index"""
    index = load_or_build_index()
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=15,  # Increased to capture learned data better
        vector_store_query_mode="default",
        alpha=0.8  # Adjusted to prioritize learned data
    )
    query_engine = RetrieverQueryEngine.from_args(
        retriever,
        response_mode="compact",
        timeout=10
    )
    response = query_engine.query(query)
    return str(response)

async def ask_ai_streaming(query: str):
    """Stream tokens for a query"""
    try:
        index = load_or_build_index()
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=15,
            vector_store_query_mode="default",
            alpha=0.8
        )
        query_engine = RetrieverQueryEngine.from_args(
            retriever,
            streaming=True,
            response_mode="compact",
            timeout=10
        )
        response = query_engine.query(query)
        if hasattr(response, 'response_gen') and response.response_gen is not None:
            logger.debug("Streaming response started")
            async for token in response.response_gen:
                logger.debug(f"Token: {token}")
                yield token
        else:
            logger.warning("LLM does not support streaming, yielding full response")
            yield str(response)
    except Exception as e:
        logger.error(f"Streaming query failed: {e}")
        yield "[Error] Something went wrong during response streaming]"

def learn_from_interaction(query: str, answer: str):
    """Append the Q&A to the index so the system learns from interactions."""
    try:
        index = load_or_build_index()  # Use the cached index
        storage_context = index.storage_context  # Use the existing storage context

        combined_text = f"Q: {query}\nA: {answer}"
        node = TextNode(text=combined_text)

        # Add metadata to the node for better retrieval
        node_id = str(uuid.uuid4())
        node.metadata = {
            "type": "learned_interaction",
            "timestamp": str(int(time.time())),
            "query": query[:100],  # First 100 chars for reference
            "_node_type": "TextNode",
            "document_id": node_id,
            "doc_id": node_id,
            "ref_doc_id": node_id
        }

        index.insert_nodes([node])
        
        # Also save to file for backup and transparency
        _save_interaction_to_file(query, answer)
        
        try:
            index.storage_context.persist(persist_dir=STORAGE_DIR)
            logger.info(f"✅ Learned from interaction and updated the index. Persisted to {STORAGE_DIR}")
        except Exception as e:
            logger.error(f"Failed to persist index: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Failed to learn from interaction: {str(e)}", exc_info=True)
        raise

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
        # Don't raise here as this is just backup functionality