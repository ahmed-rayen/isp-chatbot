'use client';
import { useState, useCallback } from 'react';
import { apiFetch } from '../lib/api';

export function useSessions() {
  const [sessions, setSessions] = useState([]);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await apiFetch('/sessions');
      if (!res.ok) return;
      const data = await res.json();
      setSessions(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Failed to load sessions', e.message);
    }
  }, []);

  const deleteSession = useCallback(async (id, currentSessionId, onDeleted) => {
    try {
      await apiFetch(`/sessions/${id}`, { method: 'DELETE' });
      if (id === currentSessionId) onDeleted();
      fetchSessions();
    } catch (e) {
      console.error('Failed to delete session', e.message);
    }
  }, [fetchSessions]);

  const summarizeSession = useCallback(async (id) => {
    try {
      await apiFetch(`/sessions/${id}/summarize`, { method: 'POST' });
    } catch (e) {
      console.error('Failed to summarize session', e.message);
    }
  }, []);

  const loadSessionMessages = useCallback(async (id) => {
    try {
      const res = await apiFetch(`/sessions/${id}/messages`);
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      console.error('Failed to load chat', e.message);
      return null;
    }
  }, []);

  return { sessions, fetchSessions, deleteSession, summarizeSession, loadSessionMessages };
}