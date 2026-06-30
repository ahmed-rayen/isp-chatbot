'use client';
import { useEffect, useRef } from 'react';
import { IconRobot } from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';

function MessageBubble({ message, userName, isFirstAssistant, sessionId, onQuickChip }) {
  const isUser = message.role === 'user';

  return (
    <div className={`msg ${isUser ? 'user' : ''}`}>
      <div className={`msg-avatar ${isUser ? 'user-avatar-msg' : 'bot-avatar'}`}>
        {isUser ? (userName.charAt(0) || 'U') : <IconRobot size={13} />}
      </div>
      <div>
        <div className={`bubble ${isUser ? 'user-bubble' : 'bot-bubble'}`}>
          {isUser ? message.content : <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{message.content}</ReactMarkdown>}
        </div>
        {isFirstAssistant && sessionId === null && (
          <div className="quick-chips">
            {['Internet not working', 'Slow connection', 'Router help', 'Check my plan'].map(text => (
              <div key={text} className="chip" onClick={() => onQuickChip(text)}>{text}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MessageList({ messages, isLoading, userName, sessionId, onSend }) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="messages">
      {messages.map((msg, index) => (
        <MessageBubble
          key={index}
          message={msg}
          userName={userName}
          isFirstAssistant={index === 0 && msg.role === 'assistant'}
          sessionId={sessionId}
          onQuickChip={onSend}
        />
      ))}

      {isLoading && (
        <div className="msg">
          <div className="msg-avatar bot-avatar"><IconRobot size={13} /></div>
          <div className="typing"><span></span><span></span><span></span></div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}