<template>
  <div class="app-shell">
    <header class="app-navigation">
      <span class="app-brand">中国经典教育家多模态资料与道德行动研究</span>
      <RouterLink to="/">教育家画像分析</RouterLink>
      <RouterLink to="/moral">采集与道德行为分析</RouterLink>
      <RouterLink to="/resources">研究资源库</RouterLink>
      <RouterLink to="/collection">多源数据采集中心</RouterLink>
      <RouterLink to="/knowledge">知识检索与评测</RouterLink>
    </header>
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from "vue-router";
</script>

<style scoped>
.app-navigation {
  position: sticky;
  z-index: 20;
  top: 0;
  display: flex;
  justify-content: center;
  gap: 10px;
  padding: 10px 20px;
  border-bottom: 1px solid rgba(22, 54, 78, 0.12);
  background: rgba(248, 250, 247, 0.94);
  backdrop-filter: blur(12px);
  flex-wrap: wrap;
}

.app-brand {
  align-self: center;
  margin-right: 16px;
  color: #173f52;
  font-size: 16px;
  font-weight: 700;
}

.app-navigation a {
  padding: 7px 14px;
  border-radius: 999px;
  color: #46606f;
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
}

.app-navigation a.router-link-active {
  color: white;
  background: #173f52;
}
</style>
