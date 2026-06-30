'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch } from '../lib/api';

const INITIAL_MESSAGE = { role: 'assistant', content: "Hello! I'm NetAssist, your technical support AI. How can I help you today?" };

export function useChat(fetchSessions) {
  const router = useRouter();
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const typingRef = useRef(null);

  const clearTypingInterval = () => {
    if (typingRef.current) {
      clearInterval(typingRef.current);
      typingRef.current = null;
    }
  };

  useEffect(() => {
    return clearTypingInterval;
  }, []);

  const resetChat = useCallback(() => {
    clearTypingInterval();
    setMessages([INITIAL_MESSAGE]);
    setSessionId(null);
  }, []);
    const restoreSession = useCallback((id, loadedMessages) => {
    clearTypingInterval();
    setMessages(loadedMessages);
    setSessionId(id);
  }, []);

  const startNewChat = useCallback(async (currentSessionId) => {
    if (currentSessionId) {
      await apiFetch(`/sessions/${currentSessionId}/summarize`, { method: 'POST' });
    }
    resetChat();
  }, [resetChat]);

  const loadChat = useCallback(async (id) => {
    clearTypingInterval();
    // Would need to pass loadSessionMessages here or accept messages as param
    resetChat();
    setSessionId(id);
  }, [resetChat]);

  const sendMessage = useCallback(async (textToSend) => {
    const messageText = textToSend || input;
    if (!messageText.trim() || isLoading) return;

    clearTypingInterval();
    const newUserMessage = { role: 'user', content: messageText };
    setMessages(prev => [...prev, newUserMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await apiFetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: messageText }),
      });

      if (response.status === 429) {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Too many messages. Please wait a moment before sending another.' }]);
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
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      const fullText = data.reply || '';
      let currentIndex = 0;
      let typedText = '';

      typingRef.current = setInterval(() => {
        if (currentIndex < fullText.length) {
          typedText += fullText.substring(currentIndex, currentIndex + 2);
          currentIndex += 2;
          setMessages(prev => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = { role: 'assistant', content: typedText };
            return newMessages;
          });
        } else {
          clearTypingInterval();
          fetchSessions?.();
        }
      }, 15);

    } catch (error) {
      console.error('Error sending message:', error);
      setIsLoading(false);
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I'm having trouble connecting to the server." }]);
    }
  }, [input, isLoading, sessionId, router, fetchSessions]);

  return {
    messages,
    input,
    setInput,
    isLoading,
    sessionId,
    setSessionId,
    resetChat,
    restoreSession,
    startNewChat,
    loadChat,
    sendMessage,
  };
}