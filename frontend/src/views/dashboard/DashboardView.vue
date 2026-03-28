<template>
  <main class="dashboard">
    <header class="hero-card">
      <div>
        <p class="eyebrow">Campus Risk Command Center</p>
        <h1>校园风险文本识别与可视化分析平台</h1>
        <p class="subtitle">
          当前页面已支持单条分析、批量导入、搜索筛选和风险详情查看。后端未启动时自动回退到本地规则演示，保证现场展示不断线。
        </p>
      </div>

      <div class="hero-side">
        <el-tag size="large" effect="dark" type="primary">
          {{ dashboardStore.connectionMode === "api" ? "已连接后端" : "演示数据模式" }}
        </el-tag>
        <p class="hero-note">{{ dashboardStore.statusMessage }}</p>
      </div>
    </header>

    <StatsCards :summary="dashboardStore.batchData.summary" />

    <section class="content-grid">
      <DistributionChart
        title="风险类别分布"
        :data="dashboardStore.batchData.summary.category_distribution"
      />
      <DistributionChart
        title="风险等级分布"
        :data="dashboardStore.batchData.summary.level_distribution"
      />
      <KeywordList :items="dashboardStore.batchData.summary.top_keywords" />
      <QuickAnalyzePanel
        :loading="dashboardStore.loading"
        :mode="dashboardStore.connectionMode"
        :result="dashboardStore.quickAnalysis"
        @analyze="dashboardStore.runQuickAnalysis"
      />
    </section>

    <section class="control-grid">
      <FileImportPanel
        :filename="dashboardStore.importFilename"
        :loading="dashboardStore.loading"
        :status-message="dashboardStore.statusMessage"
        @import="dashboardStore.importTextFile"
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

    <section class="table-grid">
      <RiskTable
        :items="dashboardStore.filteredResults"
        :loading="dashboardStore.loading"
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
import KeywordList from "../../components/dashboard/KeywordList.vue";
import RiskTable from "../../components/dashboard/RiskTable.vue";
import StatsCards from "../../components/dashboard/StatsCards.vue";
import FileImportPanel from "../../components/panels/FileImportPanel.vue";
import FilterToolbar from "../../components/panels/FilterToolbar.vue";
import QuickAnalyzePanel from "../../components/panels/QuickAnalyzePanel.vue";
import RiskDetailDrawer from "../../components/panels/RiskDetailDrawer.vue";
import { useDashboardStore } from "../../stores/dashboard";

const dashboardStore = useDashboardStore();

onMounted(() => {
  void dashboardStore.loadDashboardData();
});
</script>
