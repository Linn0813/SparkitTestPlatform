import type { InternalAxiosRequestConfig } from 'axios';

const SHOW_DELAY_MS = 150;

let pending = 0;
let showTimer: ReturnType<typeof setTimeout> | null = null;
let barStarted = false;

let startBar: (() => void) | null = null;
let finishBar: (() => void) | null = null;

export function registerHttpLoading(handlers: { start: () => void; finish: () => void }) {
  startBar = handlers.start;
  finishBar = handlers.finish;
}

function shouldTrack(config: InternalAxiosRequestConfig | undefined): boolean {
  return config?.skipGlobalLoading !== true;
}

function beginBar() {
  if (barStarted) return;
  barStarted = true;
  startBar?.();
}

function endBar() {
  if (showTimer) {
    clearTimeout(showTimer);
    showTimer = null;
  }
  if (!barStarted) return;
  barStarted = false;
  finishBar?.();
}

export function trackHttpRequestStart(config: InternalAxiosRequestConfig) {
  if (!shouldTrack(config)) return;
  pending += 1;
  if (pending === 1) {
    showTimer = setTimeout(() => {
      showTimer = null;
      if (pending > 0) beginBar();
    }, SHOW_DELAY_MS);
  }
}

export function trackHttpRequestEnd(config: InternalAxiosRequestConfig | undefined) {
  if (!shouldTrack(config)) return;
  pending = Math.max(0, pending - 1);
  if (pending === 0) endBar();
}
