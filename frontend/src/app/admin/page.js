'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  IconArrowLeft, 
  IconShield, 
  IconHistory, 
  IconChevronDown, 
  IconChevronUp, 
  IconAlertTriangle, 
  IconCheck 
} from '@tabler/icons-react';

export default function AdminDashboard() {
  const router = useRouter();
  const [tickets, setTickets] = useState([]);
  const [outages, setOutages] = useState([]);
  const [flaggedChunks, setFlaggedChunks] = useState([]); // New state for flagged KB chunks
  const [isLoading, setIsLoading] = useState(true);
  const [expandedTicket, setExpandedTicket] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [technicians, setTechnicians] = useState([]);

  // New States for Outage Registration Fields
  const [newOutageCity, setNewOutageCity] = useState('');
  const [newOutageStatus, setNewOutageStatus] = useState('');

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

  useEffect(() => {
    const token = sessionStorage.getItem('access_token');
    const adminFlag = sessionStorage.getItem('is_admin') === 'true';
    
    if (!token) { router.push('/login'); return; }
    if (!adminFlag) { router.push('/'); return; }
    
    setIsAdmin(true);
    
    const fetchAdminData = async () => {
      try {
        const headers = { 'Authorization': `Bearer ${token}` };
        
        const [ticketsRes, techsRes, outagesRes, flaggedRes] = await Promise.all([
          fetch(`${API_BASE}/admin/tickets`, { headers }),
          fetch(`${API_BASE}/admin/technicians`, { headers }),
          fetch(`${API_BASE}/admin/outages`, { headers }),
          fetch(`${API_BASE}/admin/flagged-chunks`, { headers }) // Fetch flagged low-rating chunks
        ]);

        if (ticketsRes.status === 401 || ticketsRes.status === 403) { router.push('/login'); return; }
        
        setTickets(await ticketsRes.json());
        setTechnicians(await techsRes.json());
        setOutages(await outagesRes.json());
        if (flaggedRes.ok) setFlaggedChunks(await flaggedRes.json());
      } catch (e) { 
        console.error("Failed to load admin data:", e); 
      } finally { 
        setIsLoading(false); 
      }
    };
    
    fetchAdminData();
  }, [router, API_BASE]);

  // Handler function to clear reviewed flagged chunks
  const handleReviewChunk = async (id) => {
    try {
      await fetch(`${API_BASE}/admin/flagged-chunks/${id}/review`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` }
      });
      setFlaggedChunks(prev => prev.filter(c => c.id !== id));
    } catch (e) {
      console.error("Failed to mark chunk as reviewed:", e);
    }
  };

  // Handler function to update ticket statuses
  const handleUpdateStatus = async (ticketId, newStatus) => {
    try {
      await fetch(`${API_BASE}/admin/tickets/${ticketId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` },
        body: JSON.stringify({ status: newStatus })
      });
      setTickets(prev => prev.map(t => t.id === ticketId ? { ...t, status: newStatus } : t));
    } catch (e) { console.error("Failed to update status"); }
  };

  // Handler function to reassign or reschedule visits
  const handleReschedule = async (ticketId, date, slot, techId) => {
    try {
      await fetch(`${API_BASE}/admin/visits/${ticketId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` },
        body: JSON.stringify({ scheduled_date: date, time_slot: slot, technician_id: techId })
      });
      alert("Visit updated!");
    } catch (e) { console.error("Failed to update visit"); }
  };

  // Handler function to remove ticket entries
  const handleDeleteTicket = async (ticketId) => {
    if (!confirm("Are you sure you want to permanently delete this ticket?")) return;
    try {
      await fetch(`${API_BASE}/admin/tickets/${ticketId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` }
      });
      setTickets(prev => prev.filter(t => t.id !== ticketId));
      setExpandedTicket(null);
    } catch (e) { console.error("Failed to delete ticket"); }
  };

  // Handler function to submit a newly defined regional outage
  const handleCreateOutage = async (e) => {
    e.preventDefault();
    if (!newOutageCity || !newOutageStatus) return;
    try {
      await fetch(`${API_BASE}/admin/outages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` },
        body: JSON.stringify({ city: newOutageCity, status: newOutageStatus })
      });
      
      // Refresh current outages list from API
      const res = await fetch(`${API_BASE}/admin/outages`, { 
        headers: { 'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` } 
      });
      setOutages(await res.json());
      setNewOutageCity('');
      setNewOutageStatus('');
    } catch (e) { console.error("Failed to create outage"); }
  };

  // Handler function to flip activation state on an outage tracking item
  const handleToggleOutage = async (city) => {
    try {
      const res = await fetch(`${API_BASE}/admin/outages/${city}`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` }
      });
      const data = await res.json();
      setOutages(prev => prev.map(o => o.city === city ? { ...o, is_active: data.is_active } : o));
    } catch (e) { console.error("Failed to toggle outage"); }
  };

  // Handler function to delete an active or inactive system outage
  const handleDeleteOutage = async (city) => {
    if (!confirm(`Permanently delete outage for ${city}?`)) return;
    try {
      await fetch(`${API_BASE}/admin/outages/${city}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${sessionStorage.getItem('access_token')}` }
      });
      setOutages(prev => prev.filter(o => o.city !== city));
    } catch (e) { console.error("Failed to delete outage"); }
  };

  if (!isAdmin) return null;

  // --- UI THEME STYLES ---
  const darkBg = "#1A1A1A";
  const orangeAccent = "#FF6B00";
  const whiteBg = "#FFFFFF";
  const lightGreyText = "#888";

  return (
    <div style={{ background: '#f0f2f5', height: '100vh', overflowY: 'auto', padding: '40px' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        {/* HEADER */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px' }}>
          <Link href="/" style={{ color: lightGreyText }}>
            <IconArrowLeft size={24} />
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: darkBg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <IconShield size={20} color={orangeAccent} />
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, color: darkBg }}>Admin Dashboard</h1>
          </div>
        </div>

        {/* OUTAGE MANAGEMENT CARD WITH INTEGRATED FORM & GRID RECOGNITION */}
        {!isLoading && (
          <div style={{ background: whiteBg, padding: '24px', borderRadius: '16px', border: '0.5px solid #E8E8E8', marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <IconAlertTriangle size={20} color={orangeAccent} />
              <h2 style={{ fontSize: '18px', fontWeight: 600, color: darkBg }}>Outage Management</h2>
            </div>
            
            {/* Create Outage Form */}
            <form onSubmit={handleCreateOutage} style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <input 
                type="text" 
                placeholder="City (e.g., Nabeul)" 
                value={newOutageCity} 
                onChange={e => setNewOutageCity(e.target.value)} 
                style={{ flex: 1, padding: '8px', fontSize: '14px', border: '0.5px solid #E0E0E0', borderRadius: '6px' }} 
              />
              <input 
                type="text" 
                placeholder="Status (e.g., Fiber cut. ETA 3h)" 
                value={newOutageStatus} 
                onChange={e => setNewOutageStatus(e.target.value)} 
                style={{ flex: 2, padding: '8px', fontSize: '14px', border: '0.5px solid #E0E0E0', borderRadius: '6px' }} 
              />
              <button 
                type="submit" 
                style={{ padding: '8px 16px', background: darkBg, color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' }}
              >
                Add Outage
              </button>
            </form>

            {/* Existing Outages Responsive Grid Control Panel */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              {outages.map(o => (
                <div key={o.city} style={{ padding: '16px', borderRadius: '12px', background: '#F7F7F7', border: `0.5px solid ${o.is_active ? '#FFCDD2' : '#E8E8E8'}` }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 600, color: darkBg, textTransform: 'capitalize', marginBottom: '4px' }}>{o.city}</h3>
                  <p style={{ fontSize: '12px', color: lightGreyText, marginBottom: '12px', height: '30px' }}>{o.status}</p>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button 
                      onClick={() => handleToggleOutage(o.city)}
                      style={{ flex: 1, padding: '6px', borderRadius: '6px', border: 'none', cursor: 'pointer', fontSize: '12px', fontWeight: 500, background: o.is_active ? '#D32F2F' : '#2E7D32', color: '#fff' }}
                    >
                      {o.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button 
                      onClick={() => handleDeleteOutage(o.city)}
                      style={{ padding: '6px 8px', borderRadius: '6px', border: '1px solid #D32F2F', cursor: 'pointer', fontSize: '12px', fontWeight: 500, background: '#fff', color: '#D32F2F' }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* FLAGGED KB CHUNKS SECTION */}
        {!isLoading && flaggedChunks.length > 0 && (
          <div style={{ background: whiteBg, padding: '24px', borderRadius: '16px', border: '0.5px solid #E8E8E8', marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <IconAlertTriangle size={20} color="#D32F2F" />
              <h2 style={{ fontSize: '18px', fontWeight: 600, color: darkBg }}>Flagged KB Chunks (Low Rating)</h2>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {flaggedChunks.map(c => (
                <div key={c.id} style={{ padding: '16px', borderRadius: '8px', background: '#FFF0F0', border: '1px solid #FFCDD2' }}>
                  <span style={{ fontSize: '12px', color: '#D32F2F', fontWeight: 600, textTransform: 'uppercase' }}>{c.topic}</span>
                  <p style={{ fontSize: '13px', color: '#555', marginTop: '4px', marginBottom: '12px' }}>{c.chunk_text}</p>
                  <button onClick={() => handleReviewChunk(c.id)} style={{ padding: '6px 12px', background: '#fff', border: '1px solid #D32F2F', color: '#D32F2F', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>Mark Reviewed</button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SUMMARY CARDS */}
        {!isLoading && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: darkBg, padding: '20px', borderRadius: '12px' }}>
              <span style={{ fontSize: '13px', color: '#AAA' }}>Total Tickets</span>
              <h2 style={{ fontSize: '28px', fontWeight: 700, color: whiteBg, marginTop: '4px' }}>{tickets.length}</h2>
            </div>
            <div style={{ background: darkBg, padding: '20px', borderRadius: '12px' }}>
              <span style={{ fontSize: '13px', color: '#AAA' }}>Scheduled Visits</span>
              <h2 style={{ fontSize: '28px', fontWeight: 700, color: whiteBg, marginTop: '4px' }}>{tickets.filter(t => t.technician).length}</h2>
            </div>
            <div style={{ background: darkBg, padding: '20px', borderRadius: '12px' }}>
              <span style={{ fontSize: '13px', color: '#AAA' }}>Open Tickets</span>
              <h2 style={{ fontSize: '28px', fontWeight: 700, color: orangeAccent, marginTop: '4px' }}>{tickets.filter(t => t.status === 'open').length}</h2>
            </div>
          </div>
        )}

        {/* TICKETS LIST */}
        {isLoading ? (
          <p style={{ textAlign: 'center', color: lightGreyText }}>Loading all tickets...</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {tickets.map(ticket => (
              <div key={ticket.id} style={{ background: whiteBg, borderRadius: '12px', border: '0.5px solid #E8E8E8', overflow: 'hidden' }}>
                <div 
                  style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={() => setExpandedTicket(expandedTicket === ticket.id ? null : ticket.id)}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <span style={{ fontWeight: 700, color: orangeAccent }}>{ticket.id}</span>
                      <span style={{ padding: '2px 8px', borderRadius: '12px', fontSize: '11px', background: '#1A1A1A', color: '#fff' }}>
                        {ticket.client_name} (#{ticket.client_account})
                      </span>
                    </div>
                    <p style={{ fontSize: '14px', color: '#555' }}>{ticket.issue}</p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <span style={{ fontSize: '12px', color: lightGreyText }}>{ticket.date}</span>
                    {expandedTicket === ticket.id ? <IconChevronUp size={20} /> : <IconChevronDown size={20} />}
                  </div>
                </div>

                {/* EXPANDED TRANSCRIPT VIEW */}
                {expandedTicket === ticket.id && (
                  <div style={{ borderTop: '0.5px solid #E8E8E8', padding: '20px', background: '#FAFAFA' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                      
                      {/* Change Status Control Form Elements */}
                      <div style={{ background: whiteBg, padding: '12px', borderRadius: '8px', border: '0.5px solid #E8E8E8' }}>
                        <label style={{ fontSize: '12px', color: lightGreyText, display: 'block', marginBottom: '4px' }}>Change Status</label>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <select id={`status-${ticket.id}`} defaultValue={ticket.status} style={{ flex: 1, padding: '8px', fontSize: '13px', border: '0.5px solid #E0E0E0', borderRadius: '6px' }}>
                            <option value="open">Open</option>
                            <option value="in_progress">In Progress</option>
                            <option value="visit_scheduled">Visit Scheduled</option>
                            <option value="resolved">Resolved</option>
                            <option value="closed">Closed</option>
                          </select>
                          <button onClick={() => handleUpdateStatus(ticket.id, document.getElementById(`status-${ticket.id}`).value)} style={{ padding: '8px 16px', background: orangeAccent, color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}>Save</button>
                        </div>
                      </div>

                      {/* Reschedule Visit Control Form Elements */}
                      {ticket.technician && (
                        <div style={{ background: whiteBg, padding: '12px', borderRadius: '8px', border: '0.5px solid #E8E8E8' }}>
                          <label style={{ fontSize: '12px', color: lightGreyText, display: 'block', marginBottom: '4px' }}>Reassign / Reschedule</label>
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
                            <button onClick={() => handleReschedule(ticket.id, document.getElementById(`date-${ticket.id}`).value, document.getElementById(`slot-${ticket.id}`).value, document.getElementById(`tech-${ticket.id}`).value)} style={{ padding: '6px 12px', background: darkBg, color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>Update</button>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Chat Transcript Panel */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
                      <IconHistory size={16} color={lightGreyText} />
                      <h3 style={{ fontSize: '14px', fontWeight: 600, color: darkBg }}>Chat Transcript</h3>
                    </div>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: '13px', color: '#333', background: whiteBg, padding: '16px', borderRadius: '8px', border: '0.5px solid #E8E8E8', maxHeight: '300px', overflowY: 'auto' }}>
                      {ticket.transcript}
                    </pre>

                    {/* Delete Ticket Context Button */}
                    <div style={{ marginTop: '20px', textAlign: 'right' }}>
                      <button onClick={() => handleDeleteTicket(ticket.id)} style={{ padding: '8px 16px', background: whiteBg, color: '#D32F2F', border: '1px solid #D32F2F', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}>Delete Ticket</button>
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