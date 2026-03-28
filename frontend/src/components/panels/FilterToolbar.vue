<template>
  <el-card class="panel-card">
    <template #header>
      <div class="panel-header">
        <span>搜索与筛选</span>
        <span class="toolbar-count">当前展示 {{ filteredCount }} / {{ total }}</span>
      </div>
    </template>

    <div class="toolbar-grid">
      <el-input
        :model-value="searchText"
        placeholder="搜索文本内容或关键词"
        clearable
        @update:model-value="emit('update:searchText', $event)"
      />

      <el-select
        :model-value="categoryFilter"
        placeholder="类别筛选"
        @update:model-value="emit('update:categoryFilter', $event)"
      >
        <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
      </el-select>

      <el-select
        :model-value="levelFilter"
        placeholder="等级筛选"
        @update:model-value="emit('update:levelFilter', $event)"
      >
        <el-option v-for="item in levels" :key="item" :label="item" :value="item" />
      </el-select>

      <el-switch
        :model-value="attentionOnly"
        inline-prompt
        active-text="重点"
        inactive-text="全部"
        @update:model-value="emit('update:attentionOnly', $event)"
      />

      <el-button @click="emit('reset')">重置筛选</el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
defineProps<{
  attentionOnly: boolean;
  categories: string[];
  categoryFilter: string;
  filteredCount: number;
  levelFilter: string;
  levels: string[];
  searchText: string;
  total: number;
}>();

const emit = defineEmits<{
  "update:attentionOnly": [value: boolean];
  "update:categoryFilter": [value: string];
  "update:levelFilter": [value: string];
  "update:searchText": [value: string];
  reset: [];
}>();
</script>
