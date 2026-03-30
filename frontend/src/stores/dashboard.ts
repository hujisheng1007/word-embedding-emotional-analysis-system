import { computed, ref } from "vue";
import { defineStore } from "pinia";

import {
  activateFoundationModelProfile,
  analyzeBatch,
  analyzeText,
  fetchPublicSource,
  getDataset,
  getDefaultDataset,
  getReferenceLibrary,
  getSystemStatus,
  listDatasets,
  listFoundationModelProfiles,
  listPublicSources
} from "../api/analysis";
import { dashboardMockData, referenceLibraryMockData } from "../constants/mock";
import type {
  AnalysisResult,
  BatchAnalysisResponse,
  DatasetOption,
  FoundationModelProfile,
  ImportSummary,
  PublicSource,
  ReferenceLibraryResponse,
  SystemStatusResponse
} from "../types/analysis";
import { extractTextsFromFile } from "../utils/fileParser";
import { analyzeBatchFallback, analyzeTextFallback } from "../utils/fallbackAnalysis";

const ALL_OPTION = "全部";

export const useDashboardStore = defineStore("dashboard", () => {
  const batchData = ref<BatchAnalysisResponse>(dashboardMockData);
  const referenceLibrary = ref<ReferenceLibraryResponse>(referenceLibraryMockData);
  const quickAnalysis = ref<AnalysisResult | null>(null);
  const selectedResult = ref<AnalysisResult | null>(dashboardMockData.results[0] ?? null);
  const loading = ref(false);
  const datasetLoading = ref(false);
  const publicLoading = ref(false);
  const foundationSwitching = ref(false);
  const connectionMode = ref<"mock" | "api">("mock");
  const searchText = ref("");
  const categoryFilter = ref(ALL_OPTION);
  const levelFilter = ref(ALL_OPTION);
  const attentionOnly = ref(false);
  const importFilename = ref("");
  const importSummary = ref<ImportSummary | null>(null);
  const statusMessage = ref("当前展示的是按论文重构后的教育家三重人格演示数据。");
  const publicSources = ref<PublicSource[]>([]);
  const selectedPublicSourceId = ref("");
  const foundationProfiles = ref<FoundationModelProfile[]>([]);
  const selectedFoundationProfileId = ref("foundation-disabled");
  const systemStatus = ref<SystemStatusResponse | null>(null);
  const datasets = ref<DatasetOption[]>([]);
  const selectedDatasetId = ref("");

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
      const keyword = searchText.value.trim();
      const matchesSearch =
        !keyword ||
        item.text.includes(keyword) ||
        item.keywords.some((current) => current.includes(keyword)) ||
        item.category.includes(keyword);
      const matchesCategory =
        categoryFilter.value === ALL_OPTION || item.category === categoryFilter.value;
      const matchesLevel = levelFilter.value === ALL_OPTION || item.level === levelFilter.value;
      const matchesAttention = !attentionOnly.value || item.needs_attention;
      return matchesSearch && matchesCategory && matchesLevel && matchesAttention;
    })
  );

  const highlightedResults = computed(() =>
    batchData.value.results.filter((item) => item.needs_attention)
  );

  const activeFoundationProfile = computed(() =>
    foundationProfiles.value.find((item) => item.id === selectedFoundationProfileId.value) ?? null
  );

  const selectedDatasetMeta = computed(() =>
    datasets.value.find((item) => item.id === selectedDatasetId.value) ?? null
  );

  async function bootstrap(): Promise<void> {
    await Promise.all([
      loadReferenceLibrary(),
      loadDatasetCatalog(),
      loadPublicSources(),
      loadSystemStatus(),
      loadFoundationProfiles()
    ]);
    await loadDashboardData();
  }

  async function loadReferenceLibrary(): Promise<void> {
    try {
      referenceLibrary.value = await getReferenceLibrary();
    } catch {
      referenceLibrary.value = referenceLibraryMockData;
    }
  }

  async function loadDatasetCatalog(): Promise<void> {
    try {
      datasets.value = await listDatasets();
      const defaultDataset = datasets.value.find((item) => item.is_default);
      if (!selectedDatasetId.value) {
        selectedDatasetId.value = defaultDataset?.id ?? datasets.value[0]?.id ?? "";
      }
    } catch {
      datasets.value = [];
    }
  }

  async function loadDashboardData(): Promise<void> {
    datasetLoading.value = true;
    try {
      batchData.value = await getDefaultDataset();
      connectionMode.value = "api";
      if (!selectedDatasetId.value) {
        const defaultDataset = datasets.value.find((item) => item.is_default);
        selectedDatasetId.value = defaultDataset?.id ?? "";
      }
      statusMessage.value =
        "已载入你提供的访谈底库，并按论文的三重人格结构完成首轮分析。";
      importFilename.value = "";
      importSummary.value = null;
      selectedResult.value =
        batchData.value.summary.high_risk_texts[0] ?? batchData.value.results[0] ?? null;
    } catch {
      batchData.value = dashboardMockData;
      connectionMode.value = "mock";
      statusMessage.value = "后端暂未连通，当前使用本地三重人格演示数据。";
      selectedResult.value =
        batchData.value.summary.high_risk_texts[0] ?? batchData.value.results[0] ?? null;
    } finally {
      datasetLoading.value = false;
    }
  }

  async function loadSelectedDataset(): Promise<void> {
    if (!selectedDatasetId.value) {
      statusMessage.value = "请先选择一个数据集。";
      return;
    }

    datasetLoading.value = true;
    try {
      batchData.value = await getDataset(selectedDatasetId.value);
      connectionMode.value = "api";
      importFilename.value = "";
      importSummary.value = null;
      resetFilters();
      selectedResult.value =
        batchData.value.summary.high_risk_texts[0] ?? batchData.value.results[0] ?? null;

      const dataset = selectedDatasetMeta.value;
      statusMessage.value = dataset
        ? `已切换到数据集“${dataset.name}”，当前共展示 ${dataset.record_count} 条文本。`
        : "已切换到所选数据集。";
    } catch (error) {
      statusMessage.value =
        error instanceof Error ? `数据集加载失败：${error.message}` : "数据集加载失败，请稍后重试。";
    } finally {
      datasetLoading.value = false;
    }
  }

  async function loadSystemStatus(): Promise<void> {
    try {
      systemStatus.value = await getSystemStatus();
      selectedFoundationProfileId.value =
        systemStatus.value.active_foundation_profile_id || "foundation-disabled";
    } catch {
      systemStatus.value = null;
    }
  }

  async function loadFoundationProfiles(): Promise<void> {
    try {
      foundationProfiles.value = await listFoundationModelProfiles();
      const activeProfile = foundationProfiles.value.find((item) => item.active);
      if (activeProfile) {
        selectedFoundationProfileId.value = activeProfile.id;
      }
    } catch {
      foundationProfiles.value = [];
    }
  }

  async function activateSelectedFoundationProfile(): Promise<void> {
    if (!selectedFoundationProfileId.value) {
      return;
    }

    foundationSwitching.value = true;
    try {
      systemStatus.value = await activateFoundationModelProfile(selectedFoundationProfileId.value);
      await loadFoundationProfiles();
      const profile = foundationProfiles.value.find(
        (item) => item.id === selectedFoundationProfileId.value
      );
      statusMessage.value = profile
        ? `已切换解释增强档案：${profile.label}。`
        : "已切换解释增强档案。";
    } catch (error) {
      statusMessage.value =
        error instanceof Error ? `强模型切换失败：${error.message}` : "强模型切换失败，请稍后重试。";
    } finally {
      foundationSwitching.value = false;
    }
  }

  async function loadPublicSources(): Promise<void> {
    try {
      publicSources.value = await listPublicSources();
      if (!selectedPublicSourceId.value && publicSources.value.length > 0) {
        selectedPublicSourceId.value = publicSources.value[0].id;
      }
    } catch {
      publicSources.value = [];
    }
  }

  async function fetchSelectedPublicSource(): Promise<void> {
    if (!selectedPublicSourceId.value) {
      statusMessage.value = "当前没有可用的在线文本源。";
      return;
    }

    publicLoading.value = true;
    try {
      const payload = await fetchPublicSource({
        source_id: selectedPublicSourceId.value,
        limit: 8
      });
      batchData.value = payload.analysis;
      selectedResult.value =
        payload.analysis.summary.high_risk_texts[0] ?? payload.analysis.results[0] ?? null;
      connectionMode.value = "api";
      statusMessage.value = `已从“${payload.source.name}”抓取 ${payload.fetched_count} 条在线文本，并完成底库映射分析。`;
      importFilename.value = "";
      importSummary.value = null;
      resetFilters();
    } catch (error) {
      statusMessage.value =
        error instanceof Error
          ? `在线文本获取失败：${error.message}`
          : "在线文本获取失败，请稍后重试。";
    } finally {
      publicLoading.value = false;
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
      statusMessage.value = "单条在线文本已完成三重人格映射分析。";
    } catch {
      quickAnalysis.value = analyzeTextFallback(text);
      connectionMode.value = "mock";
      statusMessage.value = "后端未连通，当前使用本地三重人格规则完成单条分析。";
    } finally {
      selectedResult.value = quickAnalysis.value;
      loading.value = false;
    }
  }

  async function importTextFile(file: File): Promise<void> {
    loading.value = true;
    try {
      const { texts, summary } = await extractTextsFromFile(file);
      importSummary.value = summary;

      if (texts.length === 0) {
        statusMessage.value = "文件中没有可分析的文本，请检查内容格式。";
        return;
      }

      try {
        batchData.value = await analyzeBatch({ texts });
        connectionMode.value = "api";
        statusMessage.value = `已导入 ${file.name}，共保留 ${summary.extracted_count} 条有效文本并完成映射分析。`;
      } catch {
        batchData.value = analyzeBatchFallback(texts);
        connectionMode.value = "mock";
        statusMessage.value = `后端未连通，已使用本地规则分析导入文件 ${file.name}。`;
      }

      importFilename.value = file.name;
      selectedResult.value =
        batchData.value.summary.high_risk_texts[0] ?? batchData.value.results[0] ?? null;
      resetFilters();
    } finally {
      loading.value = false;
    }
  }

  function selectResult(result: AnalysisResult): void {
    selectedResult.value = result;
  }

  function resetFilters(): void {
    searchText.value = "";
    categoryFilter.value = ALL_OPTION;
    levelFilter.value = ALL_OPTION;
    attentionOnly.value = false;
  }

  return {
    activeFoundationProfile,
    activateSelectedFoundationProfile,
    attentionOnly,
    batchData,
    bootstrap,
    categories,
    categoryFilter,
    connectionMode,
    datasetLoading,
    datasets,
    fetchSelectedPublicSource,
    filteredResults,
    foundationProfiles,
    foundationSwitching,
    highlightedResults,
    importFilename,
    importSummary,
    importTextFile,
    levelFilter,
    levels,
    loadDashboardData,
    loadDatasetCatalog,
    loadFoundationProfiles,
    loadPublicSources,
    loadReferenceLibrary,
    loadSelectedDataset,
    loadSystemStatus,
    loading,
    publicLoading,
    publicSources,
    quickAnalysis,
    referenceLibrary,
    resetFilters,
    runQuickAnalysis,
    searchText,
    selectResult,
    selectedDatasetId,
    selectedDatasetMeta,
    selectedFoundationProfileId,
    selectedPublicSourceId,
    selectedResult,
    statusMessage,
    systemStatus
  };
});
