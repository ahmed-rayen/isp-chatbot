'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export function useAuth() {
  const router = useRouter();
  const [user, setUser] = useState({
    name: '',
    account: '',
    isAdmin: false,
    isTech: false,
    isAuthenticated: false,
  });

  useEffect(() => {
    const token = sessionStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    setUser({
      name: sessionStorage.getItem('user_name') || 'User',
      account: sessionStorage.getItem('user_account') || '0000',
      isAdmin: sessionStorage.getItem('is_admin') === 'true',
      isTech: sessionStorage.getItem('is_technician') === 'true',
      isAuthenticated: true,
    });
  }, [router]);

  const logout = () => {
    sessionStorage.clear();
    router.push('/login');
  };

  return { ...user, logout };
}