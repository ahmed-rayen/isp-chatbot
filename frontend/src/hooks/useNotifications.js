'use client';
import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../lib/api';

export function useNotifications(pollInterval = 20000) {
  const [notifications, setNotifications] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await apiFetch('/notifications');
      if (res.ok) {
        const data = await res.json();
        setNotifications(data || []);
      }
    } catch (e) {
      console.error('Failed to load notifications', e.message);
    }
  }, []);

  const markAsRead = useCallback(async (id) => {
    try {
      await apiFetch(`/notifications/${id}/read`, { method: 'PATCH' });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (e) {
      console.error('Failed to mark notification as read', e.message);
    }
  }, []);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  useEffect(() => {
    fetchNotifications();
    const intervalId = setInterval(fetchNotifications, pollInterval);
    return () => clearInterval(intervalId);
  }, [fetchNotifications, pollInterval]);

  return { notifications, showDropdown, setShowDropdown, unreadCount, markAsRead };
}