'use client';

import { useState, useRef, useEffect } from 'react';
import { IconWifi, IconPlus, IconRobot, IconSend, IconTrash, IconMessage2 } from '@tabler/icons-react';

export default function ChatPage() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hello! I'm NetAssist, your technical support AI. How can I help you today?" }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [chatSessions, setChatSessions] = useState([]); // Sidebar chats
  const messagesEndRef = useRef(null);

  const API_BASE = 'http://localhost:8000/api'; // Hardcoded for now, or use your .env

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Fetch all past chats on mount
  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`);
      const data = await res.json();
      setChatSessions(data);
    } catch (e) { console.error("Failed to load sessions"); }
  };

  const startNewChat = () => {
    setSessionId(null);
    setMessages([{ role: 'assistant', content: "Hello! I'm NetAssist, your technical support AI. How can I help you today?" }]);
  };

  const loadChat = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/sessions/${id}/messages`);
      const data = await res.json();
      if (data.length > 0) {
        setMessages(data);
        setSessionId(id);
      } else {
        startNewChat();
        setSessionId(id);
      }
    } catch (e) { console.error("Failed to load chat"); }
  };

  const deleteChat = async (e, id) => {
    e.stopPropagation(); // Prevent triggering loadChat
    try {
      await fetch(`${API_BASE}/sessions/${id}`, { method: 'DELETE' });
      if (sessionId === id) startNewChat();
      fetchSessions();
    } catch (e) { console.error("Failed to delete"); }
  };

  const handleSend = async (textToSend) => {
    const messageText = textToSend || input;
    if (!messageText.trim() || isLoading) return;

    const newUserMessage = { role: 'user', content: messageText };
    setMessages((prev) => [...prev, newUserMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: messageText })
      });

      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      if (data.session_id) setSessionId(data.session_id);

      setIsLoading(false);
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      const fullText = data.reply;
      let currentIndex = 0;
      const typingInterval = setInterval(() => {
        if (currentIndex < fullText.length) {
          setMessages((prev) => {
            const newMessages = [...prev];
            const nextChars = fullText.substring(currentIndex, currentIndex + 2);
            newMessages[newMessages.length - 1] = {
              role: 'assistant',
              content: newMessages[newMessages.length - 1].content + nextChars
            };
            return newMessages;
          });
          currentIndex += 2;
        } else {
          clearInterval(typingInterval);
          fetchSessions(); // Update sidebar with new title
        }
      }, 10);

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

        <button className="new-chat-btn" onClick={startNewChat}>
          <IconPlus size={14} /> New conversation
        </button>

        <div className="section-label">Recent</div>
        
        {/* DYNAMIC CHAT LIST */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {chatSessions.map((chat) => (
            <div 
              key={chat.id} 
              className={`chat-item ${sessionId === chat.id ? 'active' : ''}`}
              onClick={() => loadChat(chat.id)}
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                <IconMessage2 size={13} style={{ marginRight: '6px', flexShrink: 0 }} />
                {chat.title}
              </span>
              <IconTrash 
                size={14} 
                style={{ marginLeft: '8px', opacity: 0.5, cursor: 'pointer', flexShrink: 0 }} 
                onClick={(e) => deleteChat(e, chat.id)}
              />
            </div>
          ))}
        </div>

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
                
                {index === 0 && msg.role === 'assistant' && sessionId === null && (
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