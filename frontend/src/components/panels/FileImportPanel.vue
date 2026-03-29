<template>
  <el-card class="panel-card">
    <template #header>
      <div class="panel-header">
        <span>数据集与批量导入</span>
      </div>
    </template>

    <div class="dataset-selector">
      <p class="panel-copy">
        可以直接切换已经整理好的数据集，也可以上传新的 <code>.txt</code> 或 <code>.csv</code>
        文件重新分析。
      </p>

      <div class="panel-actions">
        <el-select
          :model-value="selectedDatasetId"
          class="dataset-select"
          placeholder="选择已整理数据集"
          @update:model-value="emit('update:selectedDatasetId', $event)"
        >
          <el-option
            v-for="dataset in datasets"
            :key="dataset.id"
            :label="dataset.name"
            :value="dataset.id"
          >
            <div class="dataset-option">
              <span>{{ dataset.name }}</span>
              <small>{{ dataset.record_count }} 条</small>
            </div>
          </el-option>
        </el-select>
        <el-button type="success" :loading="loading" @click="emit('load-dataset')">
          加载数据集
        </el-button>
      </div>

      <div v-if="selectedDatasetMeta" class="dataset-meta">
        <span>{{ selectedDatasetMeta.data_kind === "analysis" ? "分析结果集" : "原始导入集" }}</span>
        <span>{{ selectedDatasetMeta.record_count }} 条文本</span>
        <span>更新时间 {{ selectedDatasetMeta.updated_at }}</span>
        <span v-if="selectedDatasetMeta.attention_count > 0">
          重点关注 {{ selectedDatasetMeta.attention_count }} 条
        </span>
      </div>
      <p v-if="selectedDatasetMeta" class="panel-copy">{{ selectedDatasetMeta.description }}</p>
    </div>

    <div class="panel-divider" />

    <p class="panel-copy">
      TXT 按行解析，CSV 优先读取 <code>text</code> / <code>文本</code> / <code>内容</code> 列，并在导入时自动去重。
    </p>

    <div class="panel-actions">
      <el-button type="primary" :loading="loading" @click="openFileDialog">
        选择文件并分析
      </el-button>
      <span v-if="filename" class="file-name">{{ filename }}</span>
    </div>

    <div v-if="importSummary" class="import-summary-grid">
      <div class="import-stat">
        <strong>{{ importSummary.total_entries }}</strong>
        <span>读取条目</span>
      </div>
      <div class="import-stat">
        <strong>{{ importSummary.extracted_count }}</strong>
        <span>有效文本</span>
      </div>
      <div class="import-stat">
        <strong>{{ importSummary.duplicates_removed }}</strong>
        <span>去重条数</span>
      </div>
      <div class="import-stat">
        <strong>{{ importSummary.empty_removed }}</strong>
        <span>空白剔除</span>
      </div>
    </div>

    <p v-if="importSummary?.detected_column" class="panel-copy">
      当前 CSV 识别列：<code>{{ importSummary.detected_column }}</code>
    </p>
    <p class="panel-status">{{ statusMessage }}</p>

    <input
      ref="inputRef"
      class="hidden-input"
      type="file"
      accept=".txt,.csv"
      @change="handleFileChange"
    />
  </el-card>
</template>

<script setup lang="ts">
import { ref } from "vue";

import type { DatasetOption, ImportSummary } from "../../types/analysis";

defineProps<{
  filename: string;
  loading: boolean;
  statusMessage: string;
  datasets: DatasetOption[];
  selectedDatasetId: string;
  selectedDatasetMeta: DatasetOption | null;
  importSummary: ImportSummary | null;
}>();

const emit = defineEmits<{
  import: [file: File];
  "load-dataset": [];
  "update:selectedDatasetId": [datasetId: string];
}>();

const inputRef = ref<HTMLInputElement | null>(null);

function openFileDialog(): void {
  inputRef.value?.click();
}

function handleFileChange(event: Event): void {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) {
    return;
  }

  emit("import", file);
  target.value = "";
}
</script>
