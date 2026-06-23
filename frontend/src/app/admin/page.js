'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { IconArrowLeft, IconShield, IconHistory, IconChevronDown, IconChevronUp } from '@tabler/icons-react';

export default function AdminDashboard() {
  const router = useRouter();
  const [tickets, setTickets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedTicket, setExpandedTicket] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  
  // New States for Admin Actions
  const [technicians, setTechnicians] = useState([]);
  const [updateStatus, setUpdateStatus] = useState({});

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

  useEffect(() => {
    const token = sessionStorage.getItem('access_token');
    const adminFlag = sessionStorage.getItem('is_admin') === 'true';
    
    if (!token) { router.push('/login'); return; }
    if (!adminFlag) { router.push('/'); return; } // Kick out non-admins!
    
    setIsAdmin(true);
    
    const fetchAllTickets = async () => {
      try {
        const res = await fetch(`${API_BASE}/admin/tickets`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.status === 401 || res.status === 403) { router.push('/login'); return; }
        const data = await res.json();
        setTickets(data);
      } catch (e) { console.error("Failed to load admin tickets"); }
      finally { setIsLoading(false); }
    };

    // New fetch handler for loading available technicians
    const fetchTechs = async () => {
      try {
        const res = await fetch(`${API_BASE}/admin/technicians`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        setTechnicians(data);
      } catch (e) { console.error("Failed to load techs"); }
    };
    
    fetchAllTickets();
    fetchTechs();
  }, [router, API_BASE]);

  // Handler function to update ticket statuses
  const handleUpdateStatus = async (ticketId, newStatus) => {
    try {
      await fetch(`${API_BASE}/admin/tickets/${ticketId}`, {
        method: 'PATCH',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` 
        },
        body: JSON.stringify({ status: newStatus })
      });
      // Update local state reactively
      setTickets(prev => prev.map(t => t.id === ticketId ? { ...t, status: newStatus } : t));
    } catch (e) { console.error("Failed to update status"); }
  };

  // Handler function to reschedule or reassign visits
  const handleReschedule = async (ticketId, date, slot, techId) => {
    try {
      await fetch(`${API_BASE}/admin/visits/${ticketId}`, {
        method: 'PATCH',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` 
        },
        body: JSON.stringify({ scheduled_date: date, time_slot: slot, technician_id: techId })
      });
      alert("Visit updated!");
    } catch (e) { console.error("Failed to update visit"); }
  };

  // Hide UI until we confirm admin status
  if (!isAdmin) return null;

  return (
    <div style={{ background: '#f0f2f5', minHeight: '100vh', padding: '40px' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px' }}>
          <Link href="/" style={{ color: '#888' }}>
            <IconArrowLeft size={24} />
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: '#1A1A1A', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <IconShield size={18} color="#fff" />
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: 600, color: '#1A1A1A' }}>Admin Dashboard</h1>
          </div>
        </div>

        {/* SUMMARY CARDS */}
        {!isLoading && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: '#fff', padding: '20px', borderRadius: '12px', border: '0.5px solid #E8E8E8' }}>
              <span style={{ fontSize: '13px', color: '#888' }}>Total Tickets</span>
              <h2 style={{ fontSize: '28px', fontWeight: 700, color: '#1A1A1A', marginTop: '4px' }}>{tickets.length}</h2>
            </div>
            <div style={{ background: '#fff', padding: '20px', borderRadius: '12px', border: '0.5px solid #E8E8E8' }}>
              <span style={{ fontSize: '13px', color: '#888' }}>Scheduled Visits</span>
              <h2 style={{ fontSize: '28px', fontWeight: 700, color: '#1A1A1A', marginTop: '4px' }}>{tickets.filter(t => t.technician).length}</h2>
            </div>
            <div style={{ background: '#fff', padding: '20px', borderRadius: '12px', border: '0.5px solid #E8E8E8' }}>
              <span style={{ fontSize: '13px', color: '#888' }}>Open Tickets</span>
              <h2 style={{ fontSize: '28px', fontWeight: 700, color: '#FF6B00', marginTop: '4px' }}>{tickets.filter(t => t.status === 'open').length}</h2>
            </div>
          </div>
        )}

        {/* TICKETS LIST */}
        {isLoading ? (
          <p style={{ textAlign: 'center', color: '#888' }}>Loading all tickets...</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {tickets.map(ticket => (
              <div key={ticket.id} style={{ background: '#fff', borderRadius: '12px', border: '0.5px solid #E8E8E8', overflow: 'hidden' }}>
                <div 
                  style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={() => setExpandedTicket(expandedTicket === ticket.id ? null : ticket.id)}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <span style={{ fontWeight: 700, color: '#1A1A1A' }}>{ticket.id}</span>
                      <span style={{ padding: '2px 8px', borderRadius: '12px', fontSize: '11px', background: '#F7F7F7', color: '#555' }}>
                        {ticket.client_name} (#{ticket.client_account})
                      </span>
                    </div>
                    <p style={{ fontSize: '14px', color: '#555' }}>{ticket.issue}</p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <span style={{ fontSize: '12px', color: '#888' }}>{ticket.date}</span>
                    {expandedTicket === ticket.id ? <IconChevronUp size={20} /> : <IconChevronDown size={20} />}
                  </div>
                </div>

                {/* INTEGRATED EXPANDED VIEW WITH ACTION CONTROLS */}
                {expandedTicket === ticket.id && (
                  <div style={{ borderTop: '0.5px solid #E8E8E8', padding: '20px', background: '#FAFAFA' }}>
                    {/* Admin Controls Area */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                      
                      {/* Change Status Control Dropdown */}
                      <div style={{ background: '#fff', padding: '12px', borderRadius: '8px', border: '0.5px solid #E8E8E8' }}>
                        <label style={{ fontSize: '12px', color: '#888', display: 'block', marginBottom: '4px' }}>Change Status</label>
                        <select 
                          value={ticket.status} 
                          onChange={(e) => handleUpdateStatus(ticket.id, e.target.value)}
                          style={{ width: '100%', padding: '8px', fontSize: '13px', border: '0.5px solid #E0E0E0', borderRadius: '6px' }}
                        >
                          <option value="open">Open</option>
                          <option value="in_progress">In Progress</option>
                          <option value="visit_scheduled">Visit Scheduled</option>
                          <option value="resolved">Resolved</option>
                          <option value="closed">Closed</option>
                        </select>
                      </div>

                      {/* Reschedule Visit Section */}
                      {ticket.technician && (
                        <div style={{ background: '#fff', padding: '12px', borderRadius: '8px', border: '0.5px solid #E8E8E8' }}>
                          <label style={{ fontSize: '12px', color: '#888', display: 'block', marginBottom: '4px' }}>Reassign / Reschedule</label>
                          <div style={{ display: 'flex', gap: '4px' }}>
                            <select id={`tech-${ticket.id}`} defaultValue={ticket.technician} style={{ flex: 1, padding: '6px', fontSize: '12px', border: '0.5px solid #E0E0E0', borderRadius: '6px' }}>
                              {technicians.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                            </select>
                            <input id={`date-${ticket.id}`} type="date" defaultValue={ticket.visit_date} style={{ flex: 1, padding: '6px', fontSize: '12px', border: '0.5px solid #E0E0E0', borderRadius: '6px' }} />
                            <select id={`slot-${ticket.id}`} defaultValue={ticket.visit_slot} style={{ flex: 1, padding: '6px', fontSize: '12px', border: '0.5px solid #E0E0E0', borderRadius: '6px' }}>
                              <option value="morning">Morning</option>
                              <option value="afternoon">Afternoon</option>
                              <option value="evening">Evening</option>
                            </select>
                            <button 
                              onClick={() => handleReschedule(
                                ticket.id, 
                                document.getElementById(`date-${ticket.id}`).value, 
                                document.getElementById(`slot-${ticket.id}`).value, 
                                document.getElementById(`tech-${ticket.id}`).value
                              )}
                              style={{ padding: '6px 12px', background: '#1A1A1A', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}
                            >
                              Update
                            </button>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Chat Transcript Panel */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
                      <IconHistory size={16} color="#888" />
                      <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#1A1A1A' }}>Chat Transcript</h3>
                    </div>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: '13px', color: '#333', background: '#fff', padding: '16px', borderRadius: '8px', border: '0.5px solid #E8E8E8' }}>
                      {ticket.transcript}
                    </pre>
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