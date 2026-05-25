import axios from 'axios';
import { trackHttpRequestEnd, trackHttpRequestStart } from '@/api/httpLoading';
import { useAuthStore } from '@/stores/auth';
import { useContextStore } from '@/stores/context';

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

http.interceptors.request.use((config) => {
  const auth = useAuthStore();
  const ctx = useContextStore();
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  if (ctx.projectId) {
    config.headers['X-Project-Id'] = ctx.projectId;
  }
  trackHttpRequestStart(config);
  return config;
});

http.interceptors.response.use(
  (res) => {
    trackHttpRequestEnd(res.config);
    return res;
  },
  (err) => {
    trackHttpRequestEnd(err.config);
    const url = String(err.config?.url ?? '');
    const isAuthLogin = url.includes('/auth/login');
    if (err.response?.status === 401 && !isAuthLogin) {
      useAuthStore().logoutAndRedirect();
    }
    return Promise.reject(err);
  }
);

export default http;
