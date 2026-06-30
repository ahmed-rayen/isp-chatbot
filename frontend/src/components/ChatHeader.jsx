'use client';
import NotificationDropdown from './NotificationDropdown';

export default function ChatHeader({ notifications, showNotifs, setShowNotifs, onMarkRead }) {
  return (
    <div className="chat-header" style={{ position: 'relative' }}>
      <div className="chat-title">Technical Support</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <NotificationDropdown
          notifications={notifications}
          showDropdown={showNotifs}
          onToggle={() => setShowNotifs(!showNotifs)}
          onMarkRead={onMarkRead}
        />
        <div className="status-pill"><div className="dot"></div> Online</div>
      </div>
    </div>
  );
}