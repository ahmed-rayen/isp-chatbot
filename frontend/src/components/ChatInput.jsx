'use client';
import { IconSend } from '@tabler/icons-react';

export default function ChatInput({ value, onChange, onSend, disabled }) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="input-area">
      <div className="input-row">
        <input
          type="text"
          placeholder="Describe your issue..."
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />
        <button className="send-btn" onClick={onSend} disabled={disabled}>
          <IconSend size={15} />
        </button>
      </div>
    </div>
  );
}