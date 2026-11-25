<template>
  <main class="practice-page">
    <RouterLink to="/training">返回教师研习</RouterLink>
    <p v-if="loading" class="practice-status" role="status">正在读取案例…</p>
    <p v-if="error" class="practice-error" role="alert">{{ error }}</p>
    <template v-if="record">
      <header class="practice-head">
        <h1>{{ record.title }}</h1>
        <p class="practice-muted">{{ record.actor_name ? record.actor_name + ' · ' : '' }}案例 v{{ record.revision }} · {{ record.source.title }}</p>
      </header>
      <div class="practice-split">
        <section>
          <article class="practice-box">
            <h2>实践知识单元</h2>
            <dl>
              <div v-for="name in fieldNames" :key="name" class="reading-field">
                <dt>{{ fieldLabels[name] }}</dt>
                <dd>
                  <p v-if="record.fields[name].summary">{{ record.fields[name].summary }}</p>
                  <p v-else class="practice-muted">{{ stateLabels[record.fields[name].state] }}</p>
                  <button v-for="quote in record.fields[name].evidence" :key="quote.id" class="practice-button evidence-button"
                    @click="openEvidence(quote.id)">查看引文 · {{ formatLocator(quote.locator_type, quote.locator_value) }}</button>
                </dd>
              </div>
            </dl>
          </article>
          <article v-if="record.interpretation || record.applicability" class="practice-box">
            <h2>研习评注</h2>
            <p v-if="record.interpretation">{{ record.interpretation }}</p>
            <p v-if="record.applicability"><strong>适用条件</strong>　{{ record.applicability }}</p>
          </article>
        </section>
        <aside>
          <article ref="citationPanel" class="practice-box" aria-label="证据出处">
            <h2>证据出处</h2>
            <p>{{ record.source.citation_text || record.source.title }}</p>
            <p class="practice-muted">原文版本 {{ record.source.data_version }}<span v-if="record.source.source_institution"> · {{ record.source.source_institution }}</span></p>
            <a v-if="sourceUrl" :href="sourceUrl" target="_blank" rel="noopener noreferrer">查看资料来源</a>
            <div v-if="citation" class="reading-field">
              <strong>{{ fieldLabels[citation.field] }} · {{ formatLocator(citation.locator_type, citation.locator_value) }}</strong>
              <blockquote class="practice-quote">{{ citation.quote }}</blockquote>
              <small class="practice-muted">字符 {{ citation.start_char }}–{{ citation.end_char }} · 片段 {{ citation.segment_id }}</small>
            </div>
            <p v-else class="practice-muted">点击字段下的引文，查看原文及其定位。</p>
          </article>
          <article v-if="graph" class="practice-box">
            <h2>案例图谱</h2>
            <CaseGraph :graph="graph" @select="selectGraphNode"/>
            <ul v-if="concepts.length" class="practice-pills">
              <li v-for="concept in concepts" :key="concept.id">{{ concept.label }}</li>
            </ul>
            <h3 v-if="related.length">同类问题案例</h3>
            <ul class="practice-list">
              <li v-for="item in related" :key="item.id">
                <RouterLink :to="{ name: 'practice-case', params: { id: item.case_id }, query: { revision: item.revision } }">
                  {{ item.label }}
                </RouterLink>
              </li>
            </ul>
          </article>
        </aside>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import * as api from "../../api/practice";
import {
  fieldLabels, fieldNames, formatLocator, stateLabels,
  type CaseGraphData, type GraphNode, type LocatedEvidence, type PublishedCase
} from "../../types/practice";
import CaseGraph from "./CaseGraph.vue";
import "../practice/practice.css";

const route = useRoute();
const router = useRouter();
const record = ref<PublishedCase | null>(null);
const graph = ref<CaseGraphData | null>(null);
const citation = ref<LocatedEvidence | null>(null);
const citationPanel = ref<HTMLElement | null>(null);
const error = ref("");
const loading = ref(false);
let loadGeneration = 0;
const concepts = computed(() => record.value?.concepts ?? []);
const related = computed(() => graph.value?.nodes.filter(node => node.id !== graph.value?.center && node.kind === "case") ?? []);
const sourceUrl = computed(() => {
  try {
    const url = new URL(record.value?.source.source_url ?? "");
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
});

function openEvidence(id: string) {
  if (route.query.evidence === id) {
    citationPanel.value?.scrollIntoView({ block: "nearest" });
    return;
  }
  return router.replace({ query: { ...route.query, evidence: id } });
}

function selectGraphNode(node: GraphNode) {
  if (node.evidence_id) return openEvidence(node.evidence_id);
  if (node.case_id && node.case_id !== record.value?.case_id) {
    return router.push({ name: "practice-case", params: { id: node.case_id }, query: { revision: node.revision } });
  }
}

watch(() => [route.params.id, route.query.revision], async () => {
  const generation = ++loadGeneration;
  const id = String(route.params.id ?? "");
  const rawRevision = typeof route.query.revision === "string" ? route.query.revision : "";
  const revision = /^[1-9]\d*$/.test(rawRevision) ? Number(rawRevision) : undefined;
  error.value = "";
  record.value = null;
  graph.value = null;
  loading.value = true;
  try {
    const document = await api.publishedCase(id, revision);
    if (generation !== loadGeneration) return;
    record.value = document;
    const view = await api.caseGraph(id, document.revision);
    if (generation === loadGeneration) graph.value = view;
  } catch (e) {
    if (generation === loadGeneration) error.value = e instanceof Error ? e.message : String(e);
  } finally {
    if (generation === loadGeneration) loading.value = false;
  }
}, { immediate: true });

watch([record, () => route.query.evidence], async ([document, evidenceId], _, onCleanup) => {
  let cancelled = false;
  onCleanup(() => { cancelled = true; });
  citation.value = null;
  if (!document || typeof evidenceId !== "string") return;
  try {
    const located = await api.locateEvidence(document.case_id, document.revision, evidenceId);
    if (cancelled) return;
    citation.value = located;
    await nextTick();
    citationPanel.value?.scrollIntoView({ block: "nearest" });
  } catch (e) {
    if (!cancelled) error.value = e instanceof Error ? e.message : String(e);
  }
}, { immediate: true });
</script>

<style scoped>
.reading-field { padding: 12px 0; border-top: 1px solid var(--practice-border); }
dt { font-weight: 700; }
dd { margin: 3px 0 0; }
dd p { margin: 3px 0; }
.evidence-button { margin: 4px 7px 2px 0; }
blockquote { padding-left: 12px; border-left: 3px solid var(--practice-accent); }
</style>
