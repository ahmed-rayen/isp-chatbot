'use client';
import { useState, useEffect } from 'react';
import { apiFetch } from '../lib/api';

import { useAuth } from '../hooks/useAuth';
import { useChat } from '../hooks/useChat';
import { useSessions } from '../hooks/useSessions';
import { useNotifications } from '../hooks/useNotifications';
import { useFeedback } from '../hooks/useFeedback';

import Sidebar from '../components/Sidebar';
import ChatHeader from '../components/ChatHeader';
import OutageBanner from '../components/OutageBanner';
import MessageList from '../components/MessageList';
import ChatInput from '../components/ChatInput';
import FeedbackModal from '../components/FeedbackModal';

export default function ChatPage() {
  const user = useAuth();
  const { sessions, fetchSessions, deleteSession, loadSessionMessages } = useSessions();
  const { messages, input, setInput, isLoading, sessionId, resetChat, startNewChat, setSessionId, sendMessage, restoreSession} = useChat(fetchSessions);
  const { notifications, showDropdown: showNotifs, setShowDropdown: setShowNotifs, markAsRead } = useNotifications();
  const { pendingFeedback, rating, setRating, comment, setComment, submitFeedback } = useFeedback();

  // Fetch outages on mount
  const [outages, setOutages] = useState([]);
  useEffect(() => {
    const fetchOutages = async () => {
      try {
        const res = await apiFetch('/outages/active');
        if (res.ok) setOutages((await res.json()) || []);
      } catch (e) { console.error('Failed to load outages', e.message); }
    };
    fetchOutages();
  }, []);

  const handleNewChat = () => startNewChat(sessionId);
   const handleLoadChat = async (id) => {
    const data = await loadSessionMessages(id);
    if (data && data.length > 0) {
      restoreSession(id, data); // Actually loads the old messages into the UI
    } else {
      resetChat();
      setSessionId(id);
    }
  };

  const handleDeleteChat = (id) => deleteSession(id, sessionId, resetChat);

  if (!user.isAuthenticated) return null;

  return (
    <div className="app">
      <Sidebar
        user={user}
        sessions={sessions}
        activeSessionId={sessionId}
        onLoadChat={handleLoadChat}
        onDeleteChat={handleDeleteChat}
        onNewChat={handleNewChat}
        onLogout={user.logout}
      />
      <div className="chat-area">
        <ChatHeader notifications={notifications} showNotifs={showNotifs} setShowNotifs={setShowNotifs} onMarkRead={markAsRead} />
        <OutageBanner outages={outages} />
        <MessageList messages={messages} isLoading={isLoading} userName={user.name} sessionId={sessionId} onSend={sendMessage} />
        <ChatInput value={input} onChange={setInput} onSend={sendMessage} disabled={isLoading} />
      </div>
      <FeedbackModal
        ticketId={pendingFeedback?.ticket_id}
        rating={rating}
        onSetRating={setRating}
        comment={comment}
        onSetComment={setComment}
        onSubmit={submitFeedback}
      />
    </div>
  );
}