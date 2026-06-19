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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async (textToSend) => {
    const messageText = textToSend || input;
    if (!messageText.trim() || isLoading) return;

    // 1. Add user message
    const newUserMessage = { role: 'user', content: messageText };
    setMessages((prev) => [...prev, newUserMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // 2. Call FastAPI Backend
      const response = await fetch(process.env.NEXT_PUBLIC_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: messageText })
      });

      if (!response.ok) throw new Error('Network response was not ok');

      // 3. Parse JSON
      const data = await response.json();
      if (data.session_id) setSessionId(data.session_id);

      // 4. Hide loading dots, add empty bot message
      setIsLoading(false);
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      const fullText = data.reply;
      let currentIndex = 0;

      // 5. Typing Effect Logic
      const typingInterval = setInterval(() => {
        if (currentIndex < fullText.length) {
          setMessages((prev) => {
            const newMessages = [...prev];
            // Append 2 characters at a time for a smooth, fast typing effect
            const nextChars = fullText.substring(currentIndex, currentIndex + 2);
            newMessages[newMessages.length - 1] = {
              role: 'assistant',
              content: newMessages[newMessages.length - 1].content + nextChars
            };
            return newMessages;
          });
          currentIndex += 2;
        } else {
          clearInterval(typingInterval); // Stop when finished
        }
      }, 10); // Speed of typing (10ms is fast but smooth)

    } catch (error) {
      console.error('Error:', error);
      setIsLoading(false);
      setMessages((prev) => [...prev, { role: 'assistant', content: "Sorry, I'm having trouble connecting to the server." }]);
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