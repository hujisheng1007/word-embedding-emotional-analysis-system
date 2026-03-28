<template>
  <el-card class="panel-card">
    <template #header>
      <div class="panel-header">
        <span>高频关键词</span>
      </div>
    </template>

    <div class="keyword-list">
      <el-tag
        v-for="item in items"
        :key="item.keyword"
        class="keyword-tag"
        effect="dark"
        round
      >
        {{ item.keyword }} · {{ item.count }}
      </el-tag>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { KeywordCount } from "../../types/analysis";

defineProps<{
  items: KeywordCount[];
}>();
</script>
