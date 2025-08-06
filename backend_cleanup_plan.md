# Backend Cleanup Plan

## Files to Remove (Unused/Redundant)

### Test/Utility Scripts (Not Imported)

- [ ] `test_ollama.py` - Test script for Ollama connection
- [ ] `optimize_timeouts.py` - Timeout optimization script
- [ ] `streaming_fix.py` - Fix script (likely outdated)
- [ ] `start_optimized.py` - Optimization script
- [ ] `warmup_model.py` - Model warmup script
- [ ] `test_ollama.py` - Test script (duplicate)

### Documentation Files (Not Used in Functionality)

- [ ] `PERFORMANCE_GUIDE.md`
- [ ] `TIMEOUT_TROUBLESHOOTING.md`

### Development/Cleanup Scripts

- [ ] `clear_all_data.py` - Data clearing script
- [ ] `optimize_timeouts.py` - Optimization script (duplicate)

### Configuration/Setup Files

- [ ] `.python-version` - Python version specification
- [ ] `Dockerfile` - Docker configuration (if not using Docker)

## Files to Keep (Core Functionality)

- [x] `main.py` - Main FastAPI application
- [x] `config.py` - Configuration settings
- [x] `ai_engine/` - AI engine directory
  - [x] `ai_engine/__init__.py`
  - [x] `ai_engine/ai_engine.py`
  - [x] `ai_engine/component_recommender.py`
  - [x] `ai_engine/index.py`
- [x] `health.py` - Health check endpoint
- [x] `utils.py` - Utility functions
- [x] `requirements.txt` - Dependencies
- [x] `data/` - Data directory
- [x] `storage/` - Storage directory

## Execution Steps

1. Backup current backend directory
2. Remove identified unused files
3. Verify core functionality still works
4. Update any references if needed
