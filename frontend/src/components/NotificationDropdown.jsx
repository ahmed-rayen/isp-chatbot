'use client';
import { IconBell } from '@tabler/icons-react';

export default function NotificationDropdown({ notifications, showDropdown, onToggle, onMarkRead }) {
  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div style={{ position: 'relative' }}>
      <button onClick={onToggle} style={{ background: 'transparent', border: 'none', cursor: 'pointer', position: 'relative' }}>
        <IconBell size={20} color="#1A1A1A" />
        {unreadCount > 0 && (
          <span style={{ position: 'absolute', top: -2, right: -2, width: 8, height: 8, borderRadius: '50%', background: '#FF6B00', border: '1px solid #fff' }} />
        )}
      </button>

      {showDropdown && (
        <div style={{
          position: 'absolute', top: 30, right: 0, width: 300,
          background: '#fff', borderRadius: 12, boxShadow: '0 10px 30px rgba(0,0,0,0.1)',
          border: '0.5px solid #E8E8E8', zIndex: 100, overflow: 'hidden',
        }}>
          <div style={{ padding: '12px 16px', borderBottom: '0.5px solid #E8E8E8', fontWeight: 600 }}>Notifications</div>
          <div style={{ maxHeight: 300, overflowY: 'auto' }}>
            {notifications.length === 0 ? (
              <p style={{ padding: 16, fontSize: 13, color: '#888', textAlign: 'center' }}>No notifications</p>
            ) : (
              notifications.map(n => (
                <div
                  key={n.id}
                  onClick={() => !n.is_read && onMarkRead(n.id)}
                  style={{
                    padding: '12px 16px', borderBottom: '0.5px solid #F7F7F7',
                    cursor: n.is_read ? 'default' : 'pointer',
                    background: n.is_read ? '#fff' : '#FFF3EB',
                  }}
                >
                  <p style={{ fontSize: 13, color: '#1A1A1A', marginBottom: 4 }}>{n.message}</p>
                  <span style={{ fontSize: 11, color: '#AAA' }}>{n.time}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}