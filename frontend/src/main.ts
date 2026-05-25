import { createApp, watch } from 'vue';
import { createPinia } from 'pinia';
import naive from 'naive-ui';
import App from './App.vue';
import router from './router';
import { useAuthStore } from '@/stores/auth';

const pinia = createPinia();
const app = createApp(App);
app.use(pinia);
app.use(router);

const auth = useAuthStore(pinia);
watch(
  () => auth.token,
  (token) => {
    if (token || router.currentRoute.value.meta.public) return;
    void router.replace({ name: 'login' });
  }
);

app.use(naive);
app.mount('#app');
