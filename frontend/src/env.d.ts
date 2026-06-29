/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_BUILD_TIME: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

import 'axios';

declare module 'axios' {
  interface AxiosRequestConfig {
    /** 为 true 时不显示全局顶部 loading（如已有按钮级 loading 的登录） */
    skipGlobalLoading?: boolean;
  }
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent<object, object, unknown>;
  export default component;
}
