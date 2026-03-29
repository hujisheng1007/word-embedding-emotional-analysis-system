<template>
  <main class="dashboard">
    <header class="hero-card">
      <div>
        <p class="eyebrow">Campus Risk Command Center</p>
        <h1>校园风险文本识别与可视化分析平台</h1>
        <p class="subtitle">
          当前页面已支持单条分析、批量导入、搜索筛选、风险详情查看和公开数据接入。
          现在也支持可切换的强模型档案，便于在 Ollama、本地兼容服务和在线模型之间切换。
        </p>
      </div>

      <div class="hero-side">
        <LiveClock />
        <div class="hero-status">
          <div class="hero-badges">
            <el-tag size="large" effect="dark" type="primary">
              {{ dashboardStore.connectionMode === "api" ? "已连接后端" : "演示数据模式" }}
            </el-tag>
            <el-tag
              v-if="dashboardStore.systemStatus?.llm_enabled"
              size="large"
              effect="dark"
              type="success"
            >
              {{ dashboardStore.systemStatus.llm_model }}
            </el-tag>
            <el-tag
              v-if="dashboardStore.systemStatus?.foundation_model_enabled"
              size="large"
              effect="dark"
              type="warning"
            >
              {{ dashboardStore.systemStatus.foundation_model_name }}
            </el-tag>
          </div>

          <div class="model-switcher">
            <el-select
              v-model="dashboardStore.selectedFoundationProfileId"
              class="model-switcher-select"
              placeholder="选择强模型档案"
              size="large"
            >
              <el-option
                v-for="profile in dashboardStore.foundationProfiles"
                :key="profile.id"
                :label="profile.label"
                :value="profile.id"
              >
                <div class="model-option">
                  <span>{{ profile.label }}</span>
                  <small>{{ profile.configured ? "已配置" : "待配置" }}</small>
                </div>
              </el-option>
            </el-select>
            <el-button
              type="warning"
              :loading="dashboardStore.foundationSwitching"
              @click="dashboardStore.activateSelectedFoundationProfile"
            >
              切换强模型
            </el-button>
          </div>

          <p v-if="dashboardStore.activeFoundationProfile" class="hero-subnote">
            {{ dashboardStore.activeFoundationProfile.description }}
          </p>
          <p class="hero-note">{{ dashboardStore.statusMessage }}</p>
          <p v-if="dashboardStore.systemStatus?.llm_enabled" class="hero-subnote">
            本地 Llama 解释已启用；更强模型档案主要负责更细的分类与研判。
          </p>
        </div>
      </div>
    </header>

    <StatsCards :summary="dashboardStore.batchData.summary" />

    <section class="content-grid content-grid-emphasis">
      <DistributionChart
        title="风险类别分布"
        :data="dashboardStore.batchData.summary.category_distribution"
      />
      <DistributionChart
        title="风险等级分布"
        :data="dashboardStore.batchData.summary.level_distribution"
      />
      <WordCloudChart :items="dashboardStore.batchData.summary.wordcloud_keywords" />
      <AttentionBoard
        :items="dashboardStore.attentionItems"
        @select="dashboardStore.selectResult"
      />
    </section>

    <section class="control-grid control-grid-triple">
      <FileImportPanel
        :filename="dashboardStore.importFilename"
        :import-summary="dashboardStore.importSummary"
        :datasets="dashboardStore.datasets"
        :loading="dashboardStore.loading || dashboardStore.datasetLoading"
        :selected-dataset-id="dashboardStore.selectedDatasetId"
        :selected-dataset-meta="dashboardStore.selectedDatasetMeta"
        :status-message="dashboardStore.statusMessage"
        @load-dataset="dashboardStore.loadSelectedDataset"
        @import="dashboardStore.importTextFile"
        @update:selected-dataset-id="dashboardStore.selectedDatasetId = $event"
      />
      <PublicSourcePanel
        :loading="dashboardStore.publicLoading"
        :selected-source-id="dashboardStore.selectedPublicSourceId"
        :sources="dashboardStore.publicSources"
        @fetch="dashboardStore.fetchSelectedPublicSource"
        @update:selected-source-id="dashboardStore.selectedPublicSourceId = $event"
      />
      <FilterToolbar
        :attention-only="dashboardStore.attentionOnly"
        :categories="dashboardStore.categories"
        :category-filter="dashboardStore.categoryFilter"
        :filtered-count="dashboardStore.filteredResults.length"
        :level-filter="dashboardStore.levelFilter"
        :levels="dashboardStore.levels"
        :search-text="dashboardStore.searchText"
        :total="dashboardStore.batchData.results.length"
        @reset="dashboardStore.resetFilters"
        @update:attention-only="dashboardStore.attentionOnly = $event"
        @update:category-filter="dashboardStore.categoryFilter = $event"
        @update:level-filter="dashboardStore.levelFilter = $event"
        @update:search-text="dashboardStore.searchText = $event"
      />
    </section>

    <section class="analysis-grid">
      <QuickAnalyzePanel
        :loading="dashboardStore.loading"
        :mode="dashboardStore.connectionMode"
        :result="dashboardStore.quickAnalysis"
        @analyze="dashboardStore.runQuickAnalysis"
      />

      <RiskTable
        :items="dashboardStore.filteredResults"
        :loading="dashboardStore.loading || dashboardStore.publicLoading || dashboardStore.datasetLoading"
        @view-detail="dashboardStore.selectResult"
      />
    </section>

    <RiskDetailDrawer
      :result="dashboardStore.selectedResult"
      @close="dashboardStore.closeResultDrawer"
    />
  </main>
</template>

<script setup lang="ts">
import { onMounted } from "vue";

import DistributionChart from "../../components/charts/DistributionChart.vue";
import WordCloudChart from "../../components/charts/WordCloudChart.vue";
import AttentionBoard from "../../components/dashboard/AttentionBoard.vue";
import LiveClock from "../../components/dashboard/LiveClock.vue";
import RiskTable from "../../components/dashboard/RiskTable.vue";
import StatsCards from "../../components/dashboard/StatsCards.vue";
import FileImportPanel from "../../components/panels/FileImportPanel.vue";
import FilterToolbar from "../../components/panels/FilterToolbar.vue";
import PublicSourcePanel from "../../components/panels/PublicSourcePanel.vue";
import QuickAnalyzePanel from "../../components/panels/QuickAnalyzePanel.vue";
import RiskDetailDrawer from "../../components/panels/RiskDetailDrawer.vue";
import { useDashboardStore } from "../../stores/dashboard";

const dashboardStore = useDashboardStore();

onMounted(() => {
  void dashboardStore.bootstrap();
});
</script>
