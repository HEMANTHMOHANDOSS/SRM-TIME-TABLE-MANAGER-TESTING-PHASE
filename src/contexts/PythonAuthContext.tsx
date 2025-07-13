import React, { createContext, useContext, useState, useEffect } from 'react';
import { backendApi, User } from '../services/backendApi';

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  loading: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const PythonAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          console.log('🔐 Verifying existing token...');
          const response = await backendApi.verifyToken();
          
          if (response.success && response.data?.user) {
            console.log('✅ Token valid, user authenticated:', response.data.user.email);
            setUser(response.data.user);
          } else {
            console.warn('❌ Invalid token. Removing...');
            localStorage.removeItem('auth_token');
          }
        } catch (error) {
          console.error('❌ Auth initialization error:', error);
          localStorage.removeItem('auth_token');
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      setLoading(true);

      const cleanedEmail = email.trim().toLowerCase();   // ✅ Normalize email
      const cleanedPassword = password.trim();           // ✅ Trim whitespace

      console.log('📤 Attempting login for:', cleanedEmail);

      const response = await backendApi.login({
        email: cleanedEmail,
        password: cleanedPassword,
      });

      if (response.success && response.data) {
        const { user: userData } = response.data;
        console.log('✅ Login successful:', userData.email, 'Role:', userData.role);
        setUser(userData);
        return { success: true };
      } else {
        console.error('❌ Login failed:', response.error);
        return { success: false, error: response.error || 'Login failed' };
      }
    } catch (error) {
      console.error('❌ Login error:', error);
      return { success: false, error: 'An unexpected error occurred during login' };
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      console.log('🚪 Logging out...');
      await backendApi.logout();
    } catch (error) {
      console.error('⚠️ Logout error:', error);
    } finally {
      setUser(null);
      console.log('✅ User logged out');
    }
  };

  const value: AuthContextType = {
    user,
    login,
    logout,
    loading,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
