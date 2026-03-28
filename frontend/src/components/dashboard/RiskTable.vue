<template>
  <el-card class="panel-card">
    <template #header>
      <div class="panel-header">
        <span>风险文本列表</span>
      </div>
    </template>

    <el-table :data="items" :loading="loading" height="420" class="risk-table">
      <el-table-column prop="text" label="文本内容" min-width="260" show-overflow-tooltip />
      <el-table-column prop="category" label="类别" width="120" />
      <el-table-column prop="level" label="等级" width="100" />
      <el-table-column label="分数" width="100">
        <template #default="{ row }">
          {{ row.score.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="关键词" min-width="180">
        <template #default="{ row }">
          <div class="inline-tags">
            <el-tag
              v-for="keyword in row.keywords"
              :key="keyword"
              size="small"
              effect="plain"
            >
              {{ keyword }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="emit('view-detail', row)">
            查看详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import type { AnalysisResult } from "../../types/analysis";

defineProps<{
  items: AnalysisResult[];
  loading: boolean;
}>();

const emit = defineEmits<{
  "view-detail": [result: AnalysisResult];
}>();
</script>
