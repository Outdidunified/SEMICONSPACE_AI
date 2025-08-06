import React, { useState, useRef, useEffect } from 'react';
import { fetchEventSource } from '@fortaine/fetch-event-source';
import './App.css';

/**
 * @typedef {Object} Message
 * @property {'user'|'assistant'} role
 * @property {string} content
 * @property {string} timestamp
 * @property {boolean} [isStreaming]
 */

/**
 * @typedef {Object} ChatRequest
 * @property {string} message
 * @property {string} [context]
 */

const App = () => {
  const [input, setInput] = useState('');
  const [context, setContext] = useState('');
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState('');
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMessage = { role: 'user', content: input, timestamp };
    setMessages((prev) => [...prev, userMessage]);
    setIsStreaming(true);
    setError('');

    const request = { message: input.trim(), context: context.trim() || undefined };
    console.log('Sending request:', request);

    try {
      await fetchEventSource('http://localhost:9001/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(request),
        onopen(response) {
          console.log('SSE connection opened:', response.status);
          if (response.status === 422) {
            response.text().then(text => {
              console.error('Validation error:', text);
              setError('Invalid request: ' + text);
            });
            setIsStreaming(false);
            return;
          }
          if (response.status >= 400) {
            response.text().then(text => {
              console.error('HTTP error:', response.status, text);
              setError('Server error: ' + response.status + ' ' + text);
            });
            setIsStreaming(false);
            return;
          }
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: '', timestamp, isStreaming: true },
          ]);
        },
        onmessage(event) {
          console.log('SSE message received:', event.data);

          // Handle empty or null data
          if (!event.data || event.data.trim() === '') {
            return;
          }

          // Handle [DONE] signal
          if (event.data.trim() === '[DONE]') {
            setIsStreaming(false);
            setMessages((prev) =>
              prev.map((msg, idx) =>
                idx === prev.length - 1 ? { ...msg, isStreaming: false } : msg
              )
            );
            return;
          }

          // Remove the "data: " prefix from SSE messages if present
          let messageData = event.data;
          if (messageData.startsWith('data: ')) {
            messageData = messageData.substring(6);
          }

          // Handle [DONE] after prefix removal
          if (messageData.trim() === '[DONE]') {
            setIsStreaming(false);
            setMessages((prev) =>
              prev.map((msg, idx) =>
                idx === prev.length - 1 ? { ...msg, isStreaming: false } : msg
              )
            );
            return;
          }

          try {
            const data = JSON.parse(messageData);
            const content = data.choices?.[0]?.delta?.content || '';
            if (content) {
              setMessages((prev) =>
                prev.map((msg, idx) =>
                  idx === prev.length - 1
                    ? { ...msg, content: msg.content + content }
                    : msg
                )
              );
            }
          } catch (err) {
            console.error('Error parsing SSE data:', err, 'Data:', messageData);
            // Don't set error state for parsing issues, just log them
          }
        },
        onerror(err) {
          console.error('SSE error:', err);
          setError('Failed to connect to the server. Please try again.');
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((msg, idx) =>
              idx === prev.length - 1
                ? { ...msg, content: 'Connection error', isStreaming: false }
                : msg
            )
          );
        },
        onclose() {
          setIsStreaming(false);
        },
      });
    } catch (err) {
      console.error('Fetch error:', err);
      setError('An error occurred while fetching the response.');
      setIsStreaming(false);
      setMessages((prev) =>
        prev.map((msg, idx) =>
          idx === prev.length - 1
            ? { ...msg, content: 'Connection error', isStreaming: false }
            : msg
        )
      );
    }

    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="app-wrapper">
      <h1>Electronics AI Assistant</h1>
      <div className="chat-window" role="log" aria-live="polite">
        <div className="messages">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`message ${msg.role} ${msg.isStreaming ? 'streaming' : ''}`}
            >
              <div className="message-content">
                <span className="role">{msg.role === 'user' ? 'You' : 'AI'}</span>
                <span className="timestamp">{msg.timestamp}</span>
                <div className="content">{msg.content}</div>
                {msg.isStreaming && <span className="typing-indicator">▊</span>}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <form onSubmit={handleSubmit} className="input-form">
        <textarea
          className="context-input"
          rows={2}
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="Optional context (e.g., specific component or application)"
          aria-label="Enter context for your question"
        />
        <textarea
          className="query-input"
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about semiconductors (e.g., Explain ZX-101)"
          disabled={isStreaming}
          aria-label="Enter your question about electronics design"
        />
        <button
          type="submit"
          disabled={isStreaming || !input.trim()}
          className="submit-button"
          aria-label="Send message"
        >
          {isStreaming ? 'Streaming...' : 'Send'}
        </button>
      </form>
    </div>
  );
};

export default App;
