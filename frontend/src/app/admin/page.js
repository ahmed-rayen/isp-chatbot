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
    
    fetchAllTickets();
  }, [router]);

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

                {/* EXPANDED TRANSCRIPT VIEW */}
                {expandedTicket === ticket.id && (
                  <div style={{ borderTop: '0.5px solid #E8E8E8', padding: '20px', background: '#FAFAFA' }}>
                    <div style={{ display: 'flex', gap: '24px', marginBottom: '16px' }}>
                      <div>
                        <span style={{ fontSize: '12px', color: '#888' }}>Status</span>
                        <p style={{ fontSize: '14px', fontWeight: 500 }}>{ticket.status}</p>
                      </div>
                      <div>
                        <span style={{ fontSize: '12px', color: '#888' }}>Technician</span>
                        <p style={{ fontSize: '14px', fontWeight: 500 }}>{ticket.technician || 'None'}</p>
                      </div>
                      <div>
                        <span style={{ fontSize: '12px', color: '#888' }}>Visit Date</span>
                        <p style={{ fontSize: '14px', fontWeight: 500 }}>{ticket.visit_date ? `${ticket.visit_date} (${ticket.visit_slot})` : 'None'}</p>
                      </div>
                    </div>

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