'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { IconWifi, IconArrowLeft, IconClock, IconUser } from '@tabler/icons-react';
import { apiFetch } from '../lib/api'; // <-- ADD IMPORT

export default function TicketsPage() {
  const router = useRouter();
  const [tickets, setTickets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

  useEffect(() => {
    const token = sessionStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }
    
    const fetchTickets = async () => {
      try {
        // USE apiFetch INSTEAD OF RAW fetch
        const res = await apiFetch(`${API_BASE}/tickets`);
        if (res.status === 401) { router.push('/login'); return; }
        const data = await res.json();
        setTickets(data);
      } catch (e) { console.error("Failed to load tickets:", e.message); }
      finally { setIsLoading(false); }
    };
    
    fetchTickets();
  }, [router, API_BASE]);

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
              <div key={ticket.id} style={{ background: '#fff', padding: '24px', borderRadius: '16px', border: '0.5px solid #E8E8E8' }}>
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
            ))}
          </div>
        )}
      </div>
    </div>
  );
}