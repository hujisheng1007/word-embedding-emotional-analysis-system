<template>
  <main class="resource-page">
    <section class="resource-hero">
      <div>
        <p class="eyebrow">Research Resource Library</p>
        <h1>教育家研究资源库</h1>
        <p>统一登记书籍、访谈、论文、字幕和研究资料，保留来源、版权状态与可定位文本。</p>
      </div>
      <el-button type="primary" size="large" @click="importVisible = true">批量导入</el-button>
    </section>

    <el-alert
      v-if="pageError"
      :title="pageError"
      type="error"
      show-icon
      :closable="false"
      class="page-alert"
    />

    <section class="stat-grid">
      <article><span>资源总数</span><strong>{{ stats.total }}</strong></article>
      <article><span>已授权全文</span><strong>{{ stats.fulltext_total }}</strong></article>
      <article><span>受限访问</span><strong>{{ stats.restricted_total }}</strong></article>
      <article><span>资源类型</span><strong>{{ Object.keys(stats.type_counts).length }}</strong></article>
    </section>

    <section class="library-card">
      <div class="filters">
        <el-input
          v-model="filters.keyword"
          clearable
          placeholder="检索标题、来源或引用信息"
          @keyup.enter="refresh"
        />
        <el-select v-model="filters.resourceType" clearable placeholder="全部类型">
          <el-option v-for="option in resourceTypes" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
        <el-input v-model="filters.educatorName" clearable placeholder="教育家姓名" @keyup.enter="refresh" />
        <el-button type="primary" :loading="loading" @click="refresh">查询</el-button>
      </div>

      <el-table :data="resources" v-loading="loading" empty-text="尚无资源，请先导入" stripe>
        <el-table-column prop="title" label="资源标题" min-width="240">
          <template #default="scope">
            <button class="title-button" @click="openDetail(scope.row.id)">{{ scope.row.title }}</button>
            <small>{{ scope.row.author_names.join("、") || "作者未登记" }}</small>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110">
          <template #default="scope">{{ typeLabel(scope.row.resource_type) }}</template>
        </el-table-column>
        <el-table-column prop="educator_name" label="关联人物" width="130" />
        <el-table-column prop="source_institution" label="来源机构" min-width="150" />
        <el-table-column label="版权 / 访问" width="180">
          <template #default="scope">
            <el-tag size="small" :type="scope.row.fulltext_allowed ? 'success' : 'warning'">
              {{ scope.row.copyright_status }}
            </el-tag>
            <el-tag size="small" effect="plain">{{ scope.row.access_level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="segment_count" label="可定位片段" width="110" />
      </el-table>
    </section>

    <el-drawer v-model="detailVisible" title="资源详情" size="min(720px, 92vw)">
      <div v-if="detail" class="detail-stack">
        <div>
          <p class="eyebrow">{{ typeLabel(detail.resource_type) }}</p>
          <h2>{{ detail.title }}</h2>
          <p>{{ detail.author_names.join("、") || "作者未登记" }}</p>
        </div>
        <dl class="detail-grid">
          <div><dt>关联人物</dt><dd>{{ detail.educator_name || "未关联" }}</dd></div>
          <div><dt>来源机构</dt><dd>{{ detail.source_institution || "未登记" }}</dd></div>
          <div><dt>版权状态</dt><dd>{{ detail.copyright_status }}</dd></div>
          <div><dt>全文保存</dt><dd>{{ detail.fulltext_allowed ? "已明确允许" : "仅元数据" }}</dd></div>
          <div><dt>版本</dt><dd>{{ detail.data_version }}</dd></div>
          <div><dt>SHA-256</dt><dd class="hash">{{ detail.content_sha256 }}</dd></div>
        </dl>
        <el-alert
          v-if="!detail.fulltext_allowed"
          title="该资源没有保存全文；当前记录仅用于来源与元数据管理。"
          type="warning"
          :closable="false"
        />
        <section v-if="detail.files.length">
          <h3>文件记录</h3>
          <p v-for="file in detail.files" :key="file.id">
            {{ file.original_name }} · {{ formatBytes(file.byte_size) }} · {{ file.parse_status }}
          </p>
        </section>
        <section v-if="detail.segments.length">
          <h3>可追溯片段</h3>
          <article v-for="segment in detail.segments" :key="segment.id" class="segment-card">
            <span>{{ segment.locator_type }} · {{ segment.locator_value }}</span>
            <p>{{ segment.text }}</p>
          </article>
        </section>
      </div>
    </el-drawer>

    <el-dialog v-model="importVisible" title="批量导入研究资源" width="min(680px, 94vw)">
      <el-form label-position="top" class="import-form">
        <el-form-item label="文件（最多单个 25 MB）" required>
          <input
            class="file-input"
            type="file"
            multiple
            accept=".txt,.csv,.docx,.pdf,.xlsx,.json,.srt,.vtt"
            @change="onFileChange"
          />
          <small>{{ selectedFiles.length ? `已选择 ${selectedFiles.length} 个文件` : "支持 TXT、CSV、DOCX、PDF、XLSX、JSON、SRT、VTT" }}</small>
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="资源类型">
            <el-select v-model="importForm.resourceType">
              <el-option v-for="option in resourceTypes" :key="option.value" :label="option.label" :value="option.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联教育家"><el-input v-model="importForm.educatorName" /></el-form-item>
          <el-form-item label="作者（逗号分隔）"><el-input v-model="importForm.authors" /></el-form-item>
          <el-form-item label="来源机构"><el-input v-model="importForm.sourceInstitution" /></el-form-item>
          <el-form-item label="版权状态">
            <el-select v-model="importForm.copyrightStatus">
              <el-option label="未知" value="unknown" />
              <el-option label="已授权" value="authorized" />
              <el-option label="公共领域" value="public_domain" />
              <el-option label="合理使用" value="fair_use" />
              <el-option label="受限" value="restricted" />
            </el-select>
          </el-form-item>
          <el-form-item label="访问级别">
            <el-select v-model="importForm.accessLevel">
              <el-option label="受限" value="restricted" />
              <el-option label="内部" value="internal" />
              <el-option label="公开" value="public" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="来源网址"><el-input v-model="importForm.sourceUrl" /></el-form-item>
        <el-form-item>
          <el-checkbox v-model="importForm.fulltextAllowed">
            已确认有权在本地保存、解析并展示这些文件的全文
          </el-checkbox>
        </el-form-item>
        <el-alert
          title="未勾选时只保存元数据、文件摘要和导入记录，不保留原文件或正文。"
          type="info"
          :closable="false"
        />
      </el-form>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!selectedFiles.length" @click="submitImport">
          开始导入
        </el-button>
      </template>
    </el-dialog>
  </main>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { getResearchResource, getResourceStats, importResearchResources, listResearchResources } from "../../api/research";
import type { ResearchResourceDetail, ResearchResourceStats, ResearchResourceSummary } from "../../types/research";

const emptyStats = (): ResearchResourceStats => ({
  total: 0,
  fulltext_total: 0,
  restricted_total: 0,
  type_counts: {},
  analysis_status_counts: {},
  copyright_status_counts: {}
});

const resourceTypes = [
  { value: "book", label: "书籍" },
  { value: "interview", label: "访谈" },
  { value: "paper", label: "论文" },
  { value: "video_subtitle", label: "视频字幕" },
  { value: "webpage", label: "网页" },
  { value: "policy", label: "政策" },
  { value: "note", label: "研究笔记" },
  { value: "other", label: "其他" }
];

const stats = ref(emptyStats());
const resources = ref<ResearchResourceSummary[]>([]);
const detail = ref<ResearchResourceDetail | null>(null);
const loading = ref(false);
const importing = ref(false);
const pageError = ref("");
const importVisible = ref(false);
const detailVisible = ref(false);
const selectedFiles = ref<File[]>([]);
const filters = reactive({ keyword: "", resourceType: "", educatorName: "" });
const importForm = reactive({
  resourceType: "other",
  educatorName: "",
  authors: "",
  sourceInstitution: "",
  sourceUrl: "",
  copyrightStatus: "unknown",
  accessLevel: "restricted",
  fulltextAllowed: false
});

function typeLabel(value: string): string {
  return resourceTypes.find((item) => item.value === value)?.label ?? value;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function refresh(): Promise<void> {
  loading.value = true;
  pageError.value = "";
  try {
    const [statsResponse, listResponse] = await Promise.all([
      getResourceStats(),
      listResearchResources(filters)
    ]);
    stats.value = statsResponse;
    resources.value = listResponse.items;
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : "资源库加载失败";
  } finally {
    loading.value = false;
  }
}

async function openDetail(resourceId: string): Promise<void> {
  try {
    detail.value = await getResearchResource(resourceId);
    detailVisible.value = true;
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "资源详情加载失败");
  }
}

function onFileChange(event: Event): void {
  const target = event.target as HTMLInputElement;
  selectedFiles.value = Array.from(target.files ?? []);
}

async function submitImport(): Promise<void> {
  if (!selectedFiles.value.length) return;
  importing.value = true;
  try {
    const form = new FormData();
    selectedFiles.value.forEach((file) => form.append("files", file));
    form.append("resource_type", importForm.resourceType);
    form.append("educator_name", importForm.educatorName);
    form.append("authors", importForm.authors);
    form.append("source_institution", importForm.sourceInstitution);
    form.append("source_url", importForm.sourceUrl);
    form.append("copyright_status", importForm.copyrightStatus);
    form.append("access_level", importForm.accessLevel);
    form.append("fulltext_allowed", String(importForm.fulltextAllowed));
    const result = await importResearchResources(form);
    const failures = result.results.filter((item) => item.status === "failed");
    await ElMessageBox.alert(
      `成功 ${result.succeeded}，重复 ${result.duplicates}，失败 ${result.failed}` +
        (failures.length ? `\n${failures.map((item) => `${item.file_name}：${item.error_message}`).join("\n")}` : ""),
      "导入结果"
    );
    importVisible.value = false;
    selectedFiles.value = [];
    await refresh();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "导入失败");
  } finally {
    importing.value = false;
  }
}

onMounted(refresh);
</script>

<style scoped>
.resource-page {
  min-height: 100vh;
  padding: 42px clamp(18px, 5vw, 72px) 72px;
  color: #193646;
  background:
    radial-gradient(circle at 88% 4%, rgba(220, 152, 68, 0.14), transparent 27%),
    linear-gradient(180deg, #f7f9f5 0%, #eef3ef 100%);
}

.resource-hero {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 28px;
  max-width: 1320px;
  margin: 0 auto 24px;
}

.resource-hero h1 { margin: 6px 0 10px; font-size: clamp(32px, 5vw, 58px); }
.resource-hero p { max-width: 760px; margin: 0; color: #58707c; line-height: 1.8; }
.eyebrow { color: #bd7133 !important; font-size: 12px; font-weight: 800; letter-spacing: 0.16em; text-transform: uppercase; }
.page-alert { max-width: 1320px; margin: 0 auto 18px; }

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  max-width: 1320px;
  margin: 0 auto 18px;
}

.stat-grid article, .library-card {
  border: 1px solid rgba(27, 67, 83, 0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 18px 45px rgba(40, 65, 74, 0.07);
}

.stat-grid article { display: flex; flex-direction: column; padding: 20px; }
.stat-grid span { color: #758993; font-size: 13px; }
.stat-grid strong { margin-top: 4px; font-size: 30px; }
.library-card { max-width: 1320px; margin: auto; padding: 20px; }
.filters { display: grid; grid-template-columns: minmax(260px, 2fr) minmax(150px, 1fr) minmax(150px, 1fr) auto; gap: 12px; margin-bottom: 18px; }
.title-button { display: block; padding: 0; border: 0; color: #174f69; background: none; cursor: pointer; font: inherit; font-weight: 800; text-align: left; }
.title-button:hover { text-decoration: underline; }
.title-button + small { display: block; margin-top: 5px; color: #81919a; }
.detail-stack { display: grid; gap: 20px; }
.detail-stack h2, .detail-stack h3, .detail-stack p { margin-top: 0; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 0; }
.detail-grid div { padding: 12px; border-radius: 12px; background: #f4f7f5; }
.detail-grid dt { color: #788a92; font-size: 12px; }
.detail-grid dd { margin: 6px 0 0; overflow-wrap: anywhere; }
.hash { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; }
.segment-card { margin-bottom: 10px; padding: 14px; border-left: 3px solid #cb7e3f; border-radius: 8px; background: #f6f7f3; }
.segment-card span { color: #8b6a4e; font-size: 12px; font-weight: 700; }
.segment-card p { margin: 8px 0 0; line-height: 1.7; white-space: pre-wrap; }
.import-form small { display: block; margin-top: 8px; color: #7b8c94; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.file-input { width: 100%; padding: 12px; border: 1px dashed #a7b7bd; border-radius: 10px; background: #f8faf8; }

@media (max-width: 760px) {
  .resource-hero { align-items: stretch; flex-direction: column; }
  .stat-grid { grid-template-columns: 1fr 1fr; }
  .filters, .form-grid, .detail-grid { grid-template-columns: 1fr; }
}
</style>
