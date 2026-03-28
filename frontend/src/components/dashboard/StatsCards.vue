<template>
  <section class="stats-grid">
    <el-card class="stat-card">
      <p class="stat-label">样本总数</p>
      <p class="stat-value">{{ summary.total }}</p>
    </el-card>

    <el-card class="stat-card">
      <p class="stat-label">重点关注</p>
      <p class="stat-value danger">{{ summary.attention_count }}</p>
    </el-card>

    <el-card class="stat-card">
      <p class="stat-label">心理风险</p>
      <p class="stat-value">{{ summary.category_distribution["心理风险"] ?? 0 }}</p>
    </el-card>

    <el-card class="stat-card">
      <p class="stat-label">舆情风险</p>
      <p class="stat-value">{{ summary.category_distribution["舆情风险"] ?? 0 }}</p>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import type { BatchAnalysisSummary } from "../../types/analysis";

defineProps<{
  summary: BatchAnalysisSummary;
}>();
</script>
