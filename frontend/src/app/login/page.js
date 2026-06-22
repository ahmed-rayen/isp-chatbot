'use client';
import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { IconWifi, IconAlertCircle } from '@tabler/icons-react';

export default function LoginPage() {
  const [accountNumber, setAccountNumber] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const API_BASE = 'http://localhost:8000/api'; // Or your .env variable

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_number: accountNumber, pin: pin })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      // Save token and user info to sessionStorage
      // (Using sessionStorage so it clears when they close the tab)
      sessionStorage.setItem('access_token', data.access_token);
      sessionStorage.setItem('user_name', data.user.name);
      sessionStorage.setItem('user_plan', data.user.plan);
      sessionStorage.setItem('user_account', data.user.account_number);

      // Redirect to the main chat page
      router.push('/');
      
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh', 
      background: '#f0f2f5' 
    }}>
      <div style={{ 
        width: '400px', 
        background: '#FFFFFF', 
        borderRadius: '16px', 
        padding: '40px', 
        boxShadow: '0 10px 30px rgba(0,0,0,0.05)', 
        border: '0.5px solid #E8E8E8' 
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '24px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: '#FF6B00', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px' }}>
            <IconWifi size={24} color="#fff" />
          </div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: '#1A1A1A' }}>Oassis Telecom</h1>
          <p style={{ fontSize: '14px', color: '#888', marginTop: '4px' }}>Sign in to NetAssist Support</p>
        </div>

        {error && (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            background: '#FFF0F0', 
            color: '#D32F2F', 
            padding: '12px', 
            borderRadius: '8px', 
            marginBottom: '16px', 
            fontSize: '13px',
            border: '1px solid #FFCDD2'
          }}>
            <IconAlertCircle size={16} />
            {error}
          </div>
        )}

        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#555', marginBottom: '6px' }}>Account Number</label>
            <input 
              type="text" 
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
              required
              style={{ width: '100%', padding: '12px', fontSize: '14px', border: '0.5px solid #E0E0E0', borderRadius: '8px', outline: 'none', boxSizing: 'border-box' }}
              placeholder="e.g., 4821"
            />
          </div>
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#555', marginBottom: '6px' }}>PIN Code</label>
            <input 
              type="password" 
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              required
              style={{ width: '100%', padding: '12px', fontSize: '14px', border: '0.5px solid #E0E0E0', borderRadius: '8px', outline: 'none', boxSizing: 'border-box' }}
              placeholder="Enter your 4-digit PIN"
            />
          </div>
          <button 
            type="submit" 
            disabled={isLoading}
            style={{ 
              width: '100%', 
              padding: '12px', 
              background: '#FF6B00', 
              color: '#fff', 
              border: 'none', 
              borderRadius: '8px', 
              fontSize: '14px', 
              fontWeight: 500, 
              cursor: 'pointer',
              opacity: isLoading ? 0.7 : 1
            }}
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '13px', color: '#888' }}>
          Don&apos;t have an account? <Link href="/signup" style={{ color: '#FF6B00', textDecoration: 'none', fontWeight: 500 }}>Sign up</Link>
        </p>
      </div>
    </div>
  );
}