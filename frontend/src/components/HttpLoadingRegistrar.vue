<template />

<script setup lang="ts">
import { onMounted } from 'vue';
import { useLoadingBar } from 'naive-ui';
import { registerHttpLoading } from '@/api/httpLoading';

const loadingBar = useLoadingBar();

onMounted(() => {
  registerHttpLoading({
    start: () => loadingBar.start(),
    finish: () => loadingBar.finish(),
  });
});
</script>
