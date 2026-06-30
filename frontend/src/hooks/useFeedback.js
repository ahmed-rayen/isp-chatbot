'use client';
import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../lib/api';

export function useFeedback(pollInterval = 20000) {
  const [pendingFeedback, setPendingFeedback] = useState(null);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');

  const checkForFeedback = useCallback(async () => {
    if (pendingFeedback) return; // Already showing a modal

    try {
      const tRes = await apiFetch('/tickets');
      if (!tRes.ok) return;
      const tickets = await tRes.json();
      if (!Array.isArray(tickets)) return;

      for (const ticket of tickets.filter(t => t.status === 'resolved')) {
        const fRes = await apiFetch(`/tickets/${ticket.id}/needs-feedback`);
        if (!fRes.ok) continue;
        const fData = await fRes.json();
        if (fData?.needs_feedback) {
          setPendingFeedback({ ticket_id: ticket.id, session_id: ticket.session_id || null });
          break;
        }
      }
    } catch (e) {
      console.error('Failed to run feedback check', e.message);
    }
  }, [pendingFeedback]);

  const submitFeedback = useCallback(async () => {
    if (!pendingFeedback || rating === 0) return;

    try {
      await apiFetch('/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: pendingFeedback.session_id,
          ticket_id: pendingFeedback.ticket_id,
          rating,
          comment,
        }),
      });
    } catch (e) {
      console.error('Failed to submit feedback', e.message);
    } finally {
      setPendingFeedback(null);
      setRating(0);
      setComment('');
    }
  }, [pendingFeedback, rating, comment]);

  useEffect(() => {
    checkForFeedback();
    const intervalId = setInterval(checkForFeedback, pollInterval);
    return () => clearInterval(intervalId);
  }, [checkForFeedback, pollInterval]);

  return { pendingFeedback, rating, setRating, comment, setComment, submitFeedback };
}