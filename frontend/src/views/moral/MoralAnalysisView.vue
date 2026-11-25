<template>
  <main class="moral-page" v-loading="initializing">
    <header class="research-hero">
      <div><p class="eyebrow">CLASSIC CHINESE EDUCATORS · REST FRAMEWORK</p><h1>从教育家群体资料<br>走向道德行动证据</h1>
        <p class="intro">跨人物整理教育情境与育人行为，以 Rest 四成分考察叙事中的问题识别、伦理判断、价值优先与行动实施。每一项解释都回到原文。</p>
        <div class="scope"><span>当前：事件编码与辅助复核</span><span>后续：行为模式挖掘 · 多模态增益检验</span></div>
      </div>
      <aside><h3>理论与资料的边界</h3><p>四成分描述道德行动过程，不构成人格总分。未记载不代表人物缺少该过程。</p><p>目前分析正文与字幕；图像、声音及视频行为融合尚未实现。</p><RouterLink to="/legacy-profile">查看历史画像原型 →</RouterLink></aside>
    </header>
    <section class="component-overview">
      <article v-for="(label,id,index) in names" :key="id"><span>0{{ index+1 }}</span><h2>{{ label }}</h2><p>{{ definitions[id] }}</p></article>
    </section>
    <CollectionWorkflow @refresh="reloadResources" />
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="notice" />
    <section class="summary" v-if="stats">
      <div><strong>{{ resources.length }}</strong><span>已登记资源</span></div><div><strong>{{ resourcePeople }}</strong><span>关联人物（含外籍资料）</span></div>
      <div><strong>{{ stats.events }}</strong><span>候选与已处理事件</span></div><div><strong>{{ stats.confirmed }}</strong><span>人工确认事件</span></div><div><strong>{{ stats.failed_runs }}</strong><span>失败运行 · 可查记录</span></div>
    </section>
    <section class="section">
      <div class="section-heading"><div><p class="eyebrow">01 / CORPUS</p><h2>跨人物选择资料</h2></div><RouterLink to="/resources">查看完整资源库 →</RouterLink></div>
      <p class="helper">选择多位教育家的资料生成候选窗口；原文、字幕和来源均保留。窗口需核验上下文与事件边界，不能直接视为完整教育事件。</p>
      <div class="build-form">
        <el-select v-model="selectedResources" multiple filterable collapse-tags collapse-tags-tooltip placeholder="选择画传、访谈或字幕资料" aria-label="选择研究资源">
          <el-option v-for="r in resources" :key="r.id" :value="r.id" :disabled="!r.analyzable" :label="`${r.educator_name} · ${r.title}${r.analyzable?'':'（仅元数据/不可分析）'}`" />
        </el-select>
        <el-input v-model="keyword" clearable placeholder="道德行为关键词，以逗号分隔，如：帮助、公平、责任" aria-label="候选关键词" />
        <label>每份资料 <el-input-number v-model="perResource" :min="1" :max="5" size="small" aria-label="每份候选数" /></label>
        <label>前文段数 <el-input-number v-model="before" :min="0" :max="10" /></label>
        <label>后文段数 <el-input-number v-model="after" :min="0" :max="10" /></label>
        <label>最少命中次数 <el-input-number v-model="minHits" :min="1" :max="20" /></label>
        <el-button type="primary" :loading="building" :disabled="!selectedResources.length" @click="build">生成候选</el-button>
      </div>
      <p class="helper">默认按等位置取样并带相邻片段，用于试编码；关键词筛选会引入选择偏差。第一版不自动判断事件完整性。</p>
      <el-alert v-if="buildMessage" :title="buildMessage" type="info" :closable="false" />
    </section>
    <section class="section">
      <div class="section-heading"><div><p class="eyebrow">02 / EVIDENCE</p><h2>事件分析与原文复核</h2></div><el-button @click="download" :loading="exporting">导出研究记录 JSON</el-button></div>
      <div class="analysis-toolbar">
        <el-select v-model="resourceFilter" clearable placeholder="按资源查看事件" @change="page=1; loadEvents()" aria-label="事件资源筛选"><el-option v-for="r in resources" :key="r.id" :label="r.title" :value="r.id" /></el-select>
        <el-select v-model="method" aria-label="分析方法"><el-option label="规则候选筛选（不代表成分成立）" value="rule"/><el-option label="大模型直接判断" value="llm_direct"/><el-option label="大模型＋原文证据约束" value="llm_evidence"/></el-select>
        <el-button :disabled="!batchRows.length || busy" @click="analyzeBatch">分析勾选项（{{ batchRows.length }}）</el-button>
        <el-button v-if="busy" @click="stopBatch=true">当前事件结束后停止</el-button>
      </div>
      <el-button :disabled="!detail||busy" @click="legacyAnalyze">对当前窗口运行原有画像规则分析</el-button>
      <div v-if="legacyResult" class="helper"><strong>三重人格规则参考结果</strong><p v-for="d in legacyResult.dimension_scores" :key="d.id">{{ d.name }}：{{ d.score }} · {{ d.matched_keywords?.join('、') }}</p></div>
      <div v-if="detail" class="helper"><strong>道德行为证据呈现：{{ presentationLevel }}</strong><p>按当前四成分编码生成的描述，编辑后会更新；保存人工复核后才纳入研究统计。这不是人物道德高低排名，也不是已验证量表。</p></div>
      <p v-if="progress" class="progress" role="status">{{ progress }}</p>
      <div class="workbench">
        <div class="event-list">
          <el-table :data="events" highlight-current-row @row-click="openEvent" @selection-change="(rows:EventSummary[])=>batchRows=rows" empty-text="暂无事件。先从上方选择资料并生成候选。" max-height="630" row-key="id">
            <el-table-column type="selection" width="40" :selectable="(row:EventSummary)=>row.eligibility!=='excluded'" />
            <el-table-column label="人物 / 事件"><template #default="{row}"><strong>{{ row.educator_name }}</strong><p class="event-title">{{ row.resource_title }}</p><p class="excerpt">{{ row.excerpt }}</p><el-tag size="small" :type="row.eligibility==='confirmed'?'success':row.eligibility==='excluded'?'info':'warning'">{{ eligibilityLabel(row.eligibility) }}</el-tag></template></el-table-column>
          </el-table>
          <el-pagination small layout="prev, pager, next" :page-size="50" :total="total" v-model:current-page="page" @current-change="loadEvents" />
        </div>
        <div v-if="detail" class="event-detail" v-loading="loadingDetail">
          <div class="event-heading"><div><h3>{{ detail.snapshot.educator_name }} · {{ detail.snapshot.resource_title }}</h3><p class="helper">{{ detail.snapshot.analysis_modality }} · 复核版本 {{ detail.review_revision }} · {{ eligibilityLabel(detail.eligibility) }}</p></div><el-button :disabled="busy || detail.eligibility==='excluded'" type="primary" @click="analyzeCurrent">分析此事件</el-button></div>
          <p class="helper">来源：{{ detail.snapshot.source_institution || '待补充' }} · 原文快照已保存。<a v-if="safeSource" :href="safeSource" target="_blank" rel="noopener noreferrer">访问来源</a></p>
          <div class="source-header"><strong>原文与定位</strong><el-button size="small" @click="showContext">检查 / 调整窗口边界</el-button></div>
          <div class="source-text">
            <article v-for="span in detail.snapshot.spans" :key="span.segment_id">
              <div class="locator"><span>{{ span.locator_type }}：{{ span.locator_value }}</span><el-button link type="primary" @click="addQuote(span)">引用到「{{ componentName(activeComponent) }}」</el-button></div>
              <p><template v-for="(part,i) in highlighted(span)" :key="i"><mark v-if="part.mark">{{ part.text }}</mark><span v-else>{{ part.text }}</span></template></p>
            </article>
          </div>
          <p class="helper">规则命中只作候选提示；引文匹配通过只证明原文存在，语义支持仍需复核。直接模型模式不强制引证，保存有支持/相反判断前需补齐证据。</p>
          <div class="codes">
            <article v-for="code in codes" :key="code.component_id" :class="['code', {active:activeComponent===code.component_id}]">
              <div class="code-title"><button @click="activeComponent=code.component_id">{{ componentName(code.component_id) }} <small>{{ activeComponent===code.component_id?'· 正在引用':'' }}</small></button></div>
              <p class="definition">{{ definitions[code.component_id] }}</p>
              <el-select v-model="code.status" :aria-label="componentName(code.component_id)+'状态'"><el-option v-for="(name,key) in statusLabels" :key="key" :value="key" :label="name" /></el-select>
              <el-input v-model="code.rationale" type="textarea" :rows="2" placeholder="写明该判断的依据与局限" :aria-label="componentName(code.component_id)+'说明'" />
              <div v-for="(ev,index) in code.evidence" :key="index" class="quote">
                <div class="quote-top"><el-select v-model="ev.polarity" size="small" aria-label="证据方向"><el-option label="支持" value="support"/><el-option label="相反" value="counter"/><el-option label="相关上下文" value="context"/></el-select><el-button link type="danger" @click="code.evidence.splice(index,1)">移除</el-button></div>
                <el-input v-model="ev.quote" type="textarea" :rows="2" aria-label="逐字引文" @input="ev.start_char=null;ev.end_char=null" />
                <small>片段 {{ spanLocator(ev.segment_id) }} · 点击原文按钮添加引文，可保留其中连续的一部分。</small>
              </div>
              <p v-if="!code.evidence.length" class="empty-evidence">尚无引文；不自动补写缺失信息。</p>
            </article>
          </div>
          <div class="review"><h3>人工辅助复核</h3><p class="helper">本页可见模型结果，用于辅助复核；尚不是盲法独立编码。确认前请检查主体、事件边界和引文解释。</p>
            <div class="review-fields"><el-input v-model="reviewer" placeholder="复核者署名（用于记录）" aria-label="复核者"/><el-select v-model="eligibility" aria-label="事件资格"><el-option label="确认事件与本次编码" value="confirmed"/><el-option label="排除此候选窗口" value="excluded"/></el-select></div>
            <el-input v-model="note" type="textarea" :rows="2" placeholder="记录情境、行动、明示理由、结果及局限；排除时请填写原因" aria-label="复核说明" />
            <el-button type="primary" :loading="saving" :disabled="busy || !reviewer.trim()" @click="save">保存复核新版本</el-button>
          </div>
          <el-collapse class="history"><el-collapse-item :title="`运行与复核记录（${detail.runs.length}次运行 / ${detail.reviews.length}次复核）`">
            <div v-for="run in detail.runs" :key="run.id" class="history-row"><strong>{{ run.method }} · {{ run.status==='succeeded'?'成功 · 待语义核验':run.status==='failed'?'失败':run.status==='running'?'处理中':'中断' }}</strong><span>{{ run.created_at }}</span><p v-if="run.error" class="error">{{ run.error }}</p><el-button v-if="run.result.codes" link @click="useRun(run)">载入这次候选（未保存修改将被替换）</el-button></div>
            <div v-for="r in detail.reviews" :key="r.id" class="history-row">复核 v{{ r.revision }} · {{ r.reviewer }} · {{ eligibilityLabel(r.eligibility) }}<p>{{ r.note }}</p></div>
          </el-collapse-item></el-collapse>
        </div>
        <el-empty v-else description="选择左侧事件查看原文与四成分编码" />
      </div>
    </section>
    <section v-if="stats" class="section">
      <p class="eyebrow">03 / CROSS-EDUCATOR REVIEW</p><h2>群体资料与编码概览</h2><p class="helper">{{ stats.note }} 当前分母 N = {{ stats.denominator }}。四成分可以共现，不相加为100%；这些是叙事证据分布，不是人物道德水平。</p>
      <div class="statistics"><el-table :data="componentRows" empty-text="等待人工复核"><el-table-column prop="name" label="理论成分" min-width="140"/><el-table-column v-for="(name,key) in statusLabels" :key="key" :prop="key" :label="name" min-width="90"/></el-table>
        <el-table :data="stats.people" empty-text="尚未生成跨人物候选"><el-table-column prop="name" label="资料关联人物"/><el-table-column prop="events" label="全部窗口"/><el-table-column prop="confirmed" label="已确认"/></el-table></div>
      <p class="helper">行为语义聚类、跨源事件对齐及多模态增益实验仍待开发。当前保存的事件与证据将作为后续典范提取的基础。</p>
    </section>
    <el-dialog v-model="contextVisible" title="核对上下文并新建窗口" width="min(960px, 95vw)">
      <p>勾选同一事件的连续片段。保存后生成新候选，旧候选及其记录仍保留；请在旧候选中记录排除原因，避免重复纳入。</p>
      <el-checkbox-group v-model="contextSelection" class="context-list"><div v-for="span in context" :key="span.segment_id"><el-checkbox :value="span.segment_id">{{ span.locator_type }}：{{ span.locator_value }}</el-checkbox><p>{{ span.text }}</p></div></el-checkbox-group>
      <template #footer><el-button @click="contextVisible=false">取消</el-button><el-button type="primary" :disabled="!contextSelection.length" @click="createWindow">保存所选窗口</el-button></template>
    </el-dialog>
  </main>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import CollectionWorkflow from './CollectionWorkflow.vue';
import { RouterLink, useRoute } from 'vue-router';
const route = useRoute();
import { ElMessage, ElMessageBox } from 'element-plus';
import * as api from '../../api/moral';
import { request } from '../../api/client';
const legacyResult=ref<any>(null);
async function legacyAnalyze(){if(!detail.value)return;busy.value=true;try{legacyResult.value=await request(`/moral/events/${detail.value.id}/legacy-analysis`,{method:'POST'});}catch(e){fail(e);}finally{busy.value=false;}}
const presentationLevel=computed(()=>{const c=codes.value;const action=c.find(x=>x.component_id==='implementation');if(!action||action.status!=='supported'||!action.evidence.some(e=>e.polarity==='support'))return '尚不足以判断已实施行为';if(c.some(x=>['counterevidence','mixed'].includes(x.status)))return '有行动记录，存在矛盾证据，需复核';return c.every(x=>x.status==='supported'&&x.evidence.some(e=>e.polarity==='support'))?'行动与四成分证据均有记录':'已有行动记录，理由或动机证据尚不完整';});
import type { ComponentId,EvidenceStatus,MoralMethod,MoralCode,MoralRun,MoralResource,EventSummary,MoralEvent,MoralStats,SourceSpan } from '../../types/moral';
const names:Record<ComponentId,string>={sensitivity:'道德敏感性',judgment:'道德判断',motivation:'道德动机（价值优先）',implementation:'道德实施（行动落实）'};
const definitions:Record<ComponentId,string>={sensitivity:'识别需要、权益、潜在伤害及伦理问题。',judgment:'明确的伦理理由、原则或行动方案权衡。',motivation:'明确的价值优先或道德承诺；不能只从行动推断动机。',implementation:'已经采取的行动及实施过程；未来打算需单独区分。'};
const statusLabels:Record<EvidenceStatus,string>={supported:'有支持证据',not_mentioned:'未提及',insufficient:'证据不足',counterevidence:'相反证据',mixed:'混合证据'};
const componentName=(id:ComponentId)=>names[id];
const eligibilityLabel=(v:string)=>({candidate:'待确认窗口',confirmed:'人工已确认',excluded:'已排除'}[v]||v);
const resources=ref<MoralResource[]>([]),selectedResources=ref<string[]>([]),keyword=ref('帮助,公平,责任,家访,辍学,资助'),perResource=ref(3);
const before=ref(2),after=ref(2),minHits=ref(1);
async function reloadResources(){resources.value=await api.moralResources();await refresh();}
const stats=ref<MoralStats|null>(null),events=ref<EventSummary[]>([]),detail=ref<MoralEvent|null>(null),total=ref(0),page=ref(1),resourceFilter=ref('');
const codes=ref<MoralCode[]>([]),method=ref<MoralMethod>('rule'),activeComponent=ref<ComponentId>('sensitivity');
const reviewer=ref(localStorage.getItem('moral-reviewer')||''),note=ref(''),eligibility=ref<'confirmed'|'excluded'>('confirmed');
const error=ref(''),buildMessage=ref(''),progress=ref('');
const initializing=ref(true),building=ref(false),loadingDetail=ref(false),saving=ref(false),busy=ref(false),exporting=ref(false),stopBatch=ref(false);
const batchRows=ref<EventSummary[]>([]),contextVisible=ref(false),context=ref<SourceSpan[]>([]),contextSelection=ref<string[]>([]);
const resourcePeople=computed(()=>new Set(resources.value.map(r=>r.educator_name).filter(n=>n!=='未关联人物')).size);
const componentRows=computed(()=>(Object.keys(names) as ComponentId[]).map(id=>({name:names[id],...(stats.value?.component_counts[id]||{})})));
const safeSource=computed(()=>{try{const u=new URL(detail.value?.snapshot.source_url||'');return ['http:','https:'].includes(u.protocol)?u.href:'';}catch{return '';}});
const blankCodes=():MoralCode[]=>(Object.keys(names) as ComponentId[]).map(id=>({component_id:id,status:'not_mentioned',rationale:'待人工阅读和编码，尚未作出研究判断。',evidence:[]}));
const clone=<T,>(v:T):T=>JSON.parse(JSON.stringify(v));
const fail=(e:unknown)=>{const message=e instanceof Error?e.message:'操作失败';error.value=message;ElMessage.error(message);};
async function loadEvents(){const data=await api.moralEvents(resourceFilter.value,page.value*50-50);events.value=data.items;total.value=data.total;}
async function refresh(){await loadEvents();stats.value=await api.moralStats();}
async function openEvent(row:EventSummary|string){if(busy.value)return;const id=typeof row==='string'?row:row.id;loadingDetail.value=true;try{const d=await api.moralDetail(id);detail.value=d;legacyResult.value=null;const review=d.reviews[0];codes.value=clone(review?.codes||d.runs.find(r=>r.status==='succeeded'&&r.result.codes)?.result.codes||blankCodes());note.value=review?.note||'';eligibility.value=review?.eligibility||'confirmed';error.value='';}catch(e){fail(e);}finally{loadingDetail.value=false;}}
async function build(){building.value=true;try{const r=await api.buildMoralEvents(selectedResources.value,perResource.value,keyword.value,before.value,after.value,minHits.value);buildMessage.value=`新建 ${r.created} 个窗口；跳过 ${r.skipped.length} 项。${r.note}${r.skipped.length?' '+r.skipped.map(x=>x.reason).join('；'):''}`;page.value=1;await refresh();if(r.items[0])await openEvent(r.items[0].id);}catch(e){fail(e);}finally{building.value=false;}}
function useRun(run:MoralRun){if(run.result.codes)codes.value=clone(run.result.codes);}
async function analyzeCurrent(){if(!detail.value)return;const id=detail.value.id;busy.value=true;progress.value='正在分析本事件；大模型模式可能需要约一分钟。';try{const run=await api.analyzeMoralEvent(id,method.value);detail.value=await api.moralDetail(id);if(run.status==='failed')throw new Error(run.error);useRun(run);await refresh();progress.value='已保存运行记录，请检查原文与编码后进行人工复核。';}catch(e){fail(e);await refresh();}finally{busy.value=false;}}
async function analyzeBatch(){const rows=[...batchRows.value];if(rows.length>20)return ElMessage.warning('每批最多20个窗口，请减少勾选项');busy.value=true;stopBatch.value=false;let done=0,failed=0;try{for(const row of rows){if(stopBatch.value)break;progress.value=`批量处理 ${done+1}/${rows.length}：${row.educator_name}`;const r=await api.analyzeMoralEvent(row.id,method.value);done++;if(r.status==='failed')failed++;}progress.value=`本批已处理 ${done} 项，失败 ${failed} 项。所有成功结果仍需人工核验。`;await refresh();}catch(e){fail(e);}finally{busy.value=false;if(detail.value)await openEvent(detail.value.id);}}
function spanLocator(id:string){const span=detail.value?.snapshot.spans.find(s=>s.segment_id===id);return span?`${span.locator_type} ${span.locator_value}`:id;}
function addQuote(span:SourceSpan){const code=codes.value.find(c=>c.component_id===activeComponent.value);if(!code)return;const quote=Array.from(span.text).slice(0,6000).join('');code.evidence.push({segment_id:span.segment_id,quote,polarity:'context',start_char:0,end_char:Array.from(quote).length});}
function highlighted(span:SourceSpan){const chars=Array.from(span.text);const mask=new Uint8Array(chars.length);for(const c of codes.value)for(const e of c.evidence){if(e.segment_id!==span.segment_id)continue;let start=e.start_char;let end=e.end_char;if(start==null||end==null){const i=span.text.indexOf(e.quote);if(i<0)continue;start=Array.from(span.text.slice(0,i)).length;end=start+Array.from(e.quote).length;}for(let i=start;i<Math.min(end,chars.length);i++)mask[i]=1;}const parts:{text:string;mark:boolean}[]=[];for(let i=0;i<chars.length;i++){const mark=Boolean(mask[i]);if(parts.length&&parts[parts.length-1].mark===mark)parts[parts.length-1].text+=chars[i];else parts.push({text:chars[i],mark});}return parts;}
async function save(){if(!detail.value)return;try{await ElMessageBox.confirm('确认已核对事件范围、四个成分及引文？保存会保留历史版本。','保存人工复核',{confirmButtonText:'保存',cancelButtonText:'继续核对'});}catch{return;}saving.value=true;try{detail.value=await api.reviewMoralEvent(detail.value.id,{expected_revision:detail.value.review_revision,reviewer:reviewer.value,note:note.value,eligibility:eligibility.value,codes:codes.value});localStorage.setItem('moral-reviewer',reviewer.value);await refresh();ElMessage.success('已保存人工复核新版本');}catch(e){fail(e);}finally{saving.value=false;}}
async function showContext(){if(!detail.value)return;try{context.value=await api.moralContext(detail.value.id);contextSelection.value=detail.value.snapshot.spans.map(x=>x.segment_id);contextVisible.value=true;}catch(e){fail(e);}}
async function createWindow(){if(!detail.value)return;try{const r=await api.createMoralEvent(detail.value.resource_id,contextSelection.value);contextVisible.value=false;await refresh();await openEvent(r.id);}catch(e){fail(e);}}
async function download(){exporting.value=true;try{const data=await api.exportMoralEvents();const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='Rest事件与证据研究记录.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){fail(e);}finally{exporting.value=false;}}
onMounted(async()=>{try{resources.value=await api.moralResources();const rid=String(route.query.resource||'');if(resources.value.some(r=>r.id===rid)){selectedResources.value=[rid];resourceFilter.value=rid;}await refresh();}catch(e){fail(e);}finally{initializing.value=false;}});
</script>

<style scoped>
.component-overview{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:25px 0}.component-overview article{background:#fff;padding:22px;border-top:5px solid #287d74;border-radius:12px}.component-overview span{color:#b18343;font-size:24px}.component-overview h2{font-size:20px}.component-overview p{line-height:1.8;color:#536d73}

.moral-page{max-width:1600px;margin:auto;padding:42px clamp(16px,4vw,64px) 70px;color:#203e49;background:#f5f7f3;min-height:100vh}.research-hero{display:grid;grid-template-columns:1.8fr 1fr;gap:48px;align-items:center;margin-bottom:30px}.eyebrow{font-size:11px;letter-spacing:.14em;font-weight:700;color:#98663d;margin:0 0 14px}.research-hero h1{font-size:clamp(30px,3.5vw,52px);line-height:1.3;margin:0 0 20px;letter-spacing:-.03em}.intro{max-width:800px;font-size:17px;line-height:1.9;color:#536d73}.scope{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:#387668}.research-hero aside{border-left:3px solid #b9c9bb;padding:8px 0 8px 28px;font-size:14px;line-height:1.9;color:#627579}.research-hero aside h3{color:#244b53}.moral-page a{color:#267b77}.summary{display:grid;grid-template-columns:repeat(5,1fr);border-top:1px solid #cfdbd4;border-bottom:1px solid #cfdbd4;margin:26px 0}.summary div{padding:22px 16px}.summary strong{display:block;font-size:34px}.summary span{font-size:12px;color:#60797d}.section{background:white;border:1px solid #dae3df;border-radius:16px;padding:26px;margin:22px 0}.section h2{font-size:25px;margin:0 0 12px}.section-heading{display:flex;justify-content:space-between;align-items:center;gap:20px}.helper{font-size:13px;line-height:1.8;color:#64797f}.build-form{display:grid;grid-template-columns:2fr 1.4fr 180px auto;gap:12px;align-items:center;margin:20px 0}.build-form label{display:flex;align-items:center;gap:8px;font-size:12px}.build-form .el-input-number{width:105px}.analysis-toolbar{display:flex;gap:12px;margin:16px 0;flex-wrap:wrap}.analysis-toolbar>.el-select{width:275px}.workbench{display:grid;grid-template-columns:310px minmax(0,1fr);gap:24px;border-top:1px solid #e7eeea;padding-top:20px}.event-list{border-right:1px solid #e6eeea;padding-right:15px}.event-title{font-size:12px;margin:3px 0;color:#68858a}.excerpt{font-size:12px;line-height:1.6;max-height:58px;overflow:hidden;color:#50696c}.event-heading{display:flex;justify-content:space-between;align-items:center;gap:10px}.event-heading h3{margin:0;font-size:20px}.source-header{display:flex;justify-content:space-between;align-items:center;margin:16px 0 10px}.source-text{max-height:400px;overflow:auto;padding:16px 20px;background:#f6f5ef;border-radius:10px}.source-text article+article{border-top:1px solid #dedfd5;margin-top:12px}.source-text p{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.9;margin:6px 0 14px;font-size:14px}.locator{display:flex;justify-content:space-between;gap:12px;align-items:center;color:#7d8985;font-size:12px}.source-text mark{background:#f6dfa1;color:inherit}.codes{display:grid;grid-template-columns:1fr 1fr;gap:15px}.code{padding:16px;border:1px solid #dae5e0;border-radius:10px;min-width:0}.code.active{border-color:#4b9188;background:#fbfdfb}.code-title button{border:0;background:none;color:#204c55;font-size:17px;font-weight:700;padding:0;cursor:pointer;text-align:left}.code-title small{font-size:10px;color:#589481}.definition{font-size:12px;line-height:1.6;min-height:38px;color:#647b81}.code>.el-textarea{margin-top:10px}.quote{margin-top:12px;background:#f4f6f4;padding:8px;border-radius:7px}.quote-top{display:flex;justify-content:space-between;margin-bottom:6px}.quote-top .el-select{width:125px}.quote small{font-size:10px;color:#758983;overflow-wrap:anywhere}.empty-evidence{color:#8b9694;font-size:12px}.review{margin-top:24px;padding:20px;background:#f3f7f4;border-radius:12px}.review-fields{display:flex;gap:12px;margin-bottom:10px}.review>.el-button{margin-top:12px}.history{margin-top:20px}.history-row{border-bottom:1px solid #e4ebe7;padding:9px 0}.history-row span{display:block;color:#899794;font-size:11px}.error{color:#b34336}.notice{margin:12px 0}.progress{color:#277d74;font-size:13px}.statistics{display:grid;grid-template-columns:2fr 1fr;gap:24px}.context-list{max-height:55vh;overflow:auto}.context-list p{white-space:pre-wrap;line-height:1.8;padding:10px;background:#f6f7f3}.event-list .el-pagination{margin-top:16px}@media(max-width:1100px){.build-form{grid-template-columns:1fr 1fr}.workbench{grid-template-columns:240px minmax(0,1fr)}.codes{grid-template-columns:1fr}.statistics{grid-template-columns:1fr}}@media(max-width:750px){.research-hero{grid-template-columns:1fr;gap:12px}.summary{grid-template-columns:repeat(3,1fr)}.workbench{grid-template-columns:1fr}.event-list{border-right:0}.build-form{grid-template-columns:1fr}.section{padding:17px}.section-heading{flex-wrap:wrap}.review-fields{flex-direction:column}.analysis-toolbar>.el-select{width:100%}}
</style>
