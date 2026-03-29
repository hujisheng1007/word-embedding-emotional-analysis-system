<template>
  <el-card class="panel-card">
    <template #header>
      <div class="panel-header">
        <span>公开数据接入</span>
      </div>
    </template>

    <p class="panel-copy">
      从受控公开源拉取少量实时文本并直接分析，适合现场展示“真实数据接入”流程。
    </p>

    <el-select
      :model-value="selectedSourceId"
      class="full-width"
      placeholder="选择公开数据源"
      @update:model-value="emit('update:selectedSourceId', $event)"
    >
      <el-option
        v-for="item in sources"
        :key="item.id"
        :label="item.name"
        :value="item.id"
      />
    </el-select>

    <p v-if="currentSource" class="panel-status">{{ currentSource.description }}</p>

    <div class="panel-actions">
      <el-button type="success" :loading="loading" @click="emit('fetch')">
        获取并分析公开文本
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { PublicSource } from "../../types/analysis";

const props = defineProps<{
  loading: boolean;
  selectedSourceId: string;
  sources: PublicSource[];
}>();

const emit = defineEmits<{
  fetch: [];
  "update:selectedSourceId": [value: string];
}>();

const currentSource = computed(() =>
  props.sources.find((item) => item.id === props.selectedSourceId) ?? null
);
</script>
