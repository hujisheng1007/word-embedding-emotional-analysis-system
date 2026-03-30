<template>
  <div v-if="rows.length" :class="['personality-breakdown', { compact }]">
    <section class="personality-chart-shell">
      <div class="personality-chart-head">
        <strong>三重人格占比</strong>
        <span>按当前文本证据归一化</span>
      </div>
      <div ref="chartRef" class="personality-chart"></div>
    </section>

    <section class="personality-analysis-list">
      <article
        v-for="row in rows"
        :key="row.id"
        class="personality-analysis-card"
      >
        <div class="personality-card-head">
          <div>
            <strong class="personality-name">{{ row.name }}</strong>
            <p class="personality-subhead">占比 {{ row.shareLabel }} · 显现度 {{ row.scoreLabel }}</p>
          </div>
          <span class="personality-share-badge">{{ row.shareLabel }}</span>
        </div>

        <p class="personality-analysis-copy">{{ row.analysis }}</p>

        <div class="personality-chip-row" v-if="row.keywords.length">
          <span
            v-for="keyword in row.keywords"
            :key="`${row.id}-${keyword}`"
            class="personality-chip"
          >
            {{ keyword }}
          </span>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";

import type { AnalysisResult, DimensionScore, IndicatorMetricResult, IndicatorScore } from "../../types/analysis";

interface BreakdownRow {
  id: string;
  name: string;
  rawScore: number;
  share: number;
  shareLabel: string;
  scoreLabel: string;
  keywords: string[];
  analysis: string;
}

const props = withDefaults(
  defineProps<{
    result: AnalysisResult | null;
    compact?: boolean;
  }>(),
  {
    compact: false
  }
);

const chartRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

const groupOrder = [
  { id: "natural_personality", name: "自然人格" },
  { id: "professional_personality", name: "职业人格" },
  { id: "moral_personality", name: "道德人格" }
] as const;

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatMetricValue(metric: IndicatorMetricResult): string {
  return Number.isInteger(metric.value) ? String(metric.value) : metric.value.toFixed(2);
}

function fallbackDimensionScore(groupId: string, indicatorScores: IndicatorScore[]): number {
  const currentItems = indicatorScores.filter((item) => item.group_id === groupId);
  if (currentItems.length === 0) {
    return 0;
  }

  const topItems = [...currentItems].sort((left, right) => right.score - left.score).slice(0, 2);
  return topItems.reduce((sum, item) => sum + item.score, 0) / topItems.length;
}

function keywordsForDimension(
  dimension: DimensionScore | undefined,
  groupId: string,
  indicatorScores: IndicatorScore[]
): string[] {
  if (dimension?.matched_keywords?.length) {
    return dimension.matched_keywords.slice(0, 6);
  }

  return Array.from(
    new Set(
      indicatorScores
        .filter((item) => item.group_id === groupId)
        .flatMap((item) => item.matched_keywords)
    )
  ).slice(0, 6);
}

function buildAnalysis(
  groupName: string,
  shareLabel: string,
  scoreLabel: string,
  topIndicators: IndicatorScore[],
  keywords: string[]
): string {
  if (topIndicators.length === 0 || topIndicators.every((item) => item.score <= 0)) {
    return `${groupName}当前占比${shareLabel}，但显性证据较弱，现有文本还需要补充更具体的行为、情境或价值表述。`;
  }

  const mainIndicators = topIndicators.slice(0, 2);
  const indicatorText = mainIndicators.map((item) => `${item.name}${formatPercent(item.score)}`).join("、");
  const topIndicator = topIndicators[0];
  const metricText = topIndicator.metric_results
    .slice(0, 3)
    .map((metric) => `${metric.name}${formatMetricValue(metric)}${metric.unit}`)
    .join("、");
  const keywordText = keywords.length > 0 ? `命中线索包括“${keywords.join("、")}”。` : "";

  return `${groupName}当前占比${shareLabel}，显现度${scoreLabel}。主要由${indicatorText}支撑；其中“${topIndicator.name}”的量化表现为${metricText}。${keywordText}`;
}

const rows = computed<BreakdownRow[]>(() => {
  const result = props.result;
  if (!result) {
    return [];
  }

  const dimensionScores = result.dimension_scores ?? [];
  const indicatorScores = result.indicator_scores ?? [];
  const dimensionMap = new Map(dimensionScores.map((item) => [item.id, item]));

  const rawRows = groupOrder.map((group) => {
    const dimension = dimensionMap.get(group.id);
    const rawScore =
      dimension && dimension.score > 0
        ? dimension.score
        : fallbackDimensionScore(group.id, indicatorScores);
    const groupIndicators = indicatorScores
      .filter((item) => item.group_id === group.id)
      .sort((left, right) => right.score - left.score);
    const keywords = keywordsForDimension(dimension, group.id, indicatorScores);

    return {
      id: group.id,
      name: dimension?.name ?? group.name,
      rawScore,
      keywords,
      indicators: groupIndicators
    };
  });

  const totalScore = rawRows.reduce((sum, item) => sum + Math.max(item.rawScore, 0), 0);
  const normalizedTotal = totalScore > 0 ? totalScore : rawRows.length;

  return rawRows.map((item) => {
    const share = totalScore > 0 ? item.rawScore / normalizedTotal : 1 / normalizedTotal;
    const shareLabel = formatPercent(share);
    const scoreLabel = formatPercent(item.rawScore);

    return {
      id: item.id,
      name: item.name,
      rawScore: item.rawScore,
      share,
      shareLabel,
      scoreLabel,
      keywords: item.keywords,
      analysis: buildAnalysis(item.name, shareLabel, scoreLabel, item.indicators, item.keywords)
    };
  });
});

function renderChart(): void {
  if (!chartRef.value || rows.value.length === 0) {
    return;
  }

  chart ??= echarts.init(chartRef.value);
  chart.setOption({
    backgroundColor: "transparent",
    color: ["#207567", "#d59c3e", "#c56d42"],
    tooltip: {
      trigger: "item",
      formatter: (params: { name: string; value: number }) => `${params.name}: ${params.value}%`
    },
    series: [
      {
        type: "pie",
        radius: props.compact ? ["42%", "68%"] : ["46%", "72%"],
        center: ["50%", "50%"],
        itemStyle: {
          borderRadius: 12,
          borderColor: "#fff8ef",
          borderWidth: 3
        },
        label: {
          color: "#44525e",
          formatter: ({ name, value }: { name: string; value: number }) => `${name}\n${value}%`
        },
        data: rows.value.map((item) => ({
          name: item.name,
          value: Math.round(item.share * 100)
        }))
      }
    ]
  });
}

function handleResize(): void {
  chart?.resize();
}

onMounted(() => {
  renderChart();
  window.addEventListener("resize", handleResize);
});

watch(rows, () => {
  renderChart();
}, { deep: true });

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  chart?.dispose();
  chart = null;
});
</script>

<style scoped>
.personality-breakdown {
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) minmax(0, 1.3fr);
  gap: 16px;
  align-items: start;
}

.personality-breakdown.compact {
  grid-template-columns: 1fr;
}

.personality-chart-shell,
.personality-analysis-card {
  padding: 16px;
  border-radius: 20px;
  background: rgba(255, 250, 241, 0.92);
  border: 1px solid rgba(90, 80, 60, 0.07);
}

.personality-chart-head,
.personality-card-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.personality-chart-head strong,
.personality-name {
  color: #23313b;
}

.personality-chart-head span,
.personality-subhead,
.personality-analysis-copy {
  color: #586776;
}

.personality-subhead,
.personality-analysis-copy {
  margin: 8px 0 0;
  line-height: 1.8;
}

.personality-chart {
  height: 280px;
}

.personality-breakdown.compact .personality-chart {
  height: 240px;
}

.personality-analysis-list {
  display: grid;
  gap: 14px;
}

.personality-share-badge {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(32, 117, 103, 0.1);
  color: #1d675b;
  font-weight: 700;
}

.personality-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.personality-chip {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(180, 135, 60, 0.1);
  color: #8b6532;
  font-size: 12px;
}

@media (max-width: 960px) {
  .personality-breakdown {
    grid-template-columns: 1fr;
  }
}
</style>
