<template>
<section class="workflow">
<h2>01 · 人物分组与多源采集</h2>
<p>选择已有研究人物或添加检索姓名。分组是本次采样标签，人物称号与报道内容仍需核实；不把网络赞誉直接当作道德行为证据。</p>
<div class="controls">
<el-select v-model="group" aria-label="采样组"><el-option v-for="g in groups" :key="g" :label="g" :value="g" /></el-select>
<el-select v-model="names" multiple filterable allow-create default-first-option placeholder="选择或输入人物" aria-label="采集人物"><el-option v-for="p in people" :key="p.id" :value="p.display_name" :label="p.display_name" /></el-select>
<el-button @click="names=people.map(p=>p.display_name)">选择库内全部人物（{{ people.length }}）</el-button>
<el-button @click="names=['张桂梅','于漪'];group='当代教育家候选'">张桂梅 / 于漪</el-button>
<el-select v-model="source" placeholder="选择自动来源" aria-label="采集来源"><el-option v-for="s in sources.filter(s=>s.enabled)" :key="s.id" :value="s.id" :label="s.name" /></el-select>
<el-input-number v-model="limit" :min="1" :max="5" aria-label="每人采集上限" />
<el-button type="primary" :loading="collecting" :disabled="!names.length||!source" @click="collect">按人物创建采集任务</el-button>
<el-button @click="refresh">刷新进度与资源</el-button>
</div>
<p>{{ message }}</p>
<p>论文默认保存可检索元数据；视频有字幕后才可进入文本分析。新闻报道通过 RSS 检索，音频通过 Commons 检索；微信推文仍需原链接登记，不能分析的资料会在下方禁用。<RouterLink to="/collection">查看来源许可、字幕与任务日志 →</RouterLink></p>
<el-table :data="jobs.slice(0,12)" max-height="310"><el-table-column prop="query" label="检索人物"/><el-table-column prop="research_group" label="采样组"/><el-table-column prop="source_name" label="来源"/><el-table-column prop="status" label="状态"/><el-table-column prop="success_count" label="新增"/><el-table-column prop="duplicate_count" label="重复"/><el-table-column prop="failed_count" label="失败"/><el-table-column prop="error_message" label="失败原因"/></el-table>
<h3>过程记录</h3><p v-for="(item,i) in history" :key="i">{{ item }}</p>
<h3>02 · 原有画像分析 → 上下文切分 → 四成分证据 → 人工复核</h3>
<p>下方选定资料生成窗口后，可运行原有三重人格规则分析，再进行四成分分析。两种框架分别展示，不换算为同一个分数。</p>
</section>
</template>
<script setup lang="ts">
import {ref,onMounted,onUnmounted} from 'vue';
import {RouterLink} from 'vue-router';
import {ElMessage} from 'element-plus';
import * as api from '../../api/collection';
import type {EducatorPerson,CollectionSource,CollectionJob} from '../../types/collection';
const emit=defineEmits<{refresh:[]}>();
const groups=['经典教育家研究组','当代教育家候选','优秀教师报道候选','待核实 / 对照资料'];
const group=ref(groups[0]),names=ref<string[]>([]),source=ref(''),limit=ref(2),collecting=ref(false),message=ref('');
const people=ref<EducatorPerson[]>([]),sources=ref<CollectionSource[]>([]),jobs=ref<CollectionJob[]>([]);
const history=ref<string[]>(JSON.parse(localStorage.getItem('moral-collection-history')||'[]'));
let timer:ReturnType<typeof setInterval>|undefined;
async function refresh(){try{[people.value,sources.value,jobs.value]=await Promise.all([api.getPeople(),api.getCollectionSources(),api.getCollectionJobs()]);emit('refresh');}catch(e){ElMessage.error(String(e));}}
async function collect(){collecting.value=true;let n=0;try{for(const name of [...new Set(names.value)]){await api.createCollectionJob({source_id:source.value,query:name,educator_name:name,limit:limit.value,language:'zh',contact_email:'',research_group:group.value});n++;}message.value=`已创建 ${n} 个任务，采集结果以任务记录为准。`;history.value.unshift(`${new Date().toLocaleString()} · ${group.value} · ${names.value.join('、')} · ${n} 个任务`);localStorage.setItem('moral-collection-history',JSON.stringify(history.value.slice(0,30)));await refresh();}catch(e){message.value=`已创建 ${n} 项，后续失败：${String(e)}`;}finally{collecting.value=false;}}
onMounted(async()=>{await refresh();timer=setInterval(()=>{if(jobs.value.some(j=>['queued','running'].includes(j.status)))refresh();},5000);});
onUnmounted(()=>clearInterval(timer));
</script>
<style scoped>
.workflow{padding:26px;background:white;border:1px solid #dae3df;border-radius:16px;margin:22px 0}.workflow p{line-height:1.8;color:#627579;font-size:13px}.controls{display:flex;flex-wrap:wrap;gap:12px}.controls .el-select{width:260px}h2{font-size:25px}a{color:#267b77}
</style>
