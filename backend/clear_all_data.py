#!/usr/bin/env python3
"""
Comprehensive script to clear all learned data and previous history
This includes:
- Vector embeddings/index data
- Chat history and conversation logs
- Cached model data and temporary files
- Redis cache (if available)
"""
import os
import shutil
import glob
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

def clear_vector_embeddings():
    """Clear vector embeddings and index data"""
    print("🗂️  Clearing vector embeddings and index data...")
    
    # Storage directories to clear
    storage_dirs = [
        "d:\\Anish\\POC\\SEMICONSPACE_AI\\backend\\storage",
        "d:\\Anish\\POC\\SEMICONSPACE_AI\\backend\\data\\simple"
    ]
    
    files_cleared = 0
    for storage_dir in storage_dirs:
        if os.path.exists(storage_dir):
            print(f"   📁 Clearing {storage_dir}")
            for file in os.listdir(storage_dir):
                file_path = os.path.join(storage_dir, file)
                if os.path.isfile(file_path) and file.endswith('.json'):
                    try:
                        os.remove(file_path)
                        print(f"   ✅ Removed: {file}")
                        files_cleared += 1
                    except Exception as e:
                        print(f"   ❌ Failed to remove {file}: {e}")
        else:
            print(f"   ℹ️  Directory not found: {storage_dir}")
    
    print(f"   📊 Total vector/index files cleared: {files_cleared}")

def clear_chat_history():
    """Clear chat history and conversation logs"""
    print("💬 Clearing chat history and conversation logs...")
    
    files_cleared = 0
    
    # Clear memory.txt
    memory_file = "d:\\Anish\\POC\\SEMICONSPACE_AI\\backend\\data\\memory.txt"
    if os.path.exists(memory_file):
        try:
            with open(memory_file, 'w') as f:
                f.write("# Memory log cleared\n")
            print(f"   ✅ Cleared: memory.txt")
            files_cleared += 1
        except Exception as e:
            print(f"   ❌ Failed to clear memory.txt: {e}")
    
    # Clear learned interaction files
    docs_dir = "d:\\Anish\\POC\\SEMICONSPACE_AI\\backend\\data\\docs"
    if os.path.exists(docs_dir):
        learned_files = glob.glob(os.path.join(docs_dir, "learned_interaction_*.txt"))
        for file_path in learned_files:
            try:
                os.remove(file_path)
                print(f"   ✅ Removed: {os.path.basename(file_path)}")
                files_cleared += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {os.path.basename(file_path)}: {e}")
    
    # Clear learned datasheets directory if it exists
    learned_datasheets = "d:\\Anish\\POC\\SEMICONSPACE_AI\\backend\\data\\datasheets\\learned"
    if os.path.exists(learned_datasheets):
        try:
            shutil.rmtree(learned_datasheets)
            print(f"   ✅ Removed directory: learned datasheets")
            files_cleared += 1
        except Exception as e:
            print(f"   ❌ Failed to remove learned datasheets directory: {e}")
    
    print(f"   📊 Total chat history files cleared: {files_cleared}")

def clear_cache_data():
    """Clear Python cache and temporary files"""
    print("🗄️  Clearing cached model data and temporary files...")
    
    cache_dirs = [
        "d:\\Anish\\POC\\SEMICONSPACE_AI\\backend\\__pycache__",
        "d:\\Anish\\POC\\SEMICONSPACE_AI\\backend\\ai_engine\\__pycache__"
    ]
    
    dirs_cleared = 0
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                print(f"   ✅ Removed cache directory: {os.path.basename(cache_dir)}")
                dirs_cleared += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {cache_dir}: {e}")
    
    # Clear any .pyc files that might be scattered
    pyc_files = glob.glob("d:\\Anish\\POC\\SEMICONSPACE_AI\\backend\\**\\*.pyc", recursive=True)
    for pyc_file in pyc_files:
        try:
            os.remove(pyc_file)
            print(f"   ✅ Removed: {pyc_file}")
        except Exception as e:
            print(f"   ❌ Failed to remove {pyc_file}: {e}")
    
    print(f"   📊 Total cache directories cleared: {dirs_cleared}")

def clear_redis_cache():
    """Clear Redis cache data"""
    print("🔴 Clearing Redis cache...")
    
    try:
        # Connect to Redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, socket_connect_timeout=5)
        
        # Test connection
        r.ping()
        print(f"   ✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT} (DB: {REDIS_DB})")
        
        # Get current key count
        key_count = r.dbsize()
        print(f"   📊 Current keys in database: {key_count}")
        
        if key_count > 0:
            # Clear all keys in the current database
            r.flushdb()
            print(f"   🗑️  Cleared {key_count} keys from Redis database {REDIS_DB}")
        else:
            print("   ℹ️  Redis database is already empty")
            
        # Verify clearance
        remaining_keys = r.dbsize()
        if remaining_keys == 0:
            print("   ✅ Redis cache cleared successfully!")
        else:
            print(f"   ⚠️  Warning: {remaining_keys} keys still remain")
            
    except redis.ConnectionError as e:
        print(f"   ⚠️  Redis not available: {e}")
        print("   ℹ️  This is normal if Redis is not running or not used")
    except Exception as e:
        print(f"   ❌ Error clearing Redis cache: {e}")

def main():
    """Main function to clear all data"""
    print("🧹 Starting comprehensive data clearing process...")
    print("=" * 60)
    
    # Clear vector embeddings and index data
    clear_vector_embeddings()
    print()
    
    # Clear chat history and conversation logs
    clear_chat_history()
    print()
    
    # Clear cached model data
    clear_cache_data()
    print()
    
    # Clear Redis cache
    clear_redis_cache()
    print()
    
    print("=" * 60)
    print("🎉 Data clearing process completed!")
    print()
    print("📋 Summary of what was cleared:")
    print("   • Vector embeddings and index files (.json)")
    print("   • Chat history and learned interactions")
    print("   • Python cache files (__pycache__)")
    print("   • Redis cache (if available)")
    print()
    print("ℹ️  Note: The application will rebuild indexes and caches as needed")
    print("   when you start using it again.")

if __name__ == "__main__":
    main()