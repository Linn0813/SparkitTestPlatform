import { defineStore } from 'pinia';
import { ref } from 'vue';
import { fetchMe, login as apiLogin } from '@/api/auth';
import type { MeResponse, User } from '@/types';
import { useContextStore } from './context';

const TOKEN_KEY = 'sparkit_token';

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY));
  const user = ref<User | null>(null);
  const me = ref<MeResponse | null>(null);

  async function login(email: string, password: string) {
    const { data } = await apiLogin(email, password);
    token.value = data.access_token;
    localStorage.setItem(TOKEN_KEY, data.access_token);
    await loadMe();
  }

  async function loadMe() {
    const { data } = await fetchMe();
    user.value = data.user;
    me.value = data;
    const ctx = useContextStore();
    ctx.applyFromMe(data);
  }

  function logout() {
    token.value = null;
    user.value = null;
    me.value = null;
    localStorage.removeItem(TOKEN_KEY);
    useContextStore().reset();
  }

  return { token, user, me, login, loadMe, logout };
});
