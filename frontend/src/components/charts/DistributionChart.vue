<template>
  <el-card class="chart-card">
    <template #header>
      <div class="panel-header">
        <span>{{ title }}</span>
      </div>
    </template>
    <div ref="containerRef" class="chart-body"></div>
  </el-card>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";

const props = defineProps<{
  title: string;
  data: Record<string, number>;
}>();

const containerRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

function renderChart(): void {
  if (!containerRef.value) {
    return;
  }

  chart ??= echarts.init(containerRef.value);
  chart.setOption({
    backgroundColor: "transparent",
    color: ["#5cc8ff", "#00e4b8", "#ffb34d", "#ff6f91", "#7a8cff"],
    tooltip: {
      trigger: "item"
    },
    series: [
      {
        type: "pie",
        radius: ["45%", "70%"],
        itemStyle: {
          borderRadius: 12,
          borderColor: "#091425",
          borderWidth: 3
        },
        label: {
          color: "#d7e5f5"
        },
        data: Object.entries(props.data).map(([name, value]) => ({ name, value }))
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
  () => props.data,
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
