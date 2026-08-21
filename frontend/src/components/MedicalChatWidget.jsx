import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { chatAPI } from '../api/api';
import './MedicalChatWidget.css';

export default function MedicalChatWidget() {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I am your clinical educational assistant. You can ask me questions about skin lesion characteristics, ABCDE melanoma criteria, or your recent screening results.',
      sources: [],
    },
  ]);

  const messagesEndRef = useRef(null);

  // Extract case context if on /result or /history/:id
  const resultCaseId = location.state?.result?.case_id;
  const currentPathCaseMatch = location.pathname.match(/\/history\/(\d+)/);
  const activeCaseId = resultCaseId || (currentPathCaseMatch ? parseInt(currentPathCaseMatch[1], 10) : null);
  const activeCondition = location.state?.result?.primary_prediction?.condition || location.state?.result?.predicted_disease;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async (queryText) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMessage = { role: 'user', content: textToSend.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await chatAPI.ask(textToSend.trim(), activeCaseId);
      const assistantMessage = {
        role: 'assistant',
        content: res.data.answer,
        sources: res.data.sources || [],
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Chat query failed:', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'I experienced an issue connecting to the clinical knowledge base. Please try again or consult a dermatologist.',
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const starterQuestions = [
    activeCondition ? `Why was this classified as ${activeCondition}?` : 'What are the ABCDE criteria for melanoma?',
    'What does "pre-cancerous" mean?',
    'When should I see a dermatologist in person?',
  ];

  return (
    <div className="medical-chat-widget-wrapper">
      {!isOpen && (
        <button
          type="button"
          className="chat-floating-btn"
          onClick={() => setIsOpen(true)}
          aria-label="Open Medical Assistant"
        >
          <span className="chat-btn-icon">🩺</span>
          <span className="chat-btn-text">AI Clinical Assistant</span>
        </button>
      )}

      {isOpen && (
        <div className="chat-window-card">
          {/* Header */}
          <div className="chat-header">
            <div className="chat-header-info">
              <div className="chat-header-avatar">🩺</div>
              <div>
                <h4 className="chat-header-title">DermaAssist Assistant</h4>
                <span className="chat-header-status">Grounded Knowledge Base</span>
              </div>
            </div>
            <button
              type="button"
              className="chat-close-btn"
              onClick={() => setIsOpen(false)}
              aria-label="Close Chat"
            >
              ✕
            </button>
          </div>

          {/* Disclaimer Banner */}
          <div className="chat-disclaimer-banner">
            ⚕️ <strong>Educational Notice:</strong> Provides reference information only. Does not replace professional medical evaluation.
          </div>

          {/* Messages */}
          <div className="chat-messages-container">
            {messages.map((msg, index) => (
              <div key={index} className={`chat-msg ${msg.role}`}>
                <div className="msg-bubble">{msg.content}</div>

                {msg.sources && msg.sources.length > 0 && (
                  <div className="msg-citations">
                    <div className="citations-label">📚 Verified Sources:</div>
                    {msg.sources.map((src, i) => (
                      <div key={i} className="citation-item">
                        • <strong>{src.disease}</strong>: {src.section} ({src.source})
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="chat-msg assistant">
                <div className="msg-bubble chat-typing-dots">
                  <div className="chat-dot"></div>
                  <div className="chat-dot"></div>
                  <div className="chat-dot"></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Starter Suggestions */}
          <div className="chat-starters-section">
            <div className="starters-label">Suggested Inquiries:</div>
            <div className="starters-row">
              {starterQuestions.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="starter-chip"
                  onClick={() => handleSend(q)}
                  disabled={loading}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Input Form */}
          <form
            className="chat-input-form"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
          >
            <input
              type="text"
              className="chat-input-field"
              placeholder="Ask about skin conditions or your scan..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              className="chat-send-btn"
              disabled={!input.trim() || loading}
              aria-label="Send message"
            >
              ➤
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
