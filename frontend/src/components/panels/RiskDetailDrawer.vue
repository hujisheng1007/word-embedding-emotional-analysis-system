<template>
  <el-drawer
    :model-value="Boolean(result)"
    size="420px"
    title="风险文本详情"
    @close="emit('close')"
  >
    <template v-if="result">
      <div class="detail-block">
        <p class="detail-label">原始文本</p>
        <div class="detail-card">{{ result.text }}</div>
      </div>

      <div class="detail-meta">
        <div class="detail-item">
          <span>类别</span>
          <strong>{{ result.category }}</strong>
        </div>
        <div class="detail-item">
          <span>等级</span>
          <strong>{{ result.level }}</strong>
        </div>
        <div class="detail-item">
          <span>分数</span>
          <strong>{{ result.score.toFixed(2) }}</strong>
        </div>
      </div>

      <div class="detail-block">
        <p class="detail-label">命中关键词</p>
        <div class="inline-tags">
          <el-tag
            v-for="keyword in result.keywords"
            :key="keyword"
            effect="dark"
            round
          >
            {{ keyword }}
          </el-tag>
          <span v-if="result.keywords.length === 0" class="detail-empty">无明显关键词</span>
        </div>
      </div>

      <div class="detail-block">
        <p class="detail-label">规则说明</p>
        <div class="detail-card">{{ result.rule_reason }}</div>
      </div>

      <div class="detail-block">
        <p class="detail-label">解释说明</p>
        <div class="detail-card">{{ result.llm_explanation }}</div>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import type { AnalysisResult } from "../../types/analysis";

defineProps<{
  result: AnalysisResult | null;
}>();

const emit = defineEmits<{
  close: [];
}>();
</script>
