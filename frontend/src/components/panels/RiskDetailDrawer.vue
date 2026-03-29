<template>
  <el-drawer
    :model-value="Boolean(result)"
    size="440px"
    title="风险文本详情"
    @close="emit('close')"
  >
    <template v-if="displayResult">
      <div class="detail-block">
        <p class="detail-label">原始文本</p>
        <div class="detail-card">{{ displayResult.text }}</div>
      </div>

      <div class="detail-meta">
        <div class="detail-item">
          <span>类别</span>
          <strong>{{ displayResult.category }}</strong>
        </div>
        <div class="detail-item">
          <span>等级</span>
          <strong>{{ displayResult.level }}</strong>
        </div>
        <div class="detail-item">
          <span>分数</span>
          <strong>{{ displayResult.score.toFixed(2) }}</strong>
        </div>
      </div>

      <div class="detail-block" v-if="scoreBreakdown.length">
        <p class="detail-label">评分分解</p>
        <div class="detail-score-list">
          <div
            v-for="factor in scoreBreakdown"
            :key="`${factor.name}-${factor.description}`"
            class="detail-score-item"
          >
            <div class="detail-score-head">
              <strong>{{ factor.name }}</strong>
              <span :class="factor.value >= 0 ? 'score-up' : 'score-down'">
                {{ factor.value >= 0 ? "+" : "" }}{{ factor.value.toFixed(2) }}
              </span>
            </div>
            <p>{{ factor.description }}</p>
          </div>
        </div>
      </div>

      <div class="detail-block">
        <p class="detail-label">命中关键词</p>
        <div class="inline-tags">
          <el-tag
            v-for="keyword in displayResult.keywords"
            :key="keyword"
            effect="dark"
            round
          >
            {{ keyword }}
          </el-tag>
          <span v-if="displayResult.keywords.length === 0" class="detail-empty">无明显关键词</span>
        </div>
      </div>

      <div class="detail-block">
        <p class="detail-label">规则说明</p>
        <div class="detail-card">{{ displayResult.rule_reason }}</div>
      </div>

      <div class="detail-block">
        <div class="detail-label-row">
          <p class="detail-label">解释说明</p>
          <el-button
            text
            type="primary"
            :loading="analysisLoading"
            @click="refreshAssessment"
          >
            重新生成
          </el-button>
        </div>
        <div class="detail-card">
          <template v-if="analysisLoading">
            <el-skeleton :rows="2" animated />
          </template>
          <template v-else>
            {{ displayResult.llm_explanation }}
          </template>
        </div>
        <p v-if="analysisHint" class="detail-hint">{{ analysisHint }}</p>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { analyzeText } from "../../api/analysis";
import type { AnalysisResult } from "../../types/analysis";

const props = defineProps<{
  result: AnalysisResult | null;
}>();

const emit = defineEmits<{
  close: [];
}>();

const displayResult = ref<AnalysisResult | null>(null);
const analysisLoading = ref(false);
const analysisHint = ref("");
const scoreBreakdown = computed(() => displayResult.value?.score_breakdown ?? []);
let requestToken = 0;

watch(
  () => props.result,
  (value) => {
    if (!value) {
      displayResult.value = null;
      analysisLoading.value = false;
      analysisHint.value = "";
      return;
    }

    displayResult.value = value;
    analysisHint.value = "打开详情后会优先使用当前选中的大模型重新研判这条文本。";
    void refreshAssessment();
  },
  { immediate: true }
);

async function refreshAssessment(): Promise<void> {
  if (!props.result) {
    return;
  }

  const token = ++requestToken;
  analysisLoading.value = true;
  analysisHint.value = "正在使用当前选中的大模型重新分析并生成说明...";

  try {
    const payload = await analyzeText({ text: props.result.text });
    if (token !== requestToken) {
      return;
    }

    displayResult.value = payload;
    analysisHint.value = "当前说明与分数为基于所选大模型重新研判后的结果。";
  } catch {
    if (token !== requestToken) {
      return;
    }

    displayResult.value = props.result;
    analysisHint.value = "大模型重研判失败，当前显示的是已有分析结果。";
  } finally {
    if (token === requestToken) {
      analysisLoading.value = false;
    }
  }
}
</script>
