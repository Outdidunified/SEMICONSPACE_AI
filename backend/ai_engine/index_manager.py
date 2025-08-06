import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class IndexManager:
    """Manages index lifecycle and prevents unnecessary re-indexing"""
    
    def __init__(self, persist_dir="data/simple", memory_dir="data/docs", datasheet_dir="data/datasheets"):
        self.persist_dir = Path(persist_dir)
        self.memory_dir = Path(memory_dir)
        self.datasheet_dir = Path(datasheet_dir)
        self.state_file = self.persist_dir / "index_state.json"
        
    def get_directory_hash(self, directory):
        """Generate hash of directory contents to detect changes"""
        if not directory.exists():
            return "empty"
            
        hasher = hashlib.md5()
        try:
            for file_path in sorted(directory.rglob('*')):
                if file_path.is_file():
                    hasher.update(str(file_path.relative_to(directory)).encode())
                    hasher.update(str(file_path.stat().st_mtime).encode())
                    hasher.update(str(file_path.stat().st_size).encode())
        except Exception as e:
            logger.warning(f"Error hashing directory {directory}: {e}")
        return hasher.hexdigest()
    
    def get_current_state(self):
        """Get current state of all indexed directories"""
        return {
            "memory_hash": self.get_directory_hash(self.memory_dir),
            "datasheet_hash": self.get_directory_hash(self.datasheet_dir),
            "timestamp": datetime.now().isoformat()
        }
    
    def load_previous_state(self):
        """Load previous index state if exists"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading previous state: {e}")
        return None
    
    def save_state(self, state):
        """Save current index state"""
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving index state: {e}")
    
    def has_changes(self):
        """Check if directories have changed since last index"""
        previous_state = self.load_previous_state()
        if not previous_state:
            return True
            
        current_state = self.get_current_state()
        
        # Compare hashes
        if previous_state.get("memory_hash") != current_state["memory_hash"]:
            logger.info("Memory directory has changed")
            return True
            
        if previous_state.get("datasheet_hash") != current_state["datasheet_hash"]:
            logger.info("Datasheet directory has changed")
            return True
            
        return False
    
    def validate_index_files(self):
        """Check if all required index files exist and are valid"""
        required_files = [
            "vector_store.json",
            "docstore.json", 
            "index_store.json",
            "graph_store.json"
        ]
        
        for file in required_files:
            file_path = self.persist_dir / file
            if not file_path.exists():
                logger.info(f"Missing index file: {file}")
                return False
                
            # Check if file is valid JSON and not empty
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if not data:
                        logger.info(f"Empty index file: {file}")
                        return False
            except Exception as e:
                logger.info(f"Invalid index file {file}: {e}")
                return False
                
        return True
    
    def should_rebuild_index(self):
        """Determine if index should be rebuilt"""
        # First check if index files exist and are valid
        if not self.validate_index_files():
            logger.info("Index files missing or invalid - rebuilding")
            return True
            
        # Then check if content has changed
        if self.has_changes():
            logger.info("Content has changed - rebuilding")
            return True
            
        logger.info("Index is up to date - no rebuild needed")
        return False
    
    def mark_index_built(self):
        """Mark index as successfully built with current state"""
        current_state = self.get_current_state()
        self.save_state(current_state)
        logger.info("Index marked as built with current state")
