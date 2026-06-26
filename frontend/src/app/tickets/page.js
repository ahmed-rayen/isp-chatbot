'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { IconWifi, IconArrowLeft, IconClock, IconUser, IconSend } from '@tabler/icons-react';
import { apiFetch } from '../lib/api';

export default function TicketsPage() {
  const router = useRouter();
  const [tickets, setTickets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedTicket, setExpandedTicket] = useState(null);
  const [comments, setComments] = useState({});
  const [newComment, setNewComment] = useState('');

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

  useEffect(() => {
    const token = sessionStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }
    
    const fetchTickets = async () => {
      try {
        const res = await apiFetch(`${API_BASE}/tickets`);
        if (res.status === 401) { router.push('/login'); return; }
        const data = await res.json();
        setTickets(data);
      } catch (e) { console.error("Failed to load tickets:", e.message); }
      finally { setIsLoading(false); }
    };
    
    fetchTickets();
  }, [router, API_BASE]);

  const fetchComments = async (ticketId) => {
    try {
      const res = await apiFetch(`${API_BASE}/tickets/${ticketId}/comments`);
      if (res.ok) {
        const data = await res.json();
        setComments(prev => ({ ...prev, [ticketId]: data }));
      }
    } catch (e) {}
  };

  const handleAddComment = async (ticketId) => {
    if (!newComment.trim()) return;
    try {
      await apiFetch(`${API_BASE}/tickets/${ticketId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newComment })
      });
      setNewComment('');
      fetchComments(ticketId);
    } catch (e) { console.error("Failed to send message"); }
  };

  return (
    <div style={{ background: '#f0f2f5', minHeight: '100vh', padding: '40px' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px' }}>
          <Link href="/" style={{ color: '#888' }}>
            <IconArrowLeft size={24} />
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: '#FF6B00', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <IconWifi size={18} color="#fff" />
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: 600, color: '#1A1A1A' }}>My Support Tickets</h1>
          </div>
        </div>

        {!isLoading && (
          <div style={{ background: '#fff', padding: '16px 24px', borderRadius: '12px', marginBottom: '24px', border: '0.5px solid #E8E8E8', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '14px', color: '#555' }}>Total Tickets</span>
            <span style={{ fontSize: '24px', fontWeight: 700, color: '#FF6B00' }}>{tickets.length}</span>
          </div>
        )}

        {isLoading ? (
          <p style={{ textAlign: 'center', color: '#888' }}>Loading tickets...</p>
        ) : tickets.length === 0 ? (
          <div style={{ background: '#fff', padding: '40px', borderRadius: '16px', textAlign: 'center', border: '0.5px solid #E8E8E8' }}>
            <p style={{ color: '#888' }}>You have no support tickets yet.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {tickets.map(ticket => (
              <div key={ticket.id} style={{ background: '#fff', borderRadius: '16px', border: '0.5px solid #E8E8E8', overflow: 'hidden' }}>
                
                {/* Ticket Header (Click to expand) */}
                <div 
                  style={{ padding: '24px', cursor: 'pointer' }}
                  onClick={() => {
                    const newExpanded = expandedTicket === ticket.id ? null : ticket.id;
                    setExpandedTicket(newExpanded);
                    if (newExpanded) fetchComments(ticket.id);
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#FF6B00' }}>{ticket.id}</h2>
                    <span style={{ 
                      padding: '4px 12px', 
                      borderRadius: '20px', 
                      fontSize: '12px', 
                      fontWeight: 500,
                      background: ticket.status === 'open' ? '#FFF3EB' : '#E8F5E9',
                      color: ticket.status === 'open' ? '#FF6B00' : '#2E7D32'
                    }}>
                      {ticket.status}
                    </span>
                  </div>
                  <p style={{ fontSize: '14px', color: '#1A1A1A', marginBottom: '16px' }}>{ticket.issue}</p>
                  
                  {ticket.technician ? (
                    <div style={{ display: 'flex', gap: '24px', paddingTop: '16px', borderTop: '0.5px solid #E8E8E8' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <IconUser size={16} color="#888" />
                        <span style={{ fontSize: '13px', color: '#555' }}>{ticket.technician}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <IconClock size={16} color="#888" />
                        <span style={{ fontSize: '13px', color: '#555' }}>{ticket.visit_date} ({ticket.visit_slot})</span>
                      </div>
                    </div>
                  ) : (
                    <div style={{ paddingTop: '16px', borderTop: '0.5px solid #E8E8E8' }}>
                      <span style={{ fontSize: '13px', color: '#888' }}>Created on {ticket.date}</span>
                    </div>
                  )}
                </div>

                {/* Expanded Chat View */}
                {expandedTicket === ticket.id && (
                  <div style={{ borderTop: '0.5px solid #E8E8E8', padding: '20px', background: '#FAFAFA' }}>
                    <div style={{ background: '#F7F7F7', borderRadius: '8px', padding: '12px', marginBottom: '12px', maxHeight: '250px', overflowY: 'auto' }}>
                      {comments[ticket.id]?.length === 0 || !comments[ticket.id] ? (
                        <p style={{ fontSize: '13px', color: '#888', textAlign: 'center' }}>No messages yet. Say hello to your technician!</p>
                      ) : (
                        comments[ticket.id]?.map((c, i) => (
                          <div key={i} style={{ marginBottom: '8px', padding: '10px', background: '#fff', borderRadius: '8px', border: '0.5px solid #E8E8E8' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <span style={{ fontSize: '12px', fontWeight: 600, color: c.sender_role === 'Technician' ? '#FF6B00' : '#1A1A1A' }}>{c.sender_name}</span>
                              <span style={{ fontSize: '11px', color: '#AAA' }}>{c.time}</span>
                            </div>
                            <p style={{ fontSize: '13px', color: '#333' }}>{c.content}</p>
                          </div>
                        ))
                      )}
                    </div>
                    
                    {/* Chat Input */}
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input 
                        type="text" 
                        placeholder="Type a message..." 
                        value={newComment} 
                        onChange={(e) => setNewComment(e.target.value)}
                        style={{ flex: 1, padding: '12px', fontSize: '14px', border: '0.5px solid #E0E0E0', borderRadius: '8px' }}
                      />
                      <button 
                        onClick={() => handleAddComment(ticket.id)}
                        style={{ padding: '12px', background: '#FF6B00', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
                      >
                        <IconSend size={16} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}