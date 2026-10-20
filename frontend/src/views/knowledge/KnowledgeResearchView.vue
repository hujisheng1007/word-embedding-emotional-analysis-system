<template>
  <main class="knowledge-page">
    <section class="hero">
      <p class="eyebrow">Evidence retrieval & evaluation</p>
      <h1>知识检索与科研评测</h1>
      <p>在已获授权的正文和文字稿中检索，结果始终携带资源、来源与页码/时间戳定位；评测使用 Hit@K 和 MRR。</p>
    </section>
    <section class="search-card">
      <el-form :model="form" label-position="top" class="search-form">
        <el-form-item label="研究问题"><el-input v-model="form.query" placeholder="例如：教育如何促进社会责任" @keyup.enter="runSearch" /></el-form-item>
        <el-form-item label="教育家"><el-input v-model="form.educatorName" clearable placeholder="可选" /></el-form-item>
        <el-form-item label="资源类型"><el-select v-model="form.resourceType" clearable><el-option label="书籍" value="book" /><el-option label="访谈" value="interview" /><el-option label="视频" value="video" /><el-option label="论文" value="paper" /></el-select></el-form-item>
        <el-form-item label="Top K"><el-input-number v-model="form.topK" :min="1" :max="50" /></el-form-item>
        <el-form-item><el-button type="primary" :loading="searching" @click="runSearch">检索证据</el-button></el-form-item>
      </el-form>
      <p v-if="searchResult" class="run-note">检索运行 {{ searchResult.run_id }} · 候选 {{ searchResult.total_candidates }} 条</p>
      <div class="hits">
        <article v-for="(hit, index) in searchResult?.hits" :key="hit.segment_id">
          <span class="rank">{{ index + 1 }}</span>
          <div><h3>{{ hit.resource_title }}</h3><p>{{ hit.excerpt }}</p><footer><el-tag size="small">{{ hit.resource_type }}</el-tag><span>{{ hit.educator_name || '未关联人物' }}</span><span>{{ hit.locator_type }}：{{ hit.locator_value }}</span><span>score {{ hit.score.toFixed(2) }}</span><a :href="hit.source_url" target="_blank">原始来源</a></footer></div>
        </article>
      </div>
    </section>

    <section class="evaluation-card">
      <div><p class="eyebrow">Reproducible evaluation</p><h2>检索评测集</h2><p>每个问题填写期望命中的资源 ID。系统保存评测集、排序结果和指标，便于复现实验。</p></div>
      <el-form label-position="top">
        <el-form-item label="评测名称"><el-input v-model="evaluationName" /></el-form-item>
        <el-form-item label="案例 JSON"><el-input v-model="casesJson" type="textarea" :rows="9" /></el-form-item>
        <el-button type="primary" :loading="evaluating" @click="runEvaluation">运行评测</el-button>
      </el-form>
      <div v-if="evaluation" class="metrics"><article><span>Hit@{{ evaluation.top_k }}</span><strong>{{ percent(evaluation.hit_rate_at_k) }}</strong></article><article><span>MRR</span><strong>{{ evaluation.mean_reciprocal_rank.toFixed(3) }}</strong></article><article><span>案例数</span><strong>{{ evaluation.case_count }}</strong></article></div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { evaluateRetrieval, searchKnowledge } from "../../api/knowledge";
import type { EvaluationCase, EvaluationResponse, KnowledgeSearchResponse } from "../../types/knowledge";

const form = reactive({ query: "", educatorName: "", resourceType: "", topK: 10 });
const searching = ref(false); const evaluating = ref(false);
const searchResult = ref<KnowledgeSearchResponse | null>(null); const evaluation = ref<EvaluationResponse | null>(null);
const evaluationName = ref("检索基线评测");
const casesJson = ref('[\n  {"query": "教育与社会责任", "expected_resource_ids": ["请替换为资源ID"]}\n]');

async function runSearch() { if (!form.query.trim()) return ElMessage.warning("请填写研究问题"); searching.value = true; try { searchResult.value = await searchKnowledge({ query: form.query, educator_name: form.educatorName, resource_type: form.resourceType, top_k: form.topK }); } catch (e) { ElMessage.error(e instanceof Error ? e.message : "检索失败"); } finally { searching.value = false; } }
async function runEvaluation() { evaluating.value = true; try { const cases = JSON.parse(casesJson.value) as EvaluationCase[]; evaluation.value = await evaluateRetrieval({ name: evaluationName.value, cases, top_k: form.topK }); ElMessage.success("评测运行已保存"); } catch (e) { ElMessage.error(e instanceof Error ? e.message : "评测失败，请检查 JSON 与资源 ID"); } finally { evaluating.value = false; } }
const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
</script>

<style scoped>
.knowledge-page{min-height:100vh;padding:46px clamp(18px,6vw,86px) 80px;color:#193b48;background:linear-gradient(135deg,#f7f9f4,#eaf2ee)}.hero,.search-card,.evaluation-card{max-width:1240px;margin-left:auto;margin-right:auto}.hero{margin-bottom:22px}.hero h1{margin:5px 0 10px;font-size:clamp(34px,5vw,60px)}.hero>p:last-child{max-width:850px;color:#617781;line-height:1.75}.eyebrow{margin:0;color:#bc6f35!important;font-size:12px;font-weight:800;letter-spacing:.15em;text-transform:uppercase}.search-card,.evaluation-card{padding:22px;border:1px solid rgba(29,72,83,.1);border-radius:20px;background:rgba(255,255,255,.92);box-shadow:0 20px 50px rgba(39,67,73,.08)}.search-form{display:grid;grid-template-columns:2fr 1fr 1fr .55fr auto;gap:12px;align-items:end}.run-note{color:#82929a;font-size:12px}.hits{display:grid;gap:12px;margin-top:18px}.hits article{display:grid;grid-template-columns:42px 1fr;gap:13px;padding:16px;border-radius:14px;background:#f4f7f4}.rank{display:grid;width:34px;height:34px;place-items:center;border-radius:50%;color:#fff;background:#28596c}.hits h3{margin:0}.hits p{line-height:1.7}.hits footer{display:flex;flex-wrap:wrap;gap:10px;color:#6b8088;font-size:12px}.hits a{color:#276d88}.evaluation-card{display:grid;grid-template-columns:.75fr 1.25fr;gap:30px;margin-top:20px}.evaluation-card h2{margin:5px 0}.evaluation-card p{color:#6e8189;line-height:1.7}.metrics{display:grid;grid-column:1/-1;grid-template-columns:repeat(3,1fr);gap:12px}.metrics article{padding:18px;border-radius:14px;background:#edf3ef}.metrics span{display:block;color:#748990;font-size:12px}.metrics strong{font-size:28px}@media(max-width:850px){.search-form{grid-template-columns:1fr 1fr}.evaluation-card{grid-template-columns:1fr}}@media(max-width:520px){.search-form,.metrics{grid-template-columns:1fr}}
</style>
