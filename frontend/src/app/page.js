'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import { 
  IconWifi, 
  IconPlus, 
  IconRobot, 
  IconSend, 
  IconTrash, 
  IconMessage2, 
  IconLogout, 
  IconTicket, 
  IconShield, 
  IconAlertTriangle, 
  IconBell
} from '@tabler/icons-react';
import Link from 'next/link';

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hello! I'm NetAssist, your technical support AI. How can I help you today?" }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [chatSessions, setChatSessions] = useState([]);
  
  // User states
  const [userName, setUserName] = useState('');
  const [userAccount, setUserAccount] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);
  
  // Active Outages Alert Banner State
  const [activeOutages, setActiveOutages] = useState([]);

  // Notification States
  const [notifications, setNotifications] = useState([]);
  const [showNotifs, setShowNotifs] = useState(false);
  
  const messagesEndRef = useRef(null);

  // Fallback to localhost if env var is missing
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auth Check, Fetch Sessions, Active Regional Outages & Notifications on mount
  useEffect(() => {
    const token = sessionStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }
    
    // Load user info for the sidebar
    setUserName(sessionStorage.getItem('user_name') || 'User');
    setUserAccount(sessionStorage.getItem('user_account') || '0000');
    setIsAdmin(sessionStorage.getItem('is_admin') === 'true');
    
    fetchSessions(token);

    // Fetch active local outages if any are currently impacting regional nodes
    const fetchOutages = async () => {
      try {
        const res = await fetch(`${API_BASE}/outages/active`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          setActiveOutages(await res.json());
        }
      } catch (e) { console.error("Failed to load outages"); }
    };

    // Fetch User Notifications
    const fetchNotifs = async () => {
      try {
        const res = await fetch(`${API_BASE}/notifications`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) setNotifications(await res.json());
      } catch (e) { console.error("Failed to load notifications"); }
    };

    fetchOutages();
    fetchNotifs();
  }, [router]);

  // Handle Mark Read
  const handleMarkRead = async (id) => {
    await fetch(`${API_BASE}/notifications/${id}/read`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` }
    });
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
  };

  const fetchSessions = async (customToken = null) => {
    const token = customToken || sessionStorage.getItem('access_token');
    if (!token) return router.push('/login');
    
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 401) { router.push('/login'); return; }
      
      const data = await res.json();
      
      // SAFETY CHECK: Only set state if it's an array!
      if (Array.isArray(data)) {
        setChatSessions(data);
      } else {
        setChatSessions([]);
      }
    } catch (e) { 
      console.error("Failed to load sessions"); 
    }
  };

  const startNewChat = async () => {
    if (sessionId) {
      try {
        const token = sessionStorage.getItem('access_token');
        await fetch(`${API_BASE}/sessions/${sessionId}/summarize`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      } catch (e) { console.error("Failed to summarize previous chat"); }
    }

    setSessionId(null);
    setMessages([{ role: 'assistant', content: "Hello! I'm NetAssist, your technical support AI. How can I help you today?" }]);
  };

  const loadChat = async (id) => {
    const token = sessionStorage.getItem('access_token');
    if (!token) return router.push('/login');
    
    try {
      const res = await fetch(`${API_BASE}/sessions/${id}/messages`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 401) { router.push('/login'); return; }
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
    e.stopPropagation();
    const token = sessionStorage.getItem('access_token');
    if (!token) return router.push('/login');
    
    try {
      await fetch(`${API_BASE}/sessions/${id}`, { 
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
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
      const token = sessionStorage.getItem('access_token');
      if (!token) return router.push('/login');

      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ session_id: sessionId, message: messageText })
      });

      if (response.status === 429) {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: "Too many messages. Please wait a moment before sending another."
        }]);
        setIsLoading(false);
        return;
      }

      if (response.status === 401) { 
        router.push('/login'); 
        return; 
      }

      if (!response.ok) throw new Error('Network response was not ok');
      
      const data = await response.json();
      if (data.session_id) setSessionId(data.session_id);

      setIsLoading(false);
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);
      
      const fullText = data.reply;
      let currentIndex = 0;
      let typedText = "";
      
      const typingInterval = setInterval(() => {
        if (currentIndex < fullText.length) {
          typedText += fullText.substring(currentIndex, currentIndex + 2);
          currentIndex += 2;
          
          setMessages((prev) => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = {
              role: 'assistant',
              content: typedText
            };
            return newMessages;
          });
        } else {
          clearInterval(typingInterval);
          fetchSessions();
        }
      }, 15);

    } catch (error) {
      console.error('Error:', error);
      setIsLoading(false);
      setMessages((prev) => [...prev, { role: 'assistant', content: "Sorry, I'm having trouble connecting to the server." }]);
    }
  };

  const handleLogout = () => {
    sessionStorage.clear();
    router.push('/login');
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
        
        {/* Navigation Wrapper */}
        <div className="sidebar-nav" style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '12px' }}>
          {/* My Tickets Link */}
          <Link 
            href="/tickets" 
            className="new-chat-btn" 
            style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', justifyContent: 'flex-start' }}
          >
            <IconTicket size={14} /> My Tickets
          </Link>

          {/* Admin Dashboard Link */}
          {isAdmin && (
            <Link 
              href="/admin" 
              className="new-chat-btn" 
              style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', justifyContent: 'flex-start' }}
            >
              <IconShield size={14} /> Admin Dashboard
            </Link>
          )}
        </div>

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
          <div className="user-row" style={{ justifyContent: 'space-between', width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div className="avatar">{userName.charAt(0) || 'U'}</div>
              <div>
                <div className="user-name">{userName}</div>
                <div className="user-role">Client #{userAccount}</div>
              </div>
            </div>
            <button onClick={handleLogout} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#888', padding: '4px' }} title="Logout">
              <IconLogout size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* CHAT AREA */}
      <div className="chat-area">
        {/* DYNAMIC UPDATED HEADER WITH DROPDOWN PANEL */}
        <div className="chat-header" style={{ position: 'relative' }}>
          <div className="chat-title">Technical Support</div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Notification Bell */}
            <div style={{ position: 'relative' }}>
              <button 
                onClick={() => setShowNotifs(!showNotifs)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', position: 'relative' }}
              >
                <IconBell size={20} color="#1A1A1A" />
                {notifications.filter(n => !n.is_read).length > 0 && (
                  <span style={{
                    position: 'absolute', top: '-2px', right: '-2px', width: '8px', height: '8px',
                    borderRadius: '50%', background: '#FF6B00', border: '1px solid #fff'
                  }}></span>
                )}
              </button>
              
              {/* Dropdown Box Container */}
              {showNotifs && (
                <div style={{
                  position: 'absolute', top: '30px', right: '0', width: '300px',
                  background: '#fff', borderRadius: '12px', boxShadow: '0 10px 30px rgba(0,0,0,0.1)',
                  border: '0.5px solid #E8E8E8', zIndex: 100, overflow: 'hidden'
                }}>
                  <div style={{ padding: '12px 16px', borderBottom: '0.5px solid #E8E8E8', fontWeight: 600 }}>
                    Notifications
                  </div>
                  <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                    {notifications.length === 0 ? (
                      <p style={{ padding: '16px', fontSize: '13px', color: '#888', textAlign: 'center' }}>No notifications</p>
                    ) : (
                      notifications.map(n => (
                        <div 
                          key={n.id} 
                          onClick={() => !n.is_read && handleMarkRead(n.id)}
                          style={{ 
                            padding: '12px 16px', 
                            borderBottom: '0.5px solid #F7F7F7', 
                            cursor: n.is_read ? 'default' : 'pointer',
                            background: n.is_read ? '#fff' : '#FFF3EB'
                          }}
                        >
                          <p style={{ fontSize: '13px', color: '#1A1A1A', marginBottom: '4px' }}>{n.message}</p>
                          <span style={{ fontSize: '11px', color: '#AAA' }}>{n.time}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="status-pill"><div className="dot"></div> Online</div>
          </div>
        </div>

        {/* OUTAGE ALERT BANNER CONTAINER */}
        {activeOutages.length > 0 && (
          <div style={{ 
            margin: '16px 20px 0', 
            padding: '12px 16px', 
            background: '#FFF3EB', 
            border: '1px solid #FF6B00', 
            borderRadius: '12px', 
            display: 'flex', 
            alignItems: 'flex-start', 
            gap: '12px' 
          }}>
            <IconAlertTriangle size={20} color="#FF6B00" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#1A1A1A', marginBottom: '4px' }}>Active Outages in Your Area</h4>
              {activeOutages.map(o => (
                <p key={o.city} style={{ fontSize: '13px', color: '#555', margin: '4px 0 0' }}>
                  <strong style={{ textTransform: 'capitalize' }}>{o.city}:</strong> {o.status}
                </p>
              ))}
            </div>
          </div>
        )}

        <div className="messages">
          {messages.map((msg, index) => (
            <div key={index} className={`msg ${msg.role === 'user' ? 'user' : ''}`}>
              <div className={`msg-avatar ${msg.role === 'user' ? 'user-avatar-msg' : 'bot-avatar'}`}>
                {msg.role === 'user' ? (userName.charAt(0) || 'U') : <IconRobot size={13} />}
              </div>
              <div>
                <div className={`bubble ${msg.role === 'user' ? 'user-bubble' : 'bot-bubble'}`}>
                  {msg.role === 'user' ? (
                    msg.content
                  ) : (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  )}
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