import axios from 'axios';

// Use environment variable in production (e.g. Vercel), fallback to '/api' for Vite dev proxy
const rawApiUrl = import.meta.env.VITE_API_URL;
export const API_BASE = rawApiUrl ? rawApiUrl.replace(/\/+$/, '') : '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor — attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('derma_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — handle 401 for authenticated session expiry
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isAuthEndpoint = error.config?.url?.includes('/auth/');
    if (error.response?.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem('derma_token');
      localStorage.removeItem('derma_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// --- Auth ---
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (name, email, password, role = 'patient') => api.post('/auth/register', { name, email, password, role }),
  googleLogin: (token) => api.post('/auth/google', { token }),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token, newPassword) => api.post('/auth/reset-password', { token, new_password: newPassword }),
};

// --- Predict ---
export const predictAPI = {
  analyze: (imageFile, symptoms = '', bodyLocation = '', duration = '') => {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('symptoms', symptoms);
    if (bodyLocation) formData.append('body_location', bodyLocation);
    if (duration) formData.append('duration', duration);

    return api.post('/predict', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    });
  },
  analyzeWithForm: (formData) => {
    return api.post('/predict', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    });
  },
  exportPdf: (resultData) => {
    return api.post('/predict/report-pdf', resultData, {
      responseType: 'blob',
    });
  },
  downloadPdf: async (resultData) => {
    const response = await api.post('/predict/report-pdf', resultData, {
      responseType: 'blob',
    });
    return response.data;
  },
};

// --- History ---
export const historyAPI = {
  getAll: (limit = 50, offset = 0, filters = {}) => {
    const params = { limit, offset, ...filters };
    return api.get('/history', { params });
  },
  globalSearch: (query) => api.get(`/history/global-search?q=${encodeURIComponent(query)}`),
  getById: (caseId) => api.get(`/history/${caseId}`),
  downloadPdf: async (caseId) => {
    const response = await api.get(`/history/${caseId}/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

// --- Dataset / Show Data Explorer ---
export const datasetAPI = {
  getRecords: (params = {}) => api.get('/dataset', { params }),
  getImageUrl: (imagePath) => `${API_BASE}/dataset/image?path=${encodeURIComponent(imagePath)}`,
  getHistoryExplorer: (params = {}) => api.get('/dataset/history-explorer', { params }),
  getReference: (diseaseName) => api.get(`/dataset/reference/${encodeURIComponent(diseaseName)}`),
};

// --- Diseases ---
export const diseaseAPI = {
  getAll: () => api.get('/diseases'),
  getById: (id) => api.get(`/disease/${id}`),
};

// --- Follow-up Reminders ---
export const remindersAPI = {
  getAll: () => api.get('/reminders'),
  dismiss: (id) => api.post(`/reminders/${id}/dismiss`),
  complete: (id) => api.post(`/reminders/${id}/complete`),
  processDue: () => api.post('/reminders/process-due'),
};

// --- RAG Medical Chatbot ---
export const chatAPI = {
  ask: (question, caseId = null) => api.post('/chat', { question, case_id: caseId }),
};

// --- Continuous Learning & Training Console ---
export const trainingAPI = {
  getStats: () => api.get('/training/admin/stats'),
  reviewCase: (caseId, payload) => api.post(`/training/doctor/cases/${caseId}/review`, payload),
  retrain: () => api.post('/training/admin/retrain'),
  rollback: (targetVersionId) => api.post('/training/admin/rollback', { target_version_id: targetVersionId }),
};

// --- Admin Management Console ---
export const adminAPI = {
  getStats: () => api.get('/admin/stats'),
  getUsers: (params = {}) => api.get('/admin/users', { params }),
  getUserDetail: (userId) => api.get(`/admin/users/${userId}`),
  enrollUser: (payload) => api.post('/admin/users/enroll', payload),
  updateUserRole: (userId, role) => api.patch(`/admin/users/${userId}/role`, { role }),
  updateUserStatus: (userId, status) => api.patch(`/admin/users/${userId}/status`, { status }),
  getLoginActivity: (params = {}) => api.get('/admin/login-activity', { params }),
  getAuditLogs: (params = {}) => api.get('/admin/audit-logs', { params }),
  reloadDiseaseData: () => api.post('/admin/reload-disease-data'),
};

// --- Health ---
export const healthAPI = {
  check: () => api.get('/health'),
};

export default api;

