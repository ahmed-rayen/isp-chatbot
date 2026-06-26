'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  IconArrowLeft, 
  IconTools, 
  IconMapPin, 
  IconCheck, 
  IconChevronDown, 
  IconChevronUp, 
  IconSend 
} from '@tabler/icons-react';
import { apiFetch } from '../lib/api';

export default function TechnicianDashboard() {
  const router = useRouter();
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState({ resolved: 0, upcoming: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [isTech, setIsTech] = useState(false);

  // Accordion and Chat Thread States
  const [expandedTicket, setExpandedTicket] = useState(null);
  const [comments, setComments] = useState({});
  const [newComment, setNewComment] = useState('');
  const wsRef = useRef(null); // WebSocket reference

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
  const WS_BASE = API_BASE.replace('http', 'ws').replace('/api', ''); // e.g., ws://localhost:8000

  // Extracted core data hydration logic to prevent stale state issues
  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [tRes, sRes] = await Promise.all([
        apiFetch(`${API_BASE}/technician/tickets`),
        apiFetch(`${API_BASE}/technician/stats`)
      ]);
      
      if (tRes.ok) setTickets(await tRes.json());
      if (sRes.ok) setStats(await sRes.json());
    } catch (e) { 
      console.error("Failed to load tech data", e); 
    } finally { 
      setIsLoading(false); 
    }
  }, [API_BASE]);

  // CRIT-004 FIX: Verify technician privileges directly from server payload
  useEffect(() => {
    const token = sessionStorage.getItem('access_token');
    if (!token) { router.push('/login'); return; }
    
    const verifyTechnician = async () => {
      try {
        const res = await apiFetch(`${API_BASE}/auth/me`);
        if (!res.ok) { router.push('/login'); return; }
        
        const user = await res.json();
        if (!user.is_technician) { router.push('/'); return; }
        
        setIsTech(true);
        fetchData();
      } catch (e) {
        router.push('/login');
      }
    };

    verifyTechnician();
  }, [router, API_BASE, fetchData]);

  // WEBSOCKET LOGIC: Connect when ticket expanded, disconnect when collapsed
  useEffect(() => {
    if (!expandedTicket) return;
    
    const token = sessionStorage.getItem('access_token');
    const ws = new WebSocket(`${WS_BASE}/api/ws/tickets/${expandedTicket}?token=${token}`);
    wsRef.current = ws;
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setComments(prev => ({
        ...prev,
        [expandedTicket]: [...(prev[expandedTicket] || []), data]
      }));
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [expandedTicket, WS_BASE]);

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
    const tempComment = newComment;
    setNewComment(''); // Clear input immediately for UX
    
    try {
      // Send via REST. Backend will save it and broadcast it over WS.
      await apiFetch(`${API_BASE}/tickets/${ticketId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: tempComment })
      });
      // No need to fetchComments, the WebSocket will push the saved message automatically
    } catch (e) { console.error("Failed to send message"); }
  };

  const handleKeyDown = (e, ticketId) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddComment(ticketId);
    }
  };

  const handleResolve = async (ticketId) => {
    try {
      await apiFetch(`${API_BASE}/technician/tickets/${ticketId}/resolve`, { method: 'PATCH' });
      setTickets(prev => prev.map(t => t.ticket_id === ticketId ? { ...t, status: 'resolved' } : t));
      setStats(prev => ({ ...prev, resolved: prev.resolved + 1 }));
    } catch (e) { console.error("Failed to resolve"); }
  };

  if (!isTech) return null;

  return (
    <div style={{ background: '#f0f2f5', minHeight: '100vh', padding: '40px' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        {/* Header Section */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px' }}>
          <Link href="/" style={{ color: '#888' }}><IconArrowLeft size={24} /></Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: '#1A1A1A', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <IconTools size={18} color="#FF6B00" />
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: 600, color: '#1A1A1A' }}>Technician Dashboard</h1>
          </div>
        </div>

        {/* Stats Cards */}
        {!isLoading && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: '#1A1A1A', padding: '20px', borderRadius: '12px' }}>
              <span style={{ fontSize: '13px', color: '#AAA' }}>Upcoming Visits</span>
              <h2 style={{ fontSize: '28px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>{stats.upcoming}</h2>
            </div>
            <div style={{ background: '#1A1A1A', padding: '20px', borderRadius: '12px' }}>
              <span style={{ fontSize: '13px', color: '#AAA' }}>Resolved Tickets</span>
              <h2 style={{ fontSize: '28px', fontWeight: 700, color: '#FF6B00', marginTop: '4px' }}>{stats.resolved}</h2>
            </div>
          </div>
        )}

        {/* Visits Accordion List */}
        {isLoading ? (
          <p style={{ textAlign: 'center', color: '#888' }}>Loading schedule...</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {tickets.map(ticket => (
              <div key={ticket.ticket_id} style={{ background: '#fff', borderRadius: '12px', border: '0.5px solid #E8E8E8', overflow: 'hidden' }}>
                
                {/* Main Row Information (Clicking handles open/close) */}
                <div 
                  onClick={() => {
                    const newExpanded = expandedTicket === ticket.ticket_id ? null : ticket.ticket_id;
                    setExpandedTicket(newExpanded);
                    if (newExpanded) fetchComments(ticket.ticket_id);
                  }}
                  style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <span style={{ fontWeight: 700, color: '#1A1A1A' }}>{ticket.ticket_id}</span>
                      <span style={{ padding: '2px 8px', borderRadius: '12px', fontSize: '11px', background: ticket.status === 'resolved' ? '#E8F5E9' : '#FFF3EB', color: ticket.status === 'resolved' ? '#2E7D32' : '#FF6B00' }}>
                        {ticket.status}
                      </span>
                    </div>
                    <p style={{ fontSize: '14px', color: '#555', marginBottom: '8px' }}>{ticket.issue}</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '13px', color: '#888' }}>
                      <span>{ticket.visit_date} ({ticket.time_slot})</span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <IconMapPin size={14} /> {ticket.client_address}
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    {ticket.status !== 'resolved' && (
                      <button 
                        onClick={(e) => {
                          e.stopPropagation(); // Prevents collapsing the dashboard view on trigger
                          handleResolve(ticket.ticket_id);
                        }}
                        style={{ padding: '8px 16px', background: '#FF6B00', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        <IconCheck size={16} /> Mark Resolved
                      </button>
                    )}
                    {expandedTicket === ticket.ticket_id ? <IconChevronUp size={20} color="#888" /> : <IconChevronDown size={20} color="#888" />}
                  </div>
                </div>

                {/* Expanded Client Chat box */}
                {expandedTicket === ticket.ticket_id && (
                  <div style={{ borderTop: '0.5px solid #E8E8E8', padding: '20px', background: '#FAFAFA' }}>
                    <div style={{ background: '#F7F7F7', borderRadius: '8px', padding: '12px', marginBottom: '12px', maxHeight: '250px', overflowY: 'auto' }}>
                      {comments[ticket.ticket_id]?.length === 0 || !comments[ticket.ticket_id] ? (
                        <p style={{ fontSize: '13px', color: '#888', textAlign: 'center' }}>No messages yet. Send a status message to the client!</p>
                      ) : (
                        comments[ticket.ticket_id]?.map((c, i) => (
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
                    
                    {/* Input Field Form Control */}
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input 
                        type="text" 
                        placeholder="Type a response to your client..." 
                        value={newComment} 
                        onChange={(e) => setNewComment(e.target.value)}
                        onKeyDown={(e) => handleKeyDown(e, ticket.ticket_id)}
                        style={{ flex: 1, padding: '12px', fontSize: '14px', border: '0.5px solid #E0E0E0', borderRadius: '8px' }}
                      />
                      <button 
                        onClick={() => handleAddComment(ticket.ticket_id)}
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