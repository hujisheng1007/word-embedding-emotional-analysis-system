<template>
  <section class="practice-box training-conversation">
    <div class="practice-row conversation-heading">
      <h2>教学对话</h2>
      <button v-if="turns.length" class="practice-button" type="button" :disabled="!!pendingQuestion"
        @click="reset">新对话</button>
    </div>
    <div v-if="turns.length || pendingQuestion" ref="transcript" class="transcript" role="log" aria-label="教学对话记录">
      <article v-for="(turn, index) in turns" :key="index" class="dialogue-turn">
        <p class="user-question">{{ turn.question }}</p>
        <TrainingReply :result="turn.response" />
      </article>
      <article v-if="pendingQuestion" class="dialogue-turn">
        <p class="user-question">{{ pendingQuestion }}</p>
        <p class="practice-status" role="status">正在查找访谈和案例证据…</p>
      </article>
    </div>
    <form class="practice-form practice-stack" @submit.prevent="submit">
      <label>{{ turns.length ? '继续追问' : '你遇到了什么教学问题？' }}
        <textarea v-model.trim="question" maxlength="1000" :disabled="!!pendingQuestion"
          :placeholder="turns.length ? '例如：如果我只剩五分钟，第一步做什么？' : '例如：学生总不发言，我该怎么判断原因？'" />
      </label>
      <div class="practice-row">
        <button class="practice-button primary" :disabled="!!pendingQuestion || !question">
          {{ turns.length ? '发送追问' : '发送问题' }}
        </button>
      </div>
    </form>
    <p v-if="error" class="practice-error" role="alert">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { pendingQuestion, sendQuestion, turns } from "./trainingConversation";
import TrainingReply from "./TrainingReply.vue";

const question = ref("");
const error = ref("");
const transcript = ref<HTMLDivElement>();

async function submit() {
  if (!question.value || pendingQuestion.value) return;
  const text = question.value;
  error.value = "";
  question.value = "";
  try {
    await sendQuestion(text);
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    question.value = text;
  }
}

function reset() {
  turns.value = [];
  question.value = "";
  error.value = "";
}

watch([() => turns.value.length, pendingQuestion], async () => {
  await nextTick();
  const log = transcript.value;
  if (log) log.scrollTop = log.scrollHeight;
}, { immediate: true });
</script>

<style scoped>
.training-conversation { margin-bottom: 18px; }
.conversation-heading { justify-content: space-between; margin-bottom: 10px; }
.conversation-heading h2 { margin: 0; }
.transcript { display: grid; gap: 18px; max-height: min(62vh, 680px); overflow: auto; margin: 0 0 18px; padding: 2px 6px 10px 0; }
.dialogue-turn { min-width: 0; }
.user-question { width: fit-content; margin: 0 0 12px auto; padding: 8px 13px; border-radius: 15px 15px 4px 15px; background: #e4efe6; max-width: min(80%, 65ch); overflow-wrap: anywhere; white-space: pre-wrap; }
.training-conversation textarea { min-height: 68px; }
</style>
