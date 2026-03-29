<template>
  <el-card class="panel-card attention-board">
    <template #header>
      <div class="panel-header">
        <span>重点关注看板</span>
        <el-tag type="danger" effect="dark">{{ items.length }} 条</el-tag>
      </div>
    </template>

    <div v-if="items.length > 0" class="attention-list">
      <button
        v-for="item in items.slice(0, 6)"
        :key="`${item.text}-${item.score}`"
        class="attention-item"
        type="button"
        @click="emit('select', item)"
      >
        <div class="attention-topline">
          <span class="attention-category">{{ item.category }}</span>
          <span class="attention-score">{{ item.score.toFixed(2) }}</span>
        </div>
        <p class="attention-text">{{ item.text }}</p>
        <div class="inline-tags">
          <el-tag
            v-for="keyword in item.keywords.slice(0, 3)"
            :key="keyword"
            size="small"
            effect="plain"
            type="danger"
          >
            {{ keyword }}
          </el-tag>
        </div>
      </button>
    </div>

    <div v-else class="attention-empty">
      当前数据中没有重点关注文本，页面将保持正常监测状态。
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { AnalysisResult } from "../../types/analysis";

defineProps<{
  items: AnalysisResult[];
}>();

const emit = defineEmits<{
  select: [result: AnalysisResult];
}>();
</script>
