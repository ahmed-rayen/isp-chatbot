'use client';
import { IconStar } from '@tabler/icons-react';

export default function FeedbackModal({ ticketId, rating, onSetRating, comment, onSetComment, onSubmit }) {
  if (!ticketId) return null;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000,
    }}>
      <div style={{ background: '#fff', padding: 32, borderRadius: 16, width: 400, textAlign: 'center' }}>
        <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>Rate your experience</h3>
        <p style={{ fontSize: 14, color: '#888', marginBottom: 24 }}>
          How satisfied were you with the support for ticket {ticketId}?
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginBottom: 24 }}>
          {[1, 2, 3, 4, 5].map(i => (
            <button key={i} onClick={() => onSetRating(i)} style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}>
              <IconStar size={32} color={i <= rating ? '#FF6B00' : '#E0E0E0'} fill={i <= rating ? '#FF6B00' : 'none'} />
            </button>
          ))}
        </div>

        <textarea
          placeholder="Optional comment..."
          value={comment}
          onChange={e => onSetComment(e.target.value)}
          style={{
            width: '100%', padding: 12, marginBottom: 24, border: '0.5px solid #E0E0E0',
            borderRadius: 8, minHeight: 80, resize: 'none', boxSizing: 'border-box',
          }}
        />

        <button
          onClick={onSubmit}
          style={{
            width: '100%', padding: 12, background: '#FF6B00', color: '#fff',
            border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 500,
          }}
        >
          Submit Feedback
        </button>
      </div>
    </div>
  );
}