<template>
  <div ref="canvas" class="case-graph" aria-label="案例图谱" role="img"/>
</template>

<script setup lang="ts">
import * as echarts from "echarts";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { CaseGraphData, GraphNode } from "../../types/practice";

const props = defineProps<{ graph: CaseGraphData }>();
const emit = defineEmits<{ select: [node: GraphNode] }>();
const canvas = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | undefined;
let observer: ResizeObserver | undefined;
const colors = {
  case: "#1d6557", actor: "#4e7284", context: "#8b6a39",
  problem: "#a55733", strategy: "#4e723d", evidence: "#7d8472"
};

function draw() {
  if (!chart) return;
  chart.setOption({
    animation: false,
    tooltip: { trigger: "item", renderMode: "richText" },
    series: [{
      type: "graph", layout: "force", roam: true, draggable: true,
      force: { repulsion: 245, edgeLength: [72, 130], friction: 0.5 },
      label: { show: true, color: "#233b38", width: 115, overflow: "truncate", position: "right" },
      lineStyle: { color: "#9aab9b", opacity: 0.75 },
      edgeSymbol: ["none", "arrow"], edgeSymbolSize: 5,
      emphasis: { focus: "adjacency", edgeLabel: { show: true, formatter: "{c}" } },
      data: props.graph.nodes.map(node => ({
        id: node.id, name: node.label, symbolSize: node.id === props.graph.center ? 24 : 14,
        itemStyle: { color: colors[node.kind] }
      })),
      links: props.graph.edges.map(edge => ({
        source: edge.source, target: edge.target, value: edge.relation
      }))
    }]
  }, { notMerge: true });
}

onMounted(() => {
  if (!canvas.value) return;
  chart = echarts.init(canvas.value, undefined, { renderer: "canvas" });
  chart.on("click", event => {
    if (event.dataType !== "node") return;
    const data = event.data as { id?: string } | undefined;
    const node = props.graph.nodes.find(item => item.id === data?.id);
    if (node) emit("select", node);
  });
  observer = new ResizeObserver(() => chart?.resize());
  observer.observe(canvas.value);
  draw();
});
watch(() => props.graph, draw);
onBeforeUnmount(() => {
  observer?.disconnect();
  chart?.dispose();
});
</script>

<style scoped>
.case-graph { height: 360px; min-width: 0; border: 1px solid var(--practice-border); border-radius: 8px; }
@media (max-width: 650px) { .case-graph { height: 290px; } }
</style>
