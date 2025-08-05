import { useState, useRef, useEffect } from "react";
import "./App.css";

function App() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("ask"); // 'ask' or 'stream'
  const chatRef = useRef(null);
  const textareaRef = useRef(null);
  const [messagesByMode, setMessagesByMode] = useState({
    ask: [],
    stream: [],
  });
  const [eventSource, setEventSource] = useState(null);

  const handleAskSubmit = async () => {
    if (!query.trim()) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsg = { type: "user", text: query, timestamp };
    const thinkingMsg = { type: "ai", text: "⚙️ Thinking...", timestamp, isThinking: true };
    const currentMessages = messagesByMode[mode];
    const currentIndex = currentMessages.length;

    const updatedMessages = [...currentMessages, userMsg, thinkingMsg];
    setMessagesByMode((prev) => ({ ...prev, [mode]: updatedMessages }));

    try {
      if (mode === "ask") {
        const res = await fetch("http://localhost:9001/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query }),
        });

        if (!res.ok) throw new Error("Network response was not ok");

        const data = await res.json();
        setMessagesByMode((prev) => {
          const updated = { ...prev };
          updated[mode][currentIndex + 1] = { type: "ai", text: data.response, timestamp };
          return updated;
        });
      } else {
        // Use SSE for streaming
        handleSSEChat(query, currentIndex, timestamp);
      }
    } catch (error) {
      setMessagesByMode((prev) => {
        const updated = { ...prev };
        updated[mode][currentIndex + 1] = {
          type: "ai",
          text: "Unable to fetch response",
          timestamp,
        };
        return updated;
      });
    }

    setQuery("");
    textareaRef.current?.focus();
  };

  const handleSSEChat = (message, currentIndex, timestamp) => {
    // Close existing EventSource if any
    if (eventSource) {
      eventSource.close();
    }

    // Create new EventSource for POST request
    // We'll use fetch with EventSource-like handling
    const controller = new AbortController();

    fetch("http://localhost:9001/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error("Network response was not ok");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let responseText = "";

        setMessagesByMode((prev) => {
          const updated = { ...prev };
          updated[mode][currentIndex + 1] = { type: "ai", text: "", timestamp, isStreaming: true };
          return updated;
        });

        const processStream = async () => {
          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              const chunk = decoder.decode(value);
              const lines = chunk.split('\n');

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const data = line.slice(6);

                  if (data === '[DONE]') {
                    setMessagesByMode((prev) => {
                      const updated = { ...prev };
                      updated[mode][currentIndex + 1] = {
                        type: "ai",
                        text: responseText,
                        timestamp,
                        isStreaming: false,
                      };
                      return updated;
                    });
                    return;
                  }

                  try {
                    const parsed = JSON.parse(data);
                    const content = parsed.choices?.[0]?.delta?.content || "";
                    responseText += content;

                    setMessagesByMode((prev) => {
                      const updated = { ...prev };
                      updated[mode][currentIndex + 1] = {
                        type: "ai",
                        text: responseText,
                        timestamp,
                        isStreaming: true,
                      };
                      return updated;
                    });
                  } catch (e) {
                    console.error("Error parsing SSE data:", e);
                  }
                }
              }
            }
          } catch (error) {
            console.error("Stream error:", error);
            setMessagesByMode((prev) => {
              const updated = { ...prev };
              updated[mode][currentIndex + 1] = {
                type: "ai",
                text: "Stream connection error",
                timestamp,
              };
              return updated;
            });
          }
        };

        processStream();
      })
      .catch((error) => {
        console.error("Fetch error:", error);
        setMessagesByMode((prev) => {
          const updated = { ...prev };
          updated[mode][currentIndex + 1] = {
            type: "ai",
            text: "Unable to fetch response",
            timestamp,
          };
          return updated;
        });
      });
  };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    // Close EventSource when switching modes
    if (eventSource) {
      eventSource.close();
      setEventSource(null);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAskSubmit();
    }
  };

  const currentMessages = messagesByMode[mode];

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" });
  }, [currentMessages]);

  useEffect(() => {
    // Cleanup EventSource on unmount
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [eventSource]);

  return (
    <div className="app-wrapper">
      <div className="mode-selector">
        <button
          className={`mode-btn ${mode === "ask" ? "active" : ""}`}
          onClick={() => handleModeChange("ask")}
        >
          Standard Ask
        </button>
        <button
          className={`mode-btn ${mode === "stream" ? "active" : ""}`}
          onClick={() => handleModeChange("stream")}
        >
          SSE Stream
        </button>
      </div>

      <div className="chat-window" ref={chatRef} role="log" aria-live="polite">
        <div className="response-box">
          {messagesByMode[mode].map((msg, index) => (
            <div
              key={index}
              className={`chat-bubble ${msg.type} ${msg.isThinking ? "thinking" : msg.isStreaming ? "streaming" : ""}`}
            >
              <span>{msg.text}</span>
              <span className="message-time">{msg.timestamp}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="input-bar" role="form">
        <textarea
          ref={textareaRef}
          className="query-input"
          rows={2}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Semicon's AI about electronics design..."
          aria-label="Enter your question about electronics design"
        />
        <button className="submit-button" onClick={handleAskSubmit} aria-label="Send message">
          ➤
          <span className="sr-only">Send</span>
        </button>
      </div>
    </div>
  );
}

export default App;
