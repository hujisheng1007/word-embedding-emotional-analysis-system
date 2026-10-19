<template>
  <div class="app-shell">
    <header class="app-navigation">
      <RouterLink to="/">人格分析</RouterLink>
      <RouterLink to="/resources">研究资源库</RouterLink>
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
