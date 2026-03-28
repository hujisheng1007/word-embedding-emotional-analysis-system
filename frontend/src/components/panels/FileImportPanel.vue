<template>
  <el-card class="panel-card">
    <template #header>
      <div class="panel-header">
        <span>批量导入文本</span>
      </div>
    </template>

    <p class="panel-copy">
      当前支持导入 <code>.txt</code> 和 <code>.csv</code> 文件。TXT 按行解析，CSV 优先读取
      <code>text</code> / <code>文本</code> / <code>内容</code> 列。
    </p>

    <div class="panel-actions">
      <el-button type="primary" :loading="loading" @click="openFileDialog">
        选择文件并分析
      </el-button>
      <span v-if="filename" class="file-name">{{ filename }}</span>
    </div>

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

const props = defineProps<{
  filename: string;
  loading: boolean;
  statusMessage: string;
}>();

const emit = defineEmits<{
  import: [file: File];
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
