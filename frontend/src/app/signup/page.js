'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { IconWifi, IconAlertCircle, IconCircleCheck } from '@tabler/icons-react';

export default function SignupPage() {
  const [name, setName] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [successAccount, setSuccessAccount] = useState(''); // NEW: To hold the generated ID
  const router = useRouter();
  const [email, setEmail] = useState('');
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

  const handleSignup = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name,email, pin })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Signup failed');
      }

      // Save token and user info
      sessionStorage.setItem('access_token', data.access_token);
      sessionStorage.setItem('user_name', data.user.name);
      sessionStorage.setItem('user_plan', data.user.plan);
      sessionStorage.setItem('user_account', data.user.account_number);

      // Show the success screen with their new account number!
      setSuccessAccount(data.user.account_number);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // If signup is successful, show this screen first
  if (successAccount) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#f0f2f5' }}>
        <div style={{ width: '400px', background: '#FFFFFF', borderRadius: '16px', padding: '40px', boxShadow: '0 10px 30px rgba(0,0,0,0.05)', border: '0.5px solid #E8E8E8', textAlign: 'center' }}>
          <div style={{ width: '56px', height: '56px', borderRadius: '50%', background: '#E8F5E9', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
            <IconCircleCheck size={32} color="#2E7D32" />
          </div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: '#1A1A1A', marginBottom: '8px' }}>Account Created!</h1>
          <p style={{ fontSize: '14px', color: '#888', marginBottom: '24px' }}>Please save your Account Number. You will need it to log in next time.</p>
          
          <div style={{ background: '#F7F7F7', border: '0.5px dashed #FF6B00', borderRadius: '12px', padding: '16px', marginBottom: '24px' }}>
            <div style={{ fontSize: '12px', color: '#888', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Your Account Number</div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#FF6B00', marginTop: '4px', letterSpacing: '2px' }}>{successAccount}</div>
          </div>

          <button 
            onClick={() => router.push('/')} 
            style={{ width: '100%', padding: '12px', background: '#FF6B00', color: '#fff', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: 500, cursor: 'pointer' }}
          >
            Continue to Chat
          </button>
        </div>
      </div>
    );
  }

  // Normal Signup Form
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#f0f2f5' }}>
      <div style={{ width: '400px', background: '#FFFFFF', borderRadius: '16px', padding: '40px', boxShadow: '0 10px 30px rgba(0,0,0,0.05)', border: '0.5px solid #E8E8E8' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '24px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: '#FF6B00', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px' }}>
            <IconWifi size={24} color="#fff" />
          </div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: '#1A1A1A' }}>Create Account</h1>
          <p style={{ fontSize: '14px', color: '#888', marginTop: '4px' }}>Sign up for Oassis Telecom</p>
        </div>

        {error && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#FFF0F0', color: '#D32F2F', padding: '12px', borderRadius: '8px', marginBottom: '16px', fontSize: '13px', border: '1px solid #FFCDD2' }}>
            <IconAlertCircle size={16} />
            {error}
          </div>
        )}

        <form onSubmit={handleSignup}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#555', marginBottom: '6px' }}>Full Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} required style={{ width: '100%', padding: '12px', fontSize: '14px', border: '0.5px solid #E0E0E0', borderRadius: '8px', outline: 'none', boxSizing: 'border-box' }} placeholder="e.g., Ahmed H." />
          </div>
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#555', marginBottom: '6px' }}>PIN Code</label>
            <input type="password" value={pin} onChange={(e) => setPin(e.target.value)} required style={{ width: '100%', padding: '12px', fontSize: '14px', border: '0.5px solid #E0E0E0', borderRadius: '8px', outline: 'none', boxSizing: 'border-box' }} placeholder="Create a 4-digit PIN" />
          </div>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#555', marginBottom: '6px' }}>Email Address</label>
           <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={{ width: '100%', padding: '12px', fontSize: '14px', border: '0.5px solid #E0E0E0', borderRadius: '8px', outline: 'none', boxSizing: 'border-box' }} placeholder="you@example.com" />
          </div>
          <button type="submit" disabled={isLoading} style={{ width: '100%', padding: '12px', background: '#FF6B00', color: '#fff', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: 500, cursor: 'pointer', opacity: isLoading ? 0.7 : 1 }}>
            {isLoading ? 'Creating account...' : 'Sign Up'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '13px', color: '#888' }}>
          Already have an account? <Link href="/login" style={{ color: '#FF6B00', textDecoration: 'none', fontWeight: 500 }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}