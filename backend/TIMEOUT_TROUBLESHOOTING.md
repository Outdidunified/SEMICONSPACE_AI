# Timeout Troubleshooting Guide

This guide helps you resolve timeout issues with the AI streaming functionality.

## Quick Fix

If you're experiencing timeout errors, try these steps:

1. **Update your `.env` file** with the new timeout settings:
   ```env
   OLLAMA_TIMEOUT=120.0
   OLLAMA_STREAMING_TIMEOUT=180.0
   OLLAMA_CONNECTION_TIMEOUT=30.0
   OLLAMA_READ_TIMEOUT=120.0
   ```

2. **Restart your application** to apply the new settings.

## Diagnostic Tools

### 1. Test Ollama Connection
Run the diagnostic script to check your Ollama setup:
```bash
python test_ollama.py
```

This will test:
- Ollama service availability
- Basic connection
- Streaming functionality
- Async streaming

### 2. Optimize Timeout Settings
Run the optimization script to find the best timeout values for your system:
```bash
python optimize_timeouts.py
```

This will:
- Benchmark your system's response times
- Calculate optimal timeout values
- Optionally update your `.env` file

## Common Issues and Solutions

### Issue: "ReadTimeout: timed out"
**Cause**: The request is taking longer than the configured timeout.

**Solutions**:
1. Increase timeout values in `.env`
2. Use a smaller/faster model
3. Reduce query complexity
4. Check system resources (CPU, RAM)

### Issue: "Connection refused"
**Cause**: Ollama service is not running.

**Solutions**:
1. Start Ollama: `ollama serve`
2. Check if the service is running on the correct port
3. Verify `OLLAMA_BASE_URL` in `.env`

### Issue: "Model not found"
**Cause**: The specified model is not available.

**Solutions**:
1. Pull the model: `ollama pull llama3:8b-instruct-q4_K_M`
2. Check available models: `ollama list`
3. Update `OLLAMA_MODEL` in `.env`

## Timeout Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_TIMEOUT` | 120.0 | General request timeout (seconds) |
| `OLLAMA_STREAMING_TIMEOUT` | 180.0 | Streaming request timeout (seconds) |
| `OLLAMA_CONNECTION_TIMEOUT` | 30.0 | Connection establishment timeout (seconds) |
| `OLLAMA_READ_TIMEOUT` | 120.0 | Read operation timeout (seconds) |

### Recommended Values by System

| System Type | OLLAMA_TIMEOUT | OLLAMA_STREAMING_TIMEOUT |
|-------------|----------------|--------------------------|
| High-end (GPU) | 60 | 120 |
| Mid-range (CPU) | 120 | 180 |
| Low-end | 180 | 300 |

## Performance Optimization

### 1. Model Selection
- Use quantized models (e.g., `q4_K_M`) for faster responses
- Smaller models respond faster but may be less accurate

### 2. System Resources
- Ensure adequate RAM (8GB+ recommended)
- Use GPU acceleration if available
- Close unnecessary applications

### 3. Query Optimization
- Keep queries concise and specific
- Avoid very long context
- Break complex queries into smaller parts

## Monitoring and Logging

The application now includes enhanced logging for timeout issues:

- Connection attempts and failures
- Streaming token counts and timing
- Retry attempts and backoff
- Health check results

Check the application logs for detailed timeout information.

## Advanced Configuration

### Custom Retry Logic
The streaming functions now include:
- 3 retry attempts with exponential backoff
- Graceful error handling
- Connection pooling

### Health Checks
Use the `/health` endpoint to monitor service status:
```bash
curl http://localhost:9001/health
```

## Getting Help

If you continue to experience timeout issues:

1. Run the diagnostic tools
2. Check the application logs
3. Verify your system meets the requirements
4. Consider using a smaller model or increasing timeout values

## Changelog

### Recent Improvements
- ✅ Increased default timeout values
- ✅ Added retry logic with exponential backoff
- ✅ Improved error handling and logging
- ✅ Added diagnostic and optimization tools
- ✅ Enhanced health check endpoint
- ✅ Better connection management