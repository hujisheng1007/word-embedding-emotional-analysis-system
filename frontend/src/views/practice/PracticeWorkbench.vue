<template>
  <main class="practice-page">
    <header class="practice-head">
      <h1>典范实践工作台</h1>
      <p class="practice-muted">从教育叙事选取事件、为字段添加原文引证，再复核发布到教师研习。</p>
    </header>
    <TrainingConversation />
    <p v-if="error" class="practice-error" role="alert">{{ error }}</p>
    <p v-if="notice" class="practice-status" role="status">{{ notice }}</p>
    <div class="practice-grid">
      <aside>
        <section class="practice-box practice-form practice-stack">
          <h2>研究资料</h2>
          <form class="practice-row" @submit.prevent="refreshResources">
            <input v-model="keyword" aria-label="资料关键词" placeholder="搜索标题或人物">
            <button class="practice-button" :disabled="busy">搜索</button>
          </form>
          <label>选择资料
            <select v-model="resourceId" :disabled="busy" @change="changeResource">
              <option value="">全部案例</option>
              <option v-for="item in resources" :key="item.id" :value="item.id">{{ item.title }}</option>
            </select>
          </label>
          <RouterLink to="/resources">前往资源库导入资料</RouterLink>
        </section>
        <section class="practice-box">
          <h2>案例草稿</h2>
          <p v-if="!entries.length" class="practice-muted">当前范围还没有案例。</p>
          <ul class="practice-list">
            <li v-for="item in entries" :key="item.id">
              <button class="practice-button" :disabled="busy" @click="openCase(item.id)">{{ item.title }}</button>
              <small class="entry-meta">
                {{ item.published_revision ? '已发布 v' + item.published_revision : '未发布' }} · 草稿 v{{ item.draft_revision }}
              </small>
            </li>
          </ul>
          <div v-if="caseOffset || entries.length === 50" class="practice-row">
            <button class="practice-button" :disabled="busy || !caseOffset" @click="pageCases(-50)">上一页</button>
            <button class="practice-button" :disabled="busy || entries.length < 50" @click="pageCases(50)">下一页</button>
          </div>
        </section>
      </aside>

      <div>
        <section v-if="resource" class="practice-box">
          <h2>{{ resource.title }}</h2>
          <p v-if="!resource.fulltext_allowed || !resource.segments.length" class="practice-muted">这份资料当前没有可选的授权原文片段。</p>
          <template v-else>
            <p class="practice-muted">选择一个事件的连续原文片段。已选 {{ selected.length }} 段，最多 30 段。</p>
            <div class="segment-picker">
              <label v-for="span in visibleSegments" :key="span.id">
                <input v-model="selected" type="checkbox" :value="span.id" :disabled="busy">
                <span><strong>{{ span.locator_value }}</strong> {{ span.text.slice(0, 160) }}</span>
              </label>
            </div>
            <div v-if="resource.segments.length > 12" class="practice-row page-controls">
              <button class="practice-button" :disabled="!sourceOffset" @click="sourceOffset -= 12">上一组片段</button>
              <span>{{ sourceOffset + 1 }}–{{ Math.min(sourceOffset + 12, resource.segments.length) }}</span>
              <button class="practice-button" :disabled="sourceOffset + 12 >= resource.segments.length" @click="sourceOffset += 12">下一组片段</button>
            </div>
            <form class="practice-form practice-row page-controls" @submit.prevent="makeDraft">
              <label class="grow">新案例标题
                <input v-model.trim="newTitle" maxlength="200" placeholder="用一句话概括事件">
              </label>
              <button class="practice-button primary" :disabled="busy || !canSelect || !newTitle">手工建草稿</button>
              <button class="practice-button" type="button" :disabled="busy || !canSelect" @click="queueExtraction">模型抽取</button>
            </form>
          </template>
        </section>

        <section v-if="runs.length" class="practice-box">
          <h2>模型抽取记录</h2>
          <details v-for="run in runs" :key="run.id" class="run-row">
            <summary>{{ run.config.model }} · {{ runLabels[run.status] }} · {{ displayDate(run.created_at) }}</summary>
            <p v-if="run.error" class="practice-error">{{ run.error }}</p>
            <button v-if="run.can_retry" class="practice-button" :disabled="busy" @click="retryRun(run.id)">继续或重试</button>
            <p v-if="run.status === 'succeeded' && !run.candidates.length">所选范围未识别到可提取的教育事件。</p>
            <ul class="practice-list">
              <li v-for="(candidate, index) in run.candidates" :key="index">
                <strong>{{ candidate.content.title }}</strong>
                <p>{{ candidate.content.fields.problem.summary }}</p>
                <button class="practice-button" :disabled="busy" @click="accept(run.id, index)">载入为待复核草稿</button>
              </li>
            </ul>
          </details>
        </section>

        <section v-if="active" class="practice-box" aria-label="案例编辑">
          <div class="practice-row editor-title">
            <h2>{{ active.title }}</h2>
            <span class="practice-muted">v{{ active.revision }} · {{ revisionStatus }}</span>
          </div>
          <div class="practice-row page-controls">
            <label>查看版本
              <select :value="active.revision" :disabled="busy" @change="changeRevision">
                <option v-for="item in active.history" :key="item.revision" :value="item.revision">
                  v{{ item.revision }}{{ item.published_at ? ' · 有发布记录' : '' }}
                </option>
              </select>
            </label>
            <RouterLink v-if="active.published_revision" :to="{ name: 'practice-case', params: { id: active.case_id } }">查看研习案例</RouterLink>
          </div>
          <p v-if="active.reviewer" class="practice-muted">复核人 {{ active.reviewer }}<span v-if="active.review_note"> · {{ active.review_note }}</span></p>

          <div class="practice-split">
            <section class="practice-stack">
              <div class="practice-form">
                <h3>原文 · {{ active.source.title }}</h3>
                <label v-if="editable">引文添加到
                  <select v-model="targetField">
                    <option v-for="name in fieldNames" :key="name" :value="name">{{ fieldLabels[name] }}</option>
                  </select>
                </label>
              </div>
              <p v-if="editable" class="practice-muted">可选中文字后点击「添加引文」，也可引用整段短文本。</p>
              <article v-for="span in active.source.spans" :key="span.segment_id" class="practice-field">
                <div class="practice-row">
                  <strong>{{ span.locator_value }}</strong>
                  <button v-if="editable" class="practice-button" :disabled="busy"
                    @mousedown.prevent @click="addCitation(span)">添加引文</button>
                </div>
                <p :id="'practice-span-' + span.segment_id" class="practice-quote">{{ span.text }}</p>
              </article>
            </section>

            <section class="practice-form practice-stack">
              <label>案例标题<input v-model.trim="form.title" :disabled="!editable || busy" maxlength="200"></label>
              <label>行动主体<input v-model.trim="form.actor_name" :disabled="!editable || busy" maxlength="150"></label>
              <fieldset v-for="name in fieldNames" :key="name" class="practice-field practice-stack" :disabled="!editable || busy">
                <legend>{{ fieldLabels[name] }}</legend>
                <select v-model="form.fields[name].state" :aria-label="fieldLabels[name] + '证据状态'">
                  <option v-for="(label, value) in stateLabels" :key="value" :value="value">{{ label }}</option>
                </select>
                <textarea v-model.trim="form.fields[name].summary" :aria-label="fieldLabels[name] + '说明'" maxlength="2000"/>
                <div v-for="(quote, index) in form.fields[name].evidence" :key="index" class="quote-editor">
                  <div class="practice-row">
                    <small>{{ locator(quote.segment_id) }}</small>
                    <button v-if="editable" class="practice-button" @click="form.fields[name].evidence.splice(index, 1)">移除引文</button>
                  </div>
                  <textarea :aria-label="fieldLabels[name] + '引文 ' + (index + 1)" :value="quote.quote"
                    maxlength="1500" @input="editCitation(quote, $event)"/>
                </div>
              </fieldset>
              <label>研习解读<textarea v-model.trim="form.interpretation" :disabled="!editable || busy" maxlength="2000"/></label>
              <label>适用条件<textarea v-model.trim="form.applicability" :disabled="!editable || busy" maxlength="2000"/></label>
              <details class="practice-field">
                <summary>图谱概念</summary>
                <ul v-if="!editable" class="practice-pills"><li v-for="item in active.concepts" :key="item.id">{{ item.label }}</li></ul>
                <template v-else>
                  <div class="concept-picker">
                    <label v-for="concept in availableConcepts" :key="concept.id" class="practice-check">
                      <input v-model="form.concept_ids" type="checkbox" :value="concept.id" :disabled="busy">
                      {{ fieldLabels[concept.kind] }} · {{ concept.label }}
                    </label>
                  </div>
                  <div class="practice-stack">
                    <label>概念类型
                      <select v-model="conceptKind" :disabled="busy">
                        <option value="context">情境</option><option value="problem">问题</option><option value="strategy">策略</option>
                      </select>
                    </label>
                    <label>规范词<input v-model.trim="conceptLabel" :disabled="busy" maxlength="100"></label>
                    <label>别名<input v-model.trim="conceptAliases" :disabled="busy" placeholder="用逗号分隔"></label>
                    <button class="practice-button" :disabled="busy || !conceptLabel" @click="addConcept">加入规范词并关联</button>
                  </div>
                </template>
              </details>
              <div v-if="editable" class="practice-row">
                <button class="practice-button primary" :disabled="busy || !canSave || !form.title" @click="saveDraft">保存新版本</button>
                <button class="practice-button" :disabled="busy || dirty || !!active.submitted_at" @click="submitDraft">提交复核</button>
                <small v-if="dirty" class="practice-muted">保存后可提交当前修改。</small>
              </div>
            </section>
          </div>

          <form v-if="editable && active.submitted_at && !active.published_at" class="review-panel practice-form practice-stack"
            @submit.prevent="publishDraft">
            <h3>复核并发布</h3>
            <label>复核人<input v-model.trim="reviewer" maxlength="100" :disabled="busy" required></label>
            <label>复核说明<textarea v-model.trim="reviewNote" maxlength="2000" :disabled="busy"/></label>
            <label class="practice-check"><input v-model="confirmed" type="checkbox" :disabled="busy">已复核事件主体、边界及引文对字段的支持。</label>
            <label class="practice-check"><input v-model="trainingAllowed" type="checkbox" :disabled="busy">确认此案例及所选引文获准用于研习。</label>
            <button class="practice-button primary" :disabled="busy || dirty || !reviewer || !confirmed || !trainingAllowed">发布到教师研习</button>
          </form>
          <button v-if="active.published_revision" class="practice-button withdraw" :disabled="busy" @click="withdrawPublished">撤回发布</button>
        </section>
        <section v-else-if="!resource" class="practice-box practice-muted">
          选择一份资料开始选段，或打开已有案例继续复核。
        </section>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import * as api from "../../api/practice";
import { moralDetail } from "../../api/moral";
import { getResearchResource, listResearchResources } from "../../api/research";
import type { ResearchResourceDetail, ResearchResourceSummary } from "../../types/research";
import {
  blankContent, contentFromCase, fieldLabels, fieldNames, stateLabels,
  type CaseEntry, type Citation, type Concept, type ConceptKind, type ExtractionRun,
  type FieldName, type PracticeCase, type SourceSpan
} from "../../types/practice";
import "./practice.css";
import TrainingConversation from "../training/TrainingConversation.vue";

const route = useRoute();
const keyword = ref("");
const resources = ref<ResearchResourceSummary[]>([]);
const resourceId = ref("");
const resource = ref<ResearchResourceDetail | null>(null);
const sourceOffset = ref(0);
const caseOffset = ref(0);
const selected = ref<string[]>([]);
const newTitle = ref("");
const entries = ref<CaseEntry[]>([]);
const runs = ref<ExtractionRun[]>([]);
const availableConcepts = ref<Concept[]>([]);
const active = ref<PracticeCase | null>(null);
const form = ref(blankContent());
const savedContent = ref("");
const error = ref("");
const notice = ref("");
const busy = ref(false);
const targetField = ref<FieldName>("context");
const reviewer = ref("");
const reviewNote = ref("");
const confirmed = ref(false);
const trainingAllowed = ref(false);
const conceptKind = ref<ConceptKind>("problem");
const conceptLabel = ref("");
const conceptAliases = ref("");
const runLabels = { queued: "排队中", running: "抽取中", failed: "失败", succeeded: "已完成" };
let pollTimer: ReturnType<typeof setInterval> | undefined;
let requestSignature = "";
let requestId: string | undefined;
let polling = false;

const visibleSegments = computed(() => resource.value?.segments.slice(sourceOffset.value, sourceOffset.value + 12) ?? []);
const canSelect = computed(() => selected.value.length > 0 && selected.value.length <= 30);
const editable = computed(() => active.value?.revision === active.value?.draft_revision);
const dirty = computed(() => !!active.value && savedContent.value !== JSON.stringify(form.value));
const canSave = computed(() => dirty.value || !!(active.value?.published_at && !active.value.published_revision));
const revisionStatus = computed(() => {
  if (active.value?.revision === active.value?.published_revision) return "当前发布版";
  if (active.value?.published_at) return "历史发布版";
  return active.value?.submitted_at ? "待复核" : "草稿";
});

function displayDate(value: string) {
  return new Date(value + "Z").toLocaleString();
}

async function perform(action: () => Promise<void>, success = "") {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  notice.value = "";
  try {
    await action();
    notice.value = success;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    busy.value = false;
  }
}

function mayChangeCase() {
  return !dirty.value || !editable.value || window.confirm("当前修改尚未保存，切换将丢弃这些修改。继续切换？");
}

async function loadWorkspaceLists() {
  [entries.value, runs.value] = await Promise.all([
    api.caseEntries(resourceId.value, caseOffset.value), api.extractions(resourceId.value)
  ]);
}

async function loadSource() {
  resource.value = resourceId.value ? await getResearchResource(resourceId.value) : null;
  selected.value = [];
  newTitle.value = "";
  sourceOffset.value = 0;
  caseOffset.value = 0;
  if (resource.value && !resources.value.some(item => item.id === resourceId.value)) {
    resources.value.unshift(resource.value);
  }
  await loadWorkspaceLists();
}

function changeResource() {
  return perform(loadSource);
}

async function refreshResources() {
  return perform(async () => {
    const result = await listResearchResources({ keyword: keyword.value, limit: 100 });
    resources.value = result.items.filter(item => item.fulltext_allowed && item.segment_count > 0);
    if (resource.value && !resources.value.some(item => item.id === resourceId.value)) resources.value.unshift(resource.value);
  });
}

function pageCases(step: number) {
  return perform(async () => {
    const next = caseOffset.value + step;
    entries.value = await api.caseEntries(resourceId.value, next);
    caseOffset.value = next;
  });
}

function setActive(document: PracticeCase) {
  active.value = document;
  form.value = contentFromCase(document);
  savedContent.value = JSON.stringify(form.value);
  confirmed.value = false;
  trainingAllowed.value = false;
  reviewNote.value = "";
}

function openCase(caseId: string, revision?: number) {
  if (!mayChangeCase()) return;
  return perform(async () => setActive(await api.caseDetail(caseId, revision)));
}

function changeRevision(event: Event) {
  const input = event.target as HTMLSelectElement;
  const activeCase = active.value;
  if (!activeCase) return;
  const selectedVersion = Number(input.value);
  input.value = String(activeCase.revision);
  return openCase(activeCase.case_id, selectedVersion);
}

function makeDraft() {
  if (!mayChangeCase()) return;
  return perform(async () => {
    const signature = JSON.stringify([resourceId.value, [...selected.value].sort(), newTitle.value]);
    if (requestSignature !== signature) {
      requestSignature = signature;
      requestId = globalThis.crypto?.randomUUID?.();
    }
    setActive(await api.createCase(resourceId.value, selected.value, blankContent(newTitle.value), requestId));
    newTitle.value = "";
    requestSignature = "";
    await loadWorkspaceLists();
  }, "已创建草稿，可以逐字段添加原文证据。");
}

function queueExtraction() {
  return perform(async () => {
    await api.extract(resourceId.value, selected.value);
    await loadWorkspaceLists();
  }, "抽取任务已登记。完成后可在任务记录中查看候选。");
}

function retryRun(runId: string) {
  return perform(async () => {
    await api.retryExtraction(runId);
    await loadWorkspaceLists();
  }, "已安排抽取任务。");
}

function accept(runId: string, index: number) {
  if (!mayChangeCase()) return;
  return perform(async () => {
    setActive(await api.acceptCandidate(runId, index));
    await loadWorkspaceLists();
  }, "候选已载入。请核验事件边界、行动主体与引文。");
}

function saveDraft() {
  const document = active.value;
  if (!document) return;
  return perform(async () => {
    setActive(await api.saveCase(document.case_id, document.version, form.value));
    await loadWorkspaceLists();
  }, "新版本已保存。");
}

function submitDraft() {
  const document = active.value;
  if (!document) return;
  return perform(async () => {
    setActive(await api.submitCase(document.case_id, document.version));
    await loadWorkspaceLists();
  }, "已提交复核。");
}

function publishDraft() {
  const document = active.value;
  if (!document) return;
  return perform(async () => {
    setActive(await api.publishCase(
      document.case_id, document.version, reviewer.value, reviewNote.value, trainingAllowed.value, confirmed.value
    ));
    await loadWorkspaceLists();
  }, "已发布到教师研习。");
}

function withdrawPublished() {
  const document = active.value;
  if (!document || !window.confirm("撤回后，研习端将无法访问该案例及引文。确认撤回？")) return;
  return perform(async () => {
    setActive(await api.withdrawCase(document.case_id, document.version));
    await loadWorkspaceLists();
  }, "已撤回发布。");
}

function locator(segmentId: string) {
  return active.value?.source.spans.find(span => span.segment_id === segmentId)?.locator_value ?? segmentId;
}

function addCitation(span: SourceSpan) {
  error.value = "";
  const selection = window.getSelection();
  const element = document.getElementById("practice-span-" + span.segment_id);
  const range = selection?.rangeCount ? selection.getRangeAt(0) : null;
  let quote = span.text;
  let start = 0;
  if (element && range && !range.collapsed && element.contains(range.startContainer) && element.contains(range.endContainer)) {
    const prefix = range.cloneRange();
    prefix.selectNodeContents(element);
    prefix.setEnd(range.startContainer, range.startOffset);
    start = Array.from(prefix.toString()).length;
    quote = range.toString();
  }
  const length = Array.from(quote).length;
  if (!quote.trim() || length > 1500) {
    error.value = "请选取一段原文作为引文，长度应在 1 到 1,500 字符之间。";
    return;
  }
  const evidence = form.value.fields[targetField.value].evidence;
  if (evidence.length >= 8) {
    error.value = "每个字段最多添加 8 条引文。";
    return;
  }
  if (!evidence.some(item => item.segment_id === span.segment_id && item.start_char === start && item.quote === quote)) {
    evidence.push({ segment_id: span.segment_id, quote, start_char: start, end_char: start + length });
  }
  selection?.removeAllRanges();
}

function editCitation(quote: Citation, event: Event) {
  quote.quote = (event.target as HTMLTextAreaElement).value;
  quote.start_char = null;
  quote.end_char = null;
}

function addConcept() {
  return perform(async () => {
    const aliases = conceptAliases.value.split(/[,，、]/).map(item => item.trim()).filter(Boolean);
    const concept = await api.createConcept(conceptKind.value, conceptLabel.value, aliases);
    availableConcepts.value.push(concept);
    form.value.concept_ids.push(concept.id);
    conceptLabel.value = "";
    conceptAliases.value = "";
  });
}

onMounted(async () => {
  await perform(async () => {
    const [catalog, words] = await Promise.all([listResearchResources({ limit: 100 }), api.concepts()]);
    resources.value = catalog.items.filter(item => item.fulltext_allowed && item.segment_count > 0);
    availableConcepts.value = words;
    const eventId = typeof route.query.event === "string" ? route.query.event : "";
    if (eventId) {
      const event = await moralDetail(eventId);
      resourceId.value = event.resource_id;
      await loadSource();
      selected.value = event.snapshot.spans.map(span => span.segment_id);
      const first = resource.value?.segments.findIndex(span => span.id === selected.value[0]) ?? -1;
      if (first >= 0) sourceOffset.value = Math.floor(first / 12) * 12;
    } else {
      resourceId.value = typeof route.query.resource === "string" ? route.query.resource : "";
      await loadSource();
    }
  });
  pollTimer = setInterval(async () => {
    if (polling || busy.value || !runs.value.some(run => run.status === "running" || run.status === "queued")) return;
    polling = true;
    const current = resourceId.value;
    try {
      const latest = await api.extractions(current);
      if (resourceId.value === current && !busy.value) runs.value = latest;
    } catch {
      // The next poll retries transient errors.
    } finally {
      polling = false;
    }
  }, 2500);
});

onBeforeUnmount(() => clearInterval(pollTimer));
</script>

<style scoped>
.grow { flex: 1 1 250px; }
.entry-meta { display: block; margin-top: 5px; color: var(--practice-muted); }
.segment-picker { display: grid; gap: 5px; }
.segment-picker label { display: flex; gap: 9px; align-items: start; padding: 6px 0; line-height: 1.55; }
.page-controls { margin-block: 12px; }
.editor-title h2 { margin: 0; flex: 1; }
.run-row { padding: 10px 0; border-top: 1px solid var(--practice-border); }
.run-row summary, details summary { cursor: pointer; }
.quote-editor { border-left: 2px solid var(--practice-border); padding-left: 8px; }
.quote-editor textarea { margin-top: 4px; }
.concept-picker { max-height: 210px; overflow: auto; margin: 10px 0; }
.review-panel { border-top: 1px solid var(--practice-border); margin-top: 24px; padding-top: 17px; }
.withdraw { margin-top: 18px; }
</style>
