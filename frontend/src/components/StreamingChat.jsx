import { useState, useRef, useEffect } from "react";
import { fetchEventSource } from '@fortaine/fetch-event-source';

const StreamingChat = () => {
    const [message, setMessage] = useState("");
    const [chatHistory, setChatHistory] = useState([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState("");
    const chatEndRef = useRef(null);

    const scrollToBottom = () => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [chatHistory]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!message.trim() || isStreaming) return;

        const userMessage = { role: "user", content: message, timestamp: new Date().toLocaleTimeString() };
        setChatHistory(prev => [...prev, userMessage]);
        setIsStreaming(true);
        setError("");

        try {
            const controller = new AbortController();

            await fetchEventSource('http://localhost:9001/ask-stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: message }),
                signal: controller.signal,
                onopen: async (response) => {
                    if (response.ok) {
                        const aiMessage = {
                            role: "assistant",
                            content: "",
                            timestamp: new Date().toLocaleTimeString(),
                            isStreaming: true
                        };
                        setChatHistory(prev => [...prev, aiMessage]);
                    } else {
                        throw new Error(`Failed to open: ${response.status}`);
                    }
                },
                onmessage: (event) => {
                    if (event.data === '[DONE]') {
                        setIsStreaming(false);
                        setChatHistory(prev => prev.map((msg, idx) =>
                            idx === prev.length - 1 ? { ...msg, isStreaming: false } : msg
                        ));
                        return;
                    }

                    try {
                        const data = JSON.parse(event.data);
                        const content = data.choices?.[0]?.delta?.content || "";

                        setChatHistory(prev => prev.map((msg, idx) =>
                            idx === prev.length - 1
                                ? { ...msg, content: msg.content + content }
                                : msg
                        ));
                    } catch (e) {
                        console.error("Error parsing SSE data:", e);
                    }
                },
                onerror: (error) => {
                    console.error("SSE Error:", error);
                    setError("Connection error. Please try again.");
                    setIsStreaming(false);
                },
                onclose: () => {
                    setIsStreaming(false);
                }
            });
        } catch (error) {
            console.error("Streaming error:", error);
            setError("Failed to connect to server. Please try again.");
            setIsStreaming(false);
        }

        setMessage("");
    };

    return (
        <div className="streaming-chat">
            <div className="chat-container">
                <div className="messages">
                    {chatHistory.map((msg, index) => (
                        <div key={index} className={`message ${msg.role}`}>
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

                <form onSubmit={handleSubmit} className="input-form">
                    <input
                        type="text"
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder="Ask about electronics design..."
                        disabled={isStreaming}
                        className="message-input"
                    />
                    <button type="submit" disabled={isStreaming || !message.trim()}>
                        {isStreaming ? 'Streaming...' : 'Send'}
                    </button>
                </form>

                {error && <div className="error">{error}</div>}
            </div>
        </div>
    );
};

export default StreamingChat;
