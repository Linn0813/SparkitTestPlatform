import { onUnmounted, ref } from 'vue';

/** 保存后短暂锁定工具栏，避免「保存」位被「删除」替换后同一次点击误触删除 */
export function useToolbarActionLock(ms = 800) {
  const toolbarActionLocked = ref(false);
  let timer: ReturnType<typeof setTimeout> | null = null;

  function lockToolbarActions() {
    if (timer !== null) {
      clearTimeout(timer);
    }
    toolbarActionLocked.value = true;
    timer = setTimeout(() => {
      toolbarActionLocked.value = false;
      timer = null;
    }, ms);
  }

  function stopToolbarActionLock() {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
    toolbarActionLocked.value = false;
  }

  onUnmounted(stopToolbarActionLock);

  return { toolbarActionLocked, lockToolbarActions, stopToolbarActionLock };
}
