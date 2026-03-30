<template>
  <el-card class="chart-card">
    <template #header>
      <div class="panel-header">
        <span>人格线索词云</span>
      </div>
    </template>
    <div ref="containerRef" class="chart-body"></div>
  </el-card>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import "echarts-wordcloud";

import type { KeywordCount } from "../../types/analysis";

const props = defineProps<{
  items: KeywordCount[];
}>();

const containerRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

function createFallbackData() {
  return [{ name: "暂无词云数据", value: 1, textStyle: { color: "#7b6b58" } }];
}

function renderChart(): void {
  if (!containerRef.value) {
    return;
  }

  chart ??= echarts.init(containerRef.value);
  chart.setOption({
    backgroundColor: "transparent",
    tooltip: {
      show: true
    },
    series: [
      {
        type: "wordCloud",
        shape: "circle",
        width: "100%",
        height: "100%",
        left: "center",
        top: "center",
        sizeRange: [14, 34],
        rotationRange: [-25, 25],
        rotationStep: 5,
        gridSize: 4,
        drawOutOfBound: false,
        textStyle: {
          fontFamily: "Noto Serif SC, Source Han Serif SC, Microsoft YaHei, serif",
          fontWeight: 700,
          color: () => {
            const colors = ["#207567", "#d59c3e", "#c56d42", "#6f8a5b", "#6377a6", "#8b6532"];
            return colors[Math.floor(Math.random() * colors.length)];
          }
        },
        emphasis: {
          focus: "self",
          textStyle: {
            shadowBlur: 16,
            shadowColor: "rgba(0, 0, 0, 0.35)"
          }
        },
        data:
          props.items.length > 0
            ? props.items.map((item, index) => ({
                name: item.keyword,
                value: Math.max(item.count * 10, 10) + Math.max(0, 20 - index)
              }))
            : createFallbackData()
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

watch(
  () => props.items,
  () => {
    renderChart();
  },
  { deep: true }
);

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  chart?.dispose();
  chart = null;
});
</script>
