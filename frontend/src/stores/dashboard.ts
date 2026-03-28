import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { analyzeBatch, analyzeText } from "../api/analysis";
import { dashboardMockData } from "../constants/mock";
import type { AnalysisResult, BatchAnalysisResponse } from "../types/analysis";
import { extractTextsFromFile } from "../utils/fileParser";
import { analyzeBatchFallback, analyzeTextFallback } from "../utils/fallbackAnalysis";

const ALL_OPTION = "全部";

export const useDashboardStore = defineStore("dashboard", () => {
  const batchData = ref<BatchAnalysisResponse>(dashboardMockData);
  const quickAnalysis = ref<AnalysisResult | null>(null);
  const selectedResult = ref<AnalysisResult | null>(null);
  const loading = ref(false);
  const connectionMode = ref<"mock" | "api">("mock");
  const searchText = ref("");
  const categoryFilter = ref(ALL_OPTION);
  const levelFilter = ref(ALL_OPTION);
  const attentionOnly = ref(false);
  const importFilename = ref("");
  const statusMessage = ref("当前展示默认演示数据。");

  const categories = computed(() => [
    ALL_OPTION,
    ...new Set(batchData.value.results.map((item) => item.category))
  ]);

  const levels = computed(() => [
    ALL_OPTION,
    ...new Set(batchData.value.results.map((item) => item.level))
  ]);

  const filteredResults = computed(() =>
    batchData.value.results.filter((item) => {
      const matchesSearch =
        !searchText.value.trim() ||
        item.text.includes(searchText.value.trim()) ||
        item.keywords.some((keyword) => keyword.includes(searchText.value.trim()));
      const matchesCategory =
        categoryFilter.value === ALL_OPTION || item.category === categoryFilter.value;
      const matchesLevel = levelFilter.value === ALL_OPTION || item.level === levelFilter.value;
      const matchesAttention = !attentionOnly.value || item.needs_attention;

      return matchesSearch && matchesCategory && matchesLevel && matchesAttention;
    })
  );

  const attentionItems = computed(() =>
    batchData.value.results.filter((item) => item.needs_attention)
  );

  async function loadDashboardData(): Promise<void> {
    loading.value = true;
    try {
      batchData.value = await analyzeBatch({
        texts: dashboardMockData.results.map((item) => item.text)
      });
      connectionMode.value = "api";
      statusMessage.value = "已连接后端接口，当前数据来自真实 API。";
    } catch {
      batchData.value = analyzeBatchFallback(dashboardMockData.results.map((item) => item.text));
      connectionMode.value = "mock";
      statusMessage.value = "后端未启动，已自动回退到本地演示分析。";
    } finally {
      loading.value = false;
    }
  }

  async function runQuickAnalysis(text: string): Promise<void> {
    if (!text.trim()) {
      quickAnalysis.value = null;
      return;
    }

    loading.value = true;
    try {
      quickAnalysis.value = await analyzeText({ text });
      connectionMode.value = "api";
      statusMessage.value = "单条分析已通过后端接口完成。";
    } catch {
      quickAnalysis.value = analyzeTextFallback(text);
      connectionMode.value = "mock";
      statusMessage.value = "后端未连接，单条分析已回退到本地规则演示。";
    } finally {
      selectedResult.value = quickAnalysis.value;
      loading.value = false;
    }
  }

  async function importTextFile(file: File): Promise<void> {
    loading.value = true;
    try {
      const texts = await extractTextsFromFile(file);
      if (texts.length === 0) {
        statusMessage.value = "文件中没有可分析的文本，请检查内容格式。";
        return;
      }

      try {
        batchData.value = await analyzeBatch({ texts });
        connectionMode.value = "api";
        statusMessage.value = `已通过后端分析导入文件：${file.name}`;
      } catch {
        batchData.value = analyzeBatchFallback(texts);
        connectionMode.value = "mock";
        statusMessage.value = `后端未连接，已使用本地规则分析导入文件：${file.name}`;
      }

      importFilename.value = file.name;
      selectedResult.value = batchData.value.summary.high_risk_texts[0] ?? batchData.value.results[0] ?? null;
      resetFilters();
    } finally {
      loading.value = false;
    }
  }

  function selectResult(result: AnalysisResult): void {
    selectedResult.value = result;
  }

  function closeResultDrawer(): void {
    selectedResult.value = null;
  }

  function resetFilters(): void {
    searchText.value = "";
    categoryFilter.value = ALL_OPTION;
    levelFilter.value = ALL_OPTION;
    attentionOnly.value = false;
  }

  return {
    attentionItems,
    attentionOnly,
    batchData,
    categories,
    categoryFilter,
    closeResultDrawer,
    connectionMode,
    filteredResults,
    importFilename,
    importTextFile,
    levelFilter,
    levels,
    loading,
    quickAnalysis,
    loadDashboardData,
    resetFilters,
    runQuickAnalysis,
    searchText,
    selectResult,
    selectedResult,
    statusMessage
  };
});
