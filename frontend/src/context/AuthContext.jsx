import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../api/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load user from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('derma_token');
    const savedUser = localStorage.getItem('derma_user');
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      const response = await authAPI.login(email, password);
      const { access_token, user: userData } = response.data;

      setToken(access_token);
      setUser(userData);

      localStorage.setItem('derma_token', access_token);
      localStorage.setItem('derma_user', JSON.stringify(userData));

      return { success: true, user: userData };
    } catch (error) {
      console.error('Login failed:', error);
      const message =
        error.response?.data?.detail ||
        (error.code === 'ERR_NETWORK' || !error.response
          ? 'Cannot connect to server. Please ensure the backend is running.'
          : 'Invalid email or password. Please try again.');
      return { success: false, error: message };
    }
  };

  const register = async (name, email, password, role = 'patient') => {
    try {
      const response = await authAPI.register(name, email, password, role);
      const { access_token, user: userData } = response.data;

      setToken(access_token);
      setUser(userData);

      localStorage.setItem('derma_token', access_token);
      localStorage.setItem('derma_user', JSON.stringify(userData));

      return { success: true, user: userData };
    } catch (error) {
      console.error('Registration failed:', error);
      const message =
        error.response?.data?.detail ||
        (error.code === 'ERR_NETWORK' || !error.response
          ? 'Cannot connect to server. Please ensure the backend is running.'
          : 'Registration failed. Please try again.');
      return { success: false, error: message };
    }
  };

  const googleLogin = async (googleCredential) => {
    try {
      const response = await authAPI.googleLogin(googleCredential);
      const { access_token, user: userData } = response.data;

      setToken(access_token);
      setUser(userData);

      localStorage.setItem('derma_token', access_token);
      localStorage.setItem('derma_user', JSON.stringify(userData));

      return { success: true };
    } catch (error) {
      console.error('Google login failed:', error);
      const message = error.response?.data?.detail || 'Google sign-in failed.';
      return { success: false, error: message };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('derma_token');
    localStorage.removeItem('derma_user');
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!token,
    login,
    register,
    googleLogin,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
