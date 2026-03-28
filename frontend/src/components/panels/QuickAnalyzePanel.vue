<template>
  <el-card class="panel-card">
    <template #header>
      <div class="panel-header">
        <span>单条文本分析</span>
        <el-tag size="small" effect="dark">{{ modeLabel }}</el-tag>
      </div>
    </template>

    <el-input
      v-model="draft"
      :rows="5"
      type="textarea"
      placeholder="输入一段待分析文本，例如：最近真的要崩溃了，不想继续了。"
    />

    <div class="panel-actions">
      <el-button type="primary" :loading="loading" @click="handleAnalyze">
        立即分析
      </el-button>
      <el-button text @click="fillDemoText">填入示例</el-button>
    </div>

    <div v-if="result" class="analysis-result">
      <div class="result-row">
        <span>类别</span>
        <strong>{{ result.category }}</strong>
      </div>
      <div class="result-row">
        <span>等级</span>
        <strong>{{ result.level }}</strong>
      </div>
      <div class="result-row">
        <span>分数</span>
        <strong>{{ result.score.toFixed(2) }}</strong>
      </div>
      <div class="result-text">
        <p>规则说明</p>
        <span>{{ result.rule_reason }}</span>
      </div>
      <div class="result-text">
        <p>解释说明</p>
        <span>{{ result.llm_explanation }}</span>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import type { AnalysisResult } from "../../types/analysis";

const props = defineProps<{
  loading: boolean;
  result: AnalysisResult | null;
  mode: "mock" | "api";
}>();

const emit = defineEmits<{
  analyze: [text: string];
}>();

const draft = ref("");
const modeLabel = computed(() => (props.mode === "api" ? "接口模式" : "演示模式"));

function handleAnalyze(): void {
  emit("analyze", draft.value);
}

function fillDemoText(): void {
  draft.value = "最近真的要崩溃了，不想继续了。";
}
</script>
