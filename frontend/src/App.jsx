import React, { useState, useRef, useEffect } from 'react';
import { fetchEventSource } from '@fortaine/fetch-event-source';
import './App.css';

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

    try {
      await fetchEventSource('http://localhost:9001/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(request),
        onopen(response) {
          if (response.status >= 400) {
            response.text().then(text => {
              setError('Server error: ' + response.status + ' ' + text);
            });
            setIsStreaming(false);
            return;
          }
          setMessages((prev) => [...prev, { role: 'assistant', content: '', timestamp, isStreaming: true }]);
        },
        onmessage(event) {
          if (!event.data?.trim() || event.data.trim() === '[DONE]') {
            setIsStreaming(false);
            setMessages((prev) => prev.map((msg, i) => i === prev.length - 1 ? { ...msg, isStreaming: false } : msg));
            return;
          }

          let messageData = event.data.startsWith('data: ') ? event.data.substring(6) : event.data;

          try {
            const data = JSON.parse(messageData);
            const content = data.choices?.[0]?.delta?.content || '';
            if (content) {
              setMessages((prev) => prev.map((msg, i) => i === prev.length - 1 ? { ...msg, content: msg.content + content } : msg));
            }
          } catch {
            // Intentionally ignore JSON parse errors for streaming chunks
          }
        },
        onerror() {
          setError('Failed to connect to the server. Please try again.');
          setIsStreaming(false);
          setMessages((prev) => prev.map((msg, i) => i === prev.length - 1 ? { ...msg, content: 'Connection error', isStreaming: false } : msg));
        },
        onclose() {
          setIsStreaming(false);
        },
      });
    } catch {
      setError('An error occurred while fetching the response.');
      setIsStreaming(false);
      setMessages((prev) => prev.map((msg, i) => i === prev.length - 1 ? { ...msg, content: 'Connection error', isStreaming: false } : msg));
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
    <div className="flex flex-col items-center min-h-screen p-6 bg-gray-100">
      <h1 className="text-3xl font-bold text-blue-700 mb-4">🔌 Semicon AI Assistant</h1>
      <div className="w-full max-w-3xl bg-white rounded-xl shadow-md p-4 overflow-y-auto h-[70vh]">
        {messages.map((msg, i) => (
          <div key={i} className={`mb-3 p-3 rounded-lg ${msg.role === 'user' ? 'bg-blue-50' : 'bg-green-50'}`}>
            <div className="text-xs text-gray-500 flex justify-between">
              <span>{msg.role === 'user' ? 'You' : 'Semicon AI'}</span>
              <span>{msg.timestamp}</span>
            </div>
            <div className="mt-1 text-sm whitespace-pre-wrap">{msg.content}</div>
            {msg.isStreaming && <span className="animate-pulse text-xs text-gray-400">▊ typing...</span>}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      {error && <div className="text-red-500 text-sm mt-2">{error}</div>}

      <form onSubmit={handleSubmit} className="mt-4 w-full max-w-3xl space-y-2">
        <textarea
          className="w-full p-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-400"
          rows={2}
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="Optional context (e.g., component or target app)"
        />
        <div className="flex items-center gap-2">
          <textarea
            className="flex-1 p-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-400"
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about electronics, parts, or circuits..."
            disabled={isStreaming}
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-2 rounded-md"
          >
            {isStreaming ? '⏳' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default App;
