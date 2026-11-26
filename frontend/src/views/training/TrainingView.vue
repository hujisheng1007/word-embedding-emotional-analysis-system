<template>
  <main class="practice-page">
    <header class="practice-head">
      <h1>教师研习</h1>
      <p class="practice-muted">从实习或教学中的一个具体问题出发，比较案例做法，查看它们的原文依据和适用条件。</p>
    </header>
    <TrainingConversation />
    <p v-if="error" class="practice-error" role="alert">{{ error }}</p>
    <p v-if="busy" class="practice-status" role="status">{{ busy }}</p>

    <section class="practice-box">
      <div class="practice-row case-heading">
        <h2>{{ searched ? "匹配到的案例" : "已发布案例" }}</h2>
        <button v-if="searched" type="button" class="practice-button" :disabled="!!busy" @click="browse(0)">查看全部案例</button>
        <small v-if="cards.length > 1" class="practice-muted">最多勾选两条并排比较</small>
      </div>
      <p v-if="loaded && !cards.length" class="practice-muted">
        {{ searched ? "这次没有匹配到已发布案例。" : "目前还没有可用于研习的已发布案例。" }}
      </p>
      <div class="practice-casecards">
        <article v-for="card in cards" :key="card.id" class="practice-casecard">
          <h3><RouterLink :to="caseLink(card.id, card.revision)">{{ card.title }}</RouterLink></h3>
          <p v-if="card.actor_name" class="practice-muted">{{ card.actor_name }}</p>
          <p><strong>问题</strong>　{{ card.problem }}</p>
          <p><strong>策略</strong>　{{ card.strategy }}</p>
          <p v-if="card.applicability"><strong>适用条件</strong>　{{ card.applicability }}</p>
          <p v-if="searched" class="practice-muted">
            {{ matchReason(card) }}
          </p>
          <label v-if="cards.length > 1">
            <input v-model="compared" type="checkbox" :value="card.id" :disabled="compared.length >= 2 && !compared.includes(card.id)">
            加入比较
          </label>
        </article>
      </div>
      <div v-if="!searched && (offset || cards.length === 20)" class="practice-row reflections">
        <button class="practice-button" :disabled="!!busy || !offset" @click="browse(offset - 20)">上一页</button>
        <button class="practice-button" :disabled="!!busy || cards.length < 20" @click="browse(offset + 20)">下一页</button>
      </div>
    </section>

    <section v-if="chosen.length === 2" class="practice-box">
      <h2>案例比较</h2>
      <div class="practice-split">
        <article v-for="card in chosen" :key="card.id" class="practice-casecard">
          <h3><RouterLink :to="caseLink(card.id, card.revision)">{{ card.title }}</RouterLink></h3>
          <dl>
            <dt>实际问题</dt><dd>{{ card.problem }}</dd>
            <dt>行动策略</dt><dd>{{ card.strategy }}</dd>
            <dt>适用条件</dt><dd>{{ card.applicability || "该版本暂无研习评注。" }}</dd>
          </dl>
        </article>
      </div>
      <p class="practice-muted">这些做法与自己的教学条件有哪些相同和不同？如果先尝试一步，你会观察什么？</p>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import * as api from "../../api/practice";
import type { CaseCard } from "../../types/practice";
import TrainingConversation from "./TrainingConversation.vue";
import { latestResponse } from "./trainingConversation";
import "../practice/practice.css";

const cards = ref<CaseCard[]>([]);
const compared = ref<string[]>([]);
const searched = ref(false);
const loaded = ref(false);
const offset = ref(0);
const error = ref("");
const busy = ref("");
const chosen = computed(() => cards.value.filter(card => compared.value.includes(card.id)));
function matchReason(card: CaseCard) {
  if (card.match_method === "graph") return "来自同类问题的图谱关联";
  if (card.matched_concepts?.length) {
    const prefix = card.match_method === "semantic" ? "相关教学问题 " : "命中概念 ";
    return prefix + card.matched_concepts.join("、");
  }
  return card.match_method === "semantic" ? "按问题含义匹配" : "标题或案例字段匹配";
}

function caseLink(id: string, revision: number, evidence?: string) {
  return { name: "practice-case", params: { id }, query: { revision, evidence } };
}

async function perform(message: string, action: () => Promise<void>) {
  if (busy.value) return;
  error.value = "";
  busy.value = message;
  try {
    await action();
    loaded.value = true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    busy.value = "";
  }
}

function browse(next: number) {
  return perform("正在加载已发布案例…", async () => {
    cards.value = await api.browseCases(next);
    offset.value = next;
    searched.value = false;
    compared.value = [];
  });
}

watch(latestResponse, response => {
  if (!response) {
    void browse(0);
    return;
  }
  cards.value = response.matches;
  compared.value = [];
  searched.value = true;
  loaded.value = true;
}, { immediate: true });
</script>

<style scoped>
.case-heading { justify-content: space-between; }
.reflections { margin-top: 18px; }
dt { font-weight: 700; margin-top: 9px; }
dd { margin: 2px 0 0; line-height: 1.6; }
</style>
