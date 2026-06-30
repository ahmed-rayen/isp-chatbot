'use client';
import { IconAlertTriangle } from '@tabler/icons-react';

export default function OutageBanner({ outages }) {
  if (outages.length === 0) return null;

  return (
    <div style={{
      margin: '16px 20px 0', padding: '12px 16px', background: '#FFF3EB',
      border: '1px solid #FF6B00', borderRadius: 12, display: 'flex', alignItems: 'flex-start', gap: 12,
    }}>
      <IconAlertTriangle size={20} color="#FF6B00" style={{ flexShrink: 0, marginTop: 2 }} />
      <div>
        <h4 style={{ fontSize: 14, fontWeight: 600, color: '#1A1A1A', marginBottom: 4 }}>Active Outages in Your Area</h4>
        {outages.map(o => (
          <p key={o.city} style={{ fontSize: 13, color: '#555', margin: '4px 0 0' }}>
            <strong style={{ textTransform: 'capitalize' }}>{o.city}:</strong> {o.status}
          </p>
        ))}
      </div>
    </div>
  );
}