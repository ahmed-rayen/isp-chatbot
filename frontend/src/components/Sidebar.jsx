'use client';
import Link from 'next/link';
import { IconWifi, IconTicket, IconTools, IconShield, IconMessage2, IconTrash, IconLogout } from '@tabler/icons-react';

export default function Sidebar({
  user,
  sessions,
  activeSessionId,
  onLoadChat,
  onDeleteChat,
  onNewChat,
  onLogout,
}) {
  return (
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

      <button className="new-chat-btn" onClick={onNewChat}>
        <IconWifi size={14} /> New Chat
      </button>

      <div className="sidebar-nav">
        <Link href="/tickets" className="new-chat-btn">
          <IconTicket size={14} /> My Tickets
        </Link>
        {user.isTech && (
          <Link href="/technician" className="new-chat-btn">
            <IconTools size={14} /> Technician Dashboard
          </Link>
        )}
        {user.isAdmin && (
          <Link href="/admin" className="new-chat-btn">
            <IconShield size={14} /> Admin Dashboard
          </Link>
        )}
      </div>

      <div className="section-label">Recent</div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {sessions.map(chat => (
          <div
            key={chat.id}
            className={`chat-item ${activeSessionId === chat.id ? 'active' : ''}`}
            onClick={() => onLoadChat(chat.id)}
          >
            <span>
              <IconMessage2 size={13} style={{ marginRight: 6, flexShrink: 0 }} />
              {chat.title}
            </span>
            <IconTrash
              size={14}
              style={{ marginLeft: 8, opacity: 0.5, cursor: 'pointer', flexShrink: 0 }}
              onClick={e => { e.stopPropagation(); onDeleteChat(chat.id); }}
            />
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className="user-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="avatar">{user.name.charAt(0) || 'U'}</div>
            <div>
              <div className="user-name">{user.name}</div>
              <div className="user-role">Client #{user.account}</div>
            </div>
          </div>
          <button onClick={onLogout} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#888', padding: 4 }} title="Logout">
            <IconLogout size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}