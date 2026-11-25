<template>
  <main class="practice-page">
    <header class="practice-head">
      <h1>教师研习</h1>
      <p class="practice-muted">从实习或教学中的一个具体问题出发，比较案例做法，查看它们的原文依据和适用条件。</p>
    </header>
    <form class="practice-box practice-form practice-stack" @submit.prevent="search">
      <label>你遇到了什么教学问题？
        <textarea v-model.trim="query" maxlength="1000" :disabled="!!busy"
          placeholder="例如：小组讨论时，总是同几名学生在发言。我怎样组织讨论？"/>
      </label>
      <div class="practice-row">
        <button class="practice-button primary" :disabled="!!busy || !query">匹配案例</button>
        <button class="practice-button" type="button" :disabled="!!busy || !query" @click="answer">生成带引证的回答</button>
        <button v-if="searched" type="button" class="practice-button" :disabled="!!busy" @click="browse(0)">查看全部案例</button>
      </div>
    </form>
    <p v-if="error" class="practice-error" role="alert">{{ error }}</p>
    <p v-if="busy" class="practice-status" role="status">{{ busy }}</p>

    <section v-if="result" class="practice-box" aria-label="案例问答">
      <h2>{{ result.mode === "grounded" ? "案例回答" : "原文证据" }}</h2>
      <p v-if="result.message" class="practice-status">{{ result.message }}</p>
      <ul class="practice-list">
        <li v-for="(claim, index) in result.claims" :key="index">
          <p>{{ claim.text }}</p>
          <ul class="practice-list">
            <li v-for="quote in claim.evidence" :key="quote.id">
              <RouterLink :to="caseLink(quote.case_id, quote.revision, quote.id)">
                {{ quote.case_title }} · {{ formatLocator(quote.locator_type, quote.locator_value) }} · {{ fieldLabels[quote.field] }}
              </RouterLink>
            </li>
          </ul>
        </li>
      </ul>
      <template v-if="result.reflection_questions.length">
        <h3 class="reflections">实践反思</h3>
        <ul><li v-for="question in result.reflection_questions" :key="question">{{ question }}</li></ul>
      </template>
    </section>

    <section class="practice-box">
      <div class="practice-row case-heading">
        <h2>{{ searched ? "匹配到的案例" : "已发布案例" }}</h2>
        <small v-if="cards.length > 1" class="practice-muted">最多勾选两条并排比较</small>
      </div>
      <p v-if="loaded && !cards.length" class="practice-muted">
        {{ searched ? "当前问题未匹配到案例。可补充具体情境或换一种描述。" : "目前还没有可用于研习的已发布案例。" }}
      </p>
      <div class="practice-casecards">
        <article v-for="card in cards" :key="card.id" class="practice-casecard">
          <h3><RouterLink :to="caseLink(card.id, card.revision)">{{ card.title }}</RouterLink></h3>
          <p v-if="card.actor_name" class="practice-muted">{{ card.actor_name }}</p>
          <p><strong>问题</strong>　{{ card.problem }}</p>
          <p><strong>策略</strong>　{{ card.strategy }}</p>
          <p v-if="card.applicability"><strong>适用条件</strong>　{{ card.applicability }}</p>
          <p v-if="searched" class="practice-muted">
            {{ card.matched_concepts?.length ? "命中概念 " + card.matched_concepts.join("、") : "标题或案例字段匹配" }}
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
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import * as api from "../../api/practice";
import { fieldLabels, formatLocator, type CaseCard, type TrainingAnswer } from "../../types/practice";
import "../practice/practice.css";

const query = ref("");
const cards = ref<CaseCard[]>([]);
const compared = ref<string[]>([]);
const result = ref<TrainingAnswer | null>(null);
const searched = ref(false);
const loaded = ref(false);
const offset = ref(0);
const error = ref("");
const busy = ref("");
const chosen = computed(() => cards.value.filter(card => compared.value.includes(card.id)));

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
    result.value = null;
    compared.value = [];
  });
}

function search() {
  if (!query.value) return;
  const question = query.value;
  return perform("正在匹配案例…", async () => {
    cards.value = await api.searchCases(question);
    result.value = null;
    compared.value = [];
    searched.value = true;
  });
}

function answer() {
  if (!query.value) return;
  const question = query.value;
  return perform("正在查找证据并准备回答…", async () => {
    result.value = null;
    const [matches, response] = await Promise.all([api.searchCases(question), api.ask(question)]);
    cards.value = matches;
    result.value = response;
    compared.value = [];
    searched.value = true;
  });
}

onMounted(() => browse(0));
</script>

<style scoped>
.case-heading { justify-content: space-between; }
.reflections { margin-top: 18px; }
dt { font-weight: 700; margin-top: 9px; }
dd { margin: 2px 0 0; line-height: 1.6; }
</style>
