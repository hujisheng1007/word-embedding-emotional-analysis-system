import { computed, ref } from "vue";
import { ask } from "../../api/practice";
import type { TrainingAnswer } from "../../types/practice";

export const turns = ref<{ question: string; response: TrainingAnswer }[]>([]);
export const pendingQuestion = ref("");
export const latestResponse = computed(() => turns.value[turns.value.length - 1]?.response);

export async function sendQuestion(question: string) {
  if (pendingQuestion.value) return;
  const history = turns.value.slice(-6).flatMap(({ question: priorQuestion, response }) => {
    const answer = [response.answer || response.message, response.next_step, response.clarifying_question]
      .filter(Boolean).join("\n").slice(0, 1300);
    return answer ? [{ question: priorQuestion, answer }] : [];
  });
  pendingQuestion.value = question;
  try {
    const response = await ask(question, history);
    turns.value.push({ question, response });
  } finally {
    pendingQuestion.value = "";
  }
}
