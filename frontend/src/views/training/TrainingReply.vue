<template>
  <section class="training-reply" :lang="result.language">
    <h3>{{ answerLabels.title }}</h3>
    <p v-if="!result.model" class="practice-muted model-status">{{ answerLabels.modelFallback }}</p>
    <p v-if="result.answer || result.message" class="answer-copy" :lang="result.language">
      {{ result.answer || result.message }}
    </p>
    <div v-if="result.next_step || result.clarifying_question" class="answer-actions" :lang="result.language">
      <div v-if="result.next_step">
        <h3>{{ answerLabels.nextStep }}</h3>
        <p>{{ result.next_step }}</p>
      </div>
      <div v-if="result.clarifying_question">
        <h3>{{ answerLabels.question }}</h3>
        <p>{{ result.clarifying_question }}</p>
      </div>
    </div>
    <h3 v-if="result.claims.length" class="reflections">
      {{ result.evidence_fit === "indirect" ? answerLabels.relatedEvidence : answerLabels.caseEvidence }}
    </h3>
    <ul v-if="result.claims.length" class="practice-list">
      <li v-for="(claim, index) in result.claims" :key="index">
        <p>{{ claim.text }}</p>
        <ul class="practice-list">
          <li v-for="quote in claim.evidence" :key="quote.id">
            <details v-if="quote.kind === 'interview'">
              <summary>{{ quote.source_title }} · {{ answerLabels.interviewRecord }} {{ quote.locator_value }}</summary>
              <blockquote class="practice-quote">{{ quote.quote }}</blockquote>
              <small class="practice-muted">{{ quote.source_file }}</small>
            </details>
            <RouterLink v-else :to="caseLink(quote.case_id, quote.revision, quote.id)">
              {{ quote.case_title }} · {{ formatLocator(quote.locator_type, quote.locator_value) }} · {{ fieldLabels[quote.field] }}
            </RouterLink>
          </li>
        </ul>
      </li>
    </ul>
    <template v-if="result.reflection_questions.length">
      <h3 class="reflections">{{ answerLabels.reflection }}</h3>
      <ul><li v-for="question in result.reflection_questions" :key="question">{{ question }}</li></ul>
    </template>
    <section v-if="result.related_resources?.length" class="reflections">
      <h3>{{ answerLabels.localMaterials }}</h3>
      <ul class="practice-list">
        <li v-for="hit in result.related_resources" :key="hit.segment_id">
          <details>
            <summary>{{ hit.resource_title }} · {{ formatLocator(hit.locator_type, hit.locator_value) }}</summary>
            <blockquote class="practice-quote">{{ hit.excerpt }}</blockquote>
            <RouterLink :to="{ name: 'resources', query: { resource: hit.resource_id, segment: hit.segment_id } }">
              {{ answerLabels.viewMaterial }}
            </RouterLink>
          </details>
        </li>
      </ul>
    </section>
    <details v-if="result.lookup_trace?.length" class="reflections">
      <summary>{{ answerLabels.trace }}</summary>
      <ul>
        <li v-for="(step, index) in result.lookup_trace" :key="index">
          {{ answerLabels.lookup[step.action] }} ({{ step.count }})
        </li>
      </ul>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { fieldLabels, formatLocator, type TrainingAnswer } from "../../types/practice";

const props = defineProps<{ result: TrainingAnswer }>();
const answerLabels = computed(() => props.result.language === "en" ? {
  title: "Answer", nextStep: "What to check next", question: "One question to clarify",
  relatedEvidence: "Related evidence", caseEvidence: "Evidence", reflection: "Reflection", interviewRecord: "Interview record",
  modelFallback: "Showing database results. A model-generated reply is unavailable.",
  localMaterials: "Related library materials", viewMaterial: "Open matched passage",
  trace: "Show database lookup", lookup: {
    catalog: "Catalog records loaded", search: "Published cases found", graph: "Related cases found",
    evidence: "Citations retrieved", context: "Case records retrieved for this reply",
    interview_scan: "Interview rows searched", interview_context: "Interview excerpts provided to the model",
  },
} : {
  title: "研习回答", nextStep: "建议先核实", question: "需要确认的问题",
  relatedEvidence: "相关依据", caseEvidence: "回答依据", reflection: "实践反思", interviewRecord: "访谈记录",
  modelFallback: "模型回答暂不可用，以下根据数据库检索结果展示。",
  localMaterials: "相关资料库原文", viewMaterial: "定位原文片段",
  trace: "查看数据库检索过程", lookup: {
    catalog: "读取案例目录", search: "检索已发布案例", graph: "沿图谱查找同类案例",
    evidence: "读取原文引证", context: "读取本次回答所用的案例记录",
    interview_scan: "扫描教育家访谈语料记录", interview_context: "筛选供回答参考的访谈引文",
  },
});

function caseLink(id: string, revision: number, evidence?: string) {
  return { name: "practice-case", params: { id }, query: { revision, evidence } };
}
</script>

<style scoped>
.training-reply { border: 1px solid var(--practice-border); border-radius: 9px; padding: 14px 16px; }
.training-reply h3 { font-size: 1rem; }
.model-status { margin: 0 0 7px; font-size: .92rem; }
.answer-copy { max-width: 75ch; font-size: 1.05rem; line-height: 1.65; }
.answer-actions { max-width: 75ch; border-inline-start: 3px solid currentColor; padding-inline-start: 1rem; }
.answer-actions h3 { margin: 0.9rem 0 0.25rem; }
.answer-actions p { margin: 0; line-height: 1.6; }
.reflections { margin-top: 18px; }
</style>
