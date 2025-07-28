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

@lru_cache(maxsize=128)
def ask_ai(query: str) -> str:
    """Process a query using the index"""
    try:
        index = load_or_build_index()
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=15,
            vector_store_query_mode="default",
            alpha=0.8
        )
        
        # Retrieve nodes and validate
        nodes = retriever.retrieve(query)
        valid_nodes = []
        for node in nodes:
            if hasattr(node, 'node') and hasattr(node.node, 'metadata') and node.node.text:
                if node.node.node_id in index.docstore.docs:
                    valid_nodes.append(node)
                else:
                    logger.warning(f"Node ID {node.node.node_id} not found in docstore, skipping")
            else:
                logger.warning(f"Invalid node structure, skipping: {node}")
        
        if not valid_nodes:
            logger.warning("No valid nodes retrieved for query")
            return "I couldn't find any relevant information to answer that."

        # Check for AI identity query
        if query.lower().strip() in ["tell me your name", "what is your name", "who are you"]:
            for node in valid_nodes:
                if "your name is" in node.node.text.lower() and "semicon ai" in node.node.text.lower():
                    return "I am Semicon AI, nice to meet you!"

        query_engine = RetrieverQueryEngine.from_args(
            retriever,
            response_mode="compact",
            timeout=10
        )
        response = query_engine.query(query)
        if not response or not hasattr(response, 'response'):
            logger.error("Invalid response from query engine")
            return "I encountered an issue processing your request."
        return str(response.response)
    except Exception as e:
        logger.error(f"Query processing error: {str(e)}", exc_info=True)
        return "I encountered an error while processing your request. Please try again."

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
        logger.error(f"Streaming query failed: {e}", exc_info=True)
        yield "[Error] Something went wrong during response streaming]"

def learn_from_interaction(query: str, answer: str):
    """Append the Q&A to the index so the system learns from interactions."""
    try:
        index = load_or_build_index()
        storage_context = index.storage_context

        if not query.strip() or not answer.strip():
            logger.warning("Empty query or answer in learning attempt")
            return

        combined_text = f"Q: {query}\nA: {answer}"
        node = TextNode(text=combined_text)

        node_id = str(uuid.uuid4())
        node.metadata = {
            "type": "learned_interaction",
            "timestamp": str(int(time.time())),
            "query": query[:100],
            "_node_type": "TextNode",
            "document_id": node_id,
            "doc_id": node_id,
            "ref_doc_id": node_id,
            "valid": True,
            "is_ai_identity": "your name is" in query.lower() and "semicon ai" in query.lower()
        }

        if not all(hasattr(node, attr) for attr in ['text', 'metadata']):
            logger.error("Invalid node structure in learning attempt")
            return

        try:
            index.insert_nodes([node])
            logger.debug(f"Successfully learned interaction: {node_id}")
        except Exception as e:
            logger.error(f"Failed to insert learned node: {str(e)}", exc_info=True)
        
        _save_interaction_to_file(query, answer)
        
        try:
            storage_context.persist(persist_dir=STORAGE_DIR)
            logger.info(f"✅ Learned from interaction and updated the index. Persisted to {STORAGE_DIR}")
        except Exception as e:
            logger.error(f"Failed to persist index: {str(e)}", exc_info=True)
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