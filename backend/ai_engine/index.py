import os
import logging
from llama_index.core import VectorStoreIndex, StorageContext, SimpleDirectoryReader
from llama_index.core.vector_stores.simple import SimpleVectorStore
from pathlib import Path
from datetime import datetime
import json
from utils import get_chunked_documents
from config import configure_settings
from .index_manager import IndexManager

# Constants
PERSIST_DIR = "data/simple"
DATASHEET_DIR = "data/datasheets"
MEMORY_DIR = "data/docs"

# Ensure directories exist
os.makedirs(MEMORY_DIR, exist_ok=True)
os.makedirs(PERSIST_DIR, exist_ok=True)

# Initialize logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure settings
ollama_configured = configure_settings()
if not ollama_configured:
    print("⚠️ AI features will be unavailable until Ollama is running")

# Global index
_index = None
index_manager = IndexManager(
    persist_dir=PERSIST_DIR,
    memory_dir=MEMORY_DIR,
    datasheet_dir=DATASHEET_DIR
)

def get_documents():
    """Load documents from memory and datasheet directories"""
    if not any(Path(MEMORY_DIR).iterdir()) and not any(Path(DATASHEET_DIR).iterdir()):
        with open(os.path.join(MEMORY_DIR, "memory.txt"), "w", encoding="utf-8") as f:
            f.write("The system has not yet learned anything.")

    documents = []
    if os.path.exists(MEMORY_DIR) and os.listdir(MEMORY_DIR):
        documents.extend(SimpleDirectoryReader(MEMORY_DIR).load_data())
    if os.path.exists(DATASHEET_DIR) and os.listdir(DATASHEET_DIR):
        documents.extend(get_chunked_documents(SimpleDirectoryReader(DATASHEET_DIR).load_data()))
    return documents

def create_index():
    """Create a new SimpleVectorStore index"""
    global _index
    documents = get_documents()
    if not documents:
        raise ValueError("No documents available to create index")

    vector_store = SimpleVectorStore()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    try:
        logger.info("Creating index from documents...")
        _index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            show_progress=True,
            store_nodes_override=True
        )
        logger.info("Index created successfully")
        
        storage_context.persist(persist_dir=PERSIST_DIR)
        logger.info(f"New index persisted to {PERSIST_DIR} at {datetime.now().isoformat()}")
        index_manager.mark_index_built()
    except Exception as e:
        logger.error(f"Failed to create or persist index: {str(e)}")
        raise
    
    return _index

def load_or_build_index():
    """Load existing persisted index or create new if not available"""
    global _index
    logger.info(f"Attempting to load persisted index from {PERSIST_DIR}")

    if index_manager.should_rebuild_index():
        logger.info("Rebuilding index due to changes or missing files")
        return create_index()

    try:
        storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
        _index = VectorStoreIndex(nodes=[], storage_context=storage_context)
        logger.info(f"Loaded existing persisted index from {PERSIST_DIR}")
        return _index
    except Exception as e:
        logger.warning(f"Failed to load persisted index: {str(e)}. Rebuilding...")
        return create_index()

load_index = load_or_build_index
