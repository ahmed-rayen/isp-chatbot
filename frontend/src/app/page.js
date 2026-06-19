'use client';

import { useState, useRef, useEffect } from 'react';
import { IconWifi, IconPlus, IconWifiOff, IconSpeedboat, IconRouter, IconFileInvoice, IconRobot, IconSend } from '@tabler/icons-react';

export default function ChatPage() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hello! I'm NetAssist, your technical support AI. How can I help you today?" }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async (textToSend) => {
    const messageText = textToSend || input;
    if (!messageText.trim() || isLoading) return;

    // 1. Update UI immediately with user message
    const newUserMessage = { role: 'user', content: messageText };
    setMessages((prev) => [...prev, newUserMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // 2. Call FastAPI Backend
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: messageText })
      });

      if (!response.ok) throw new Error('Network response was not ok');

      // 3. Parse the JSON response (No more streaming!)
      const data = await response.json();
      
      // 4. Save the session ID from the response body
      if (data.session_id) setSessionId(data.session_id);

      // 5. Add the AI's reply to the messages
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }]);

    } catch (error) {
      console.error('Error:', error);
      setMessages((prev) => [...prev, { role: 'assistant', content: "Sorry, I'm having trouble connecting to the server." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      {/* SIDEBAR */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon"><IconWifi size={16} color="#fff" /></div>
            <div>
              <div className="logo-text">NetAssist</div>
              <div className="logo-sub">ISP Support AI</div>
            </div>
          </div>
        </div>

        <button className="new-chat-btn">
          <IconPlus size={14} /> New conversation
        </button>

        <div className="section-label">Recent</div>
        <div className="chat-item active"><IconWifiOff size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} />Connection dropping</div>
        <div className="chat-item"><IconSpeedboat size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} />Slow speeds issue</div>
        <div className="chat-item"><IconRouter size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} />Router setup help</div>
        <div className="chat-item"><IconFileInvoice size={13} style={{ marginRight: '6px', verticalAlign: 'middle' }} />Billing question</div>

        <div className="sidebar-footer">
          <div className="user-row">
            <div className="avatar">AH</div>
            <div>
              <div className="user-name">Ahmed H.</div>
              <div className="user-role">Client #4821</div>
            </div>
          </div>
        </div>
      </div>

      {/* CHAT AREA */}
      <div className="chat-area">
        <div className="chat-header">
          <div className="chat-title">Technical Support</div>
          <div className="status-pill"><div className="dot"></div> Online</div>
        </div>

        <div className="messages">
          {messages.map((msg, index) => (
            <div key={index} className={`msg ${msg.role === 'user' ? 'user' : ''}`}>
              <div className={`msg-avatar ${msg.role === 'user' ? 'user-avatar-msg' : 'bot-avatar'}`}>
                {msg.role === 'user' ? 'AH' : <IconRobot size={13} />}
              </div>
              <div>
                <div className={`bubble ${msg.role === 'user' ? 'user-bubble' : 'bot-bubble'}`}>
                  {msg.content}
                </div>
                
                {/* Quick Chips only on the first bot message */}
                {index === 0 && msg.role === 'assistant' && (
                  <div className="quick-chips">
                    <div className="chip" onClick={() => handleSend('Internet not working')}>Internet not working</div>
                    <div className="chip" onClick={() => handleSend('Slow connection')}>Slow connection</div>
                    <div className="chip" onClick={() => handleSend('Router help')}>Router help</div>
                    <div className="chip" onClick={() => handleSend('Check my plan')}>Check my plan</div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Typing Indicator */}
          {isLoading && (
            <div className="msg">
              <div className="msg-avatar bot-avatar"><IconRobot size={13} /></div>
              <div className="typing"><span></span><span></span><span></span></div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <div className="input-row">
            <input 
              type="text" 
              placeholder="Describe your issue..." 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              disabled={isLoading}
            />
            <button className="send-btn" onClick={() => handleSend()} disabled={isLoading}>
              <IconSend size={15} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}