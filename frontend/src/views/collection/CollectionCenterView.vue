<template>
  <main class="collection-page">
    <section class="hero">
      <div>
        <p class="eyebrow">Research ingestion operations</p>
        <h1>教育家多源数据采集中心</h1>
        <p>统一管理人物、公开视频、论文与教育期刊元数据；每条记录保留来源、许可、审核状态和错误日志。</p>
      </div>
      <el-button type="primary" :loading="loading" @click="refreshAll">刷新数据</el-button>
    </section>

    <el-alert v-if="error" class="page-alert" :title="error" type="error" show-icon :closable="false" />

    <section class="stats">
      <article><span>采集来源</span><strong>{{ stats.source_count }}</strong></article>
      <article><span>任务 / 进行中</span><strong>{{ stats.job_count }} / {{ stats.running_count }}</strong></article>
      <article><span>成功 / 重复 / 失败</span><strong>{{ stats.success_count }} / {{ stats.duplicate_count }} / {{ stats.failed_count }}</strong></article>
      <article><span>人物 / 视频 / 论文</span><strong>{{ stats.person_count }} / {{ stats.video_count }} / {{ stats.paper_count }}</strong></article>
    </section>

    <section class="create-card">
      <div>
        <h2>创建采集任务</h2>
        <p>自动来源按各自许可与限流规则运行；央视网、教育部等受限来源仅开放人工元数据登记。</p>
      </div>
      <el-form :model="form" label-position="top" class="job-form">
        <el-form-item label="采集来源">
          <el-select v-model="form.sourceId" placeholder="选择来源">
            <el-option v-for="source in enabledSources" :key="source.id" :value="source.id" :label="source.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="检索词">
          <el-input v-model="form.query" placeholder="如：蔡元培、陶行知、教育家精神" />
        </el-form-item>
        <el-form-item label="关联教育家">
          <el-input v-model="form.educatorName" placeholder="视频或论文可填写人物姓名" />
        </el-form-item>
        <el-form-item label="条数">
          <el-input-number v-model="form.limit" :min="1" :max="25" />
        </el-form-item>
        <el-form-item><el-button type="primary" :loading="creating" @click="createJob">开始采集</el-button></el-form-item>
      </el-form>
    </section>

    <el-tabs v-model="activeTab" class="workspace">
      <el-tab-pane label="来源管理" name="sources">
        <el-table :data="sources" stripe>
          <el-table-column prop="name" label="来源" min-width="190" />
          <el-table-column prop="source_type" label="类型" width="100" />
          <el-table-column label="能力" min-width="240">
            <template #default="scope">
              <el-tag v-if="scope.row.allows_metadata">元数据</el-tag>
              <el-tag v-if="scope.row.allows_subtitles" type="success">字幕</el-tag>
              <el-tag v-if="scope.row.allows_media_download" type="warning">开放媒体</el-tag>
              <el-tag v-if="scope.row.allows_transcription" type="danger">授权转写</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="scope"><el-tag :type="scope.row.enabled ? 'success' : 'info'">{{ scope.row.enabled ? '自动' : '人工登记' }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="license_note" label="许可与限制" min-width="340" />
          <el-table-column label="条款" width="90"><template #default="scope"><a :href="scope.row.terms_url" target="_blank">查看</a></template></el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="任务与日志" name="jobs">
        <el-table :data="jobs" stripe>
          <el-table-column prop="source_name" label="来源" min-width="170" />
          <el-table-column prop="query" label="关键词" min-width="150" />
          <el-table-column prop="status" label="状态" width="105" />
          <el-table-column label="成功/重复/失败" width="150"><template #default="scope">{{ scope.row.success_count }}/{{ scope.row.duplicate_count }}/{{ scope.row.failed_count }}</template></el-table-column>
          <el-table-column prop="error_message" label="错误" min-width="210" show-overflow-tooltip />
          <el-table-column label="操作" width="210">
            <template #default="scope">
              <el-button size="small" @click="showLogs(scope.row)">日志</el-button>
              <el-button v-if="['queued','running'].includes(scope.row.status)" size="small" @click="pause(scope.row.id)">暂停</el-button>
              <el-button v-if="['paused','failed'].includes(scope.row.status)" size="small" type="primary" @click="resume(scope.row.id)">恢复</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="人物资料审核" name="people">
        <div class="toolbar"><el-input v-model="peopleKeyword" clearable placeholder="按教育家姓名检索" @keyup.enter="loadPeople" /><el-button @click="loadPeople">检索</el-button></div>
        <div class="person-grid">
          <article v-for="person in people" :key="person.id" class="person-card">
            <h3>{{ person.display_name }}</h3>
            <p>生卒：{{ person.birth_date || '待核' }} — {{ person.death_date || '待核' }} · 关联资源 {{ person.resource_count }}</p>
            <div v-for="fact in person.facts" :key="fact.id" class="fact">
              <p>{{ fact.value_text }}</p>
              <a :href="fact.source_url" target="_blank">{{ fact.source_publisher || fact.source_title }}</a>
              <span><el-tag size="small">{{ fact.review_status }}</el-tag>
                <el-button text type="success" @click="reviewFact(fact.id, 'approved')">通过</el-button>
                <el-button text type="danger" @click="reviewFact(fact.id, 'rejected')">拒绝</el-button></span>
            </div>
          </article>
        </div>
      </el-tab-pane>

      <el-tab-pane label="视频与文字稿" name="videos">
        <div class="toolbar"><el-input v-model="videoKeyword" clearable placeholder="按标题或教育家检索" @keyup.enter="loadVideos" /><el-button @click="loadVideos">检索</el-button></div>
        <div class="video-grid">
          <article v-for="video in videos" :key="video.id" class="video-card">
            <video v-if="video.embed_allowed && video.media_url" :src="video.media_url" controls preload="metadata" />
            <div class="video-body">
              <h3>{{ video.title }}</h3><p>{{ video.educator_name }} · {{ video.license_code }}</p>
              <a :href="video.page_url" target="_blank">查看原始来源</a>
              <el-alert v-if="video.restriction_reason" :title="video.restriction_reason" type="warning" :closable="false" />
              <div class="actions">
                <el-button v-if="video.subtitle_access" size="small" @click="fetchSubtitle(video.id)">获取官方字幕</el-button>
                <el-button v-if="video.transcription_allowed" size="small" type="warning" @click="transcribe(video.id)">授权 Whisper 转写</el-button>
                <el-button size="small" type="primary" :disabled="!video.transcripts.length" @click="analyze(video.resource_id)">三重人格分析</el-button>
              </div>
              <div v-for="transcript in video.transcripts" :key="transcript.id" class="transcript">
                <strong>{{ transcript.language }} · {{ transcript.origin }} · {{ transcript.review_status }}</strong>
                <button v-for="cue in transcript.cues" :key="cue.id" @click="seekVideo($event, cue.start_ms)">
                  <time>{{ formatTime(cue.start_ms) }}</time>{{ cue.text }}
                </button>
              </div>
            </div>
          </article>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="logVisible" title="任务日志" size="48%">
      <el-timeline><el-timeline-item v-for="log in logs" :key="log.id" :timestamp="log.created_at" :type="log.level === 'error' ? 'danger' : 'primary'"><strong>{{ log.event }}</strong><p>{{ log.message }}</p></el-timeline-item></el-timeline>
    </el-drawer>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  analyzeCollectedResource, createCollectionJob, getCollectionJobs, getCollectionSources,
  getCollectionStats, getJobLogs, getPeople, getVideos, importOfficialSubtitle,
  pauseCollectionJob, resumeCollectionJob, transcribeAuthorizedVideo, updateReview
} from "../../api/collection";
import type { CollectedVideo, CollectionJob, CollectionLog, CollectionSource, CollectionStats, EducatorPerson } from "../../types/collection";

const emptyStats = (): CollectionStats => ({ source_count: 0, job_count: 0, running_count: 0, success_count: 0, failed_count: 0, duplicate_count: 0, person_count: 0, video_count: 0, transcript_count: 0, paper_count: 0 });
const sources = ref<CollectionSource[]>([]); const jobs = ref<CollectionJob[]>([]); const logs = ref<CollectionLog[]>([]);
const people = ref<EducatorPerson[]>([]); const videos = ref<CollectedVideo[]>([]); const stats = ref(emptyStats());
const activeTab = ref("sources"); const loading = ref(false); const creating = ref(false); const error = ref("");
const logVisible = ref(false); const peopleKeyword = ref(""); const videoKeyword = ref("");
const form = reactive({ sourceId: "", query: "", educatorName: "", limit: 8, language: "zh", contactEmail: "" });
const enabledSources = computed(() => sources.value.filter((item) => item.enabled));

async function refreshAll() { loading.value = true; error.value = ""; try { const [s, j, st, p, v] = await Promise.all([getCollectionSources(), getCollectionJobs(), getCollectionStats(), getPeople(), getVideos()]); sources.value = s; jobs.value = j; stats.value = st; people.value = p; videos.value = v; if (!form.sourceId && enabledSources.value.length) form.sourceId = enabledSources.value[0].id; } catch (e) { error.value = e instanceof Error ? e.message : "采集中心加载失败"; } finally { loading.value = false; } }
async function createJob() { if (!form.sourceId || !form.query.trim()) return ElMessage.warning("请选择来源并填写检索词"); creating.value = true; try { await createCollectionJob({ source_id: form.sourceId, query: form.query, educator_name: form.educatorName, limit: form.limit, language: form.language, contact_email: form.contactEmail }); ElMessage.success("任务已创建"); activeTab.value = "jobs"; await refreshAll(); } catch (e) { ElMessage.error(e instanceof Error ? e.message : "任务创建失败"); } finally { creating.value = false; } }
async function showLogs(job: CollectionJob) { logs.value = await getJobLogs(job.id); logVisible.value = true; }
async function pause(id: string) { await pauseCollectionJob(id); await refreshAll(); }
async function resume(id: string) { await resumeCollectionJob(id); await refreshAll(); }
async function loadPeople() { people.value = await getPeople(peopleKeyword.value); }
async function loadVideos() { videos.value = await getVideos(videoKeyword.value); }
async function reviewFact(id: string, status: string) { await updateReview(`/collection/people/facts/${id}`, status); ElMessage.success("审核状态已更新"); await loadPeople(); }
async function fetchSubtitle(id: string) { try { await importOfficialSubtitle(id, "zh"); ElMessage.success("官方字幕已导入，等待人工审核"); await loadVideos(); } catch (e) { ElMessage.error(e instanceof Error ? e.message : "字幕获取失败"); } }
async function transcribe(id: string) { try { await transcribeAuthorizedVideo(id); ElMessage.success("转写任务已进入后台队列"); activeTab.value = "jobs"; await refreshAll(); } catch (e) { ElMessage.error(e instanceof Error ? e.message : "转写任务创建失败"); } }
async function analyze(resourceId: string) { try { await analyzeCollectedResource(resourceId); ElMessage.success("分析完成，证据已写入资源记录"); } catch (e) { ElMessage.error(e instanceof Error ? e.message : "分析失败"); } }
function formatTime(ms: number) { const seconds = Math.floor(ms / 1000); return `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${(seconds % 60).toString().padStart(2, "0")}`; }
function seekVideo(event: Event, ms: number) { const card = (event.currentTarget as HTMLElement).closest(".video-card"); const player = card?.querySelector("video"); if (player) { player.currentTime = ms / 1000; void player.play(); } }
onMounted(refreshAll);
</script>

<style scoped>
.collection-page{min-height:100vh;padding:42px clamp(18px,5vw,72px) 72px;color:#173847;background:radial-gradient(circle at 90% 5%,rgba(205,122,61,.14),transparent 28%),linear-gradient(#f7faf7,#edf3ef)}
.hero{display:flex;align-items:end;justify-content:space-between;gap:24px;max-width:1380px;margin:0 auto 24px}.hero h1{margin:6px 0 10px;font-size:clamp(32px,5vw,56px)}.hero p{max-width:820px;margin:0;color:#617782;line-height:1.7}.eyebrow{color:#be7137!important;font-size:12px;font-weight:800;letter-spacing:.15em;text-transform:uppercase}.page-alert,.stats,.create-card,.workspace{max-width:1380px;margin-left:auto;margin-right:auto}.page-alert{margin-bottom:18px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px}.stats article,.create-card,.workspace{border:1px solid rgba(29,71,82,.1);border-radius:18px;background:rgba(255,255,255,.9);box-shadow:0 18px 45px rgba(39,67,73,.07)}.stats article{padding:18px}.stats span{display:block;color:#758b94;font-size:12px}.stats strong{font-size:27px}.create-card{display:grid;grid-template-columns:1fr 2fr;gap:28px;padding:22px;margin-bottom:18px}.create-card h2{margin:0 0 6px}.create-card p{color:#71858e;line-height:1.6}.job-form{display:grid;grid-template-columns:1.3fr 1.5fr 1fr .55fr auto;gap:12px;align-items:end}.workspace{padding:18px}.toolbar{display:flex;gap:10px;max-width:560px;margin-bottom:16px}.person-grid,.video-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.person-card,.video-card{overflow:hidden;border:1px solid #dce5e1;border-radius:15px;background:#fff}.person-card{padding:18px}.person-card h3,.video-card h3{margin:0 0 8px}.person-card>p,.video-card p{color:#73868e}.fact{margin-top:12px;padding:12px;border-left:3px solid #ce8246;background:#f5f7f3}.fact p{margin:0 0 7px;line-height:1.6}.fact span{display:flex;align-items:center;margin-top:8px}.video-card video{width:100%;max-height:310px;background:#10232b}.video-body{padding:18px}.actions{margin:14px 0}.transcript{display:grid;gap:6px;margin-top:14px;max-height:320px;overflow:auto}.transcript button{display:grid;grid-template-columns:56px 1fr;gap:8px;padding:8px;border:0;border-radius:8px;background:#f4f7f4;text-align:left;cursor:pointer}.transcript button:hover{background:#e8f0eb}.transcript time{color:#b76a32;font-family:monospace}.el-tag+.el-tag{margin-left:5px}a{color:#286b86}
@media(max-width:900px){.stats{grid-template-columns:1fr 1fr}.create-card{grid-template-columns:1fr}.job-form{grid-template-columns:1fr 1fr}.person-grid,.video-grid{grid-template-columns:1fr}}@media(max-width:560px){.hero{align-items:stretch;flex-direction:column}.stats,.job-form{grid-template-columns:1fr}}
</style>
