<template>
  <main class="showcase-page">
    <section class="hero-band">
      <div class="hero-copy">
        <p class="hero-kicker">Paper-driven Demo</p>
        <h1>教育家三重人格量化映射台</h1>
        <p class="hero-summary">
          这版页面继续沿用论文里的“自然人格 → 职业人格 → 道德人格”主轴，但把每一层再细分成更具体的品质与行为，
          并为每个细项补上可参考的量化口径。单条输入、导入文本和在线抓取内容都会统一映射到这套结构上。
        </p>
        <div class="hero-meta">
          <span>15 个细化品质/行为指标</span>
          <span>4 类统一量化参考口径</span>
          <span>超长传记文本自动分段汇总</span>
        </div>
      </div>

      <section class="status-card">
        <div class="status-row">
          <span>当前状态</span>
          <strong>{{ dashboardStore.statusMessage }}</strong>
        </div>
        <div class="status-tags">
          <el-tag effect="plain" type="success">
            {{ dashboardStore.connectionMode === "api" ? "接口模式" : "本地演示模式" }}
          </el-tag>
          <el-tag effect="plain" type="warning" v-if="dashboardStore.systemStatus?.foundation_model_name">
            {{ dashboardStore.systemStatus.foundation_model_name }}
          </el-tag>
        </div>
        <div class="status-mini-grid">
          <article>
            <strong>{{ totalIndicatorCount }}</strong>
            <span>细化指标</span>
          </article>
          <article>
            <strong>{{ longTextCount }}</strong>
            <span>长文本样本</span>
          </article>
          <article>
            <strong>{{ dashboardStore.referenceLibrary.total_excerpts }}</strong>
            <span>底库切片</span>
          </article>
        </div>
        <div class="switcher-row">
          <el-select
            v-model="dashboardStore.selectedFoundationProfileId"
            placeholder="选择解释增强档案"
            class="full-width"
          >
            <el-option
              v-for="profile in dashboardStore.foundationProfiles"
              :key="profile.id"
              :label="profile.label"
              :value="profile.id"
            />
          </el-select>
          <el-button
            type="primary"
            :loading="dashboardStore.foundationSwitching"
            @click="dashboardStore.activateSelectedFoundationProfile"
          >
            切换
          </el-button>
        </div>
      </section>
    </section>

    <section class="paper-rail">
      <article
        v-for="dimension in dashboardStore.referenceLibrary.dimensions"
        :key="dimension.id"
        class="pillar-step"
      >
        <span class="pillar-index">{{ pillarIndexMap[dimension.id] }}</span>
        <div>
          <h3>{{ dimension.name }}</h3>
          <p>{{ dimension.description }}</p>
        </div>
      </article>
    </section>

    <section class="paper-grid">
      <details class="fold-card" open>
        <summary>
          <div>
            <p class="section-kicker">Paper Notes</p>
            <h2>论文转译与量化口径</h2>
          </div>
          <span>展开 / 收起</span>
        </summary>
        <div class="fold-body">
          <div class="note-grid note-grid-wide">
            <article>
              <strong>结构拆分</strong>
              <p>三个人格下面继续拆成“品质”与“行为”两类子项，便于既看稳定特质，也看可观察实践。</p>
            </article>
            <article>
              <strong>量化参考</strong>
              <p>每个子项统一给出关键词命中数、线索多样度、段落覆盖率、千字证据密度四类参考阈值。</p>
            </article>
            <article>
              <strong>长文本分析</strong>
              <p>遇到长篇传记、人物小传或口述材料时，系统会先按叙事片段拆分，再汇总出总体人格判断。</p>
            </article>
            <article>
              <strong>演示定位</strong>
              <p>这仍然是为了展示你现有框架可迁移能力而做的临时页，核心底层数据结构保留可恢复空间。</p>
            </article>
          </div>
        </div>
      </details>

      <details
        v-for="dimension in dashboardStore.referenceLibrary.dimensions"
        :key="`fold-${dimension.id}`"
        class="fold-card"
        open
      >
        <summary>
          <div>
            <p class="section-kicker">Base Layer</p>
            <h2>{{ dimension.name }}</h2>
          </div>
          <span>{{ dimension.indicators.length }} 个细化指标</span>
        </summary>
        <div class="fold-body">
          <p class="dimension-description">{{ dimension.description }}</p>

          <div class="dimension-stat-row">
            <article class="dimension-stat">
              <strong>{{ countIndicatorsByType(dimension.id, "quality") }}</strong>
              <span>品质</span>
            </article>
            <article class="dimension-stat">
              <strong>{{ countIndicatorsByType(dimension.id, "behavior") }}</strong>
              <span>行为</span>
            </article>
            <article class="dimension-stat">
              <strong>{{ dimension.excerpt_count }}</strong>
              <span>底库切片</span>
            </article>
          </div>

          <div class="chip-row">
            <span
              v-for="questionId in dimension.question_ids"
              :key="`${dimension.id}-${questionId}`"
              class="term-chip"
            >
              {{ questionId }}
            </span>
          </div>

          <div class="chip-row">
            <span
              v-for="keyword in dimension.keyword_cues.slice(0, 10)"
              :key="`${dimension.id}-${keyword}`"
              class="soft-chip"
            >
              {{ keyword }}
            </span>
          </div>

          <div class="indicator-catalog">
            <details
              v-for="(indicator, indicatorIndex) in dimension.indicators"
              :key="indicator.id"
              class="mini-fold indicator-fold"
              :open="indicatorIndex === 0"
            >
              <summary class="indicator-summary">
                <div class="indicator-summary-copy">
                  <span class="type-chip">{{ aspectTypeLabel(indicator.aspect_type) }}</span>
                  <strong>{{ indicator.name }}</strong>
                </div>
                <span>{{ indicator.metric_benchmarks.length }} 项参考</span>
              </summary>
              <div class="fold-body indicator-body">
                <p>{{ indicator.description }}</p>
                <div class="chip-row">
                  <span
                    v-for="questionId in indicator.question_ids"
                    :key="`${indicator.id}-${questionId}`"
                    class="term-chip"
                  >
                    {{ questionId }}
                  </span>
                </div>
                <div class="chip-row">
                  <span
                    v-for="cue in indicator.keyword_cues"
                    :key="`${indicator.id}-${cue}`"
                    class="soft-chip"
                  >
                    {{ cue }}
                  </span>
                </div>
                <div class="metric-benchmark-grid">
                  <article
                    v-for="metric in indicator.metric_benchmarks"
                    :key="`${indicator.id}-${metric.id}`"
                    class="metric-benchmark-card"
                  >
                    <div class="metric-benchmark-head">
                      <strong>{{ metric.name }}</strong>
                      <span>{{ metric.unit }}</span>
                    </div>
                    <p>{{ metric.description }}</p>
                    <div class="benchmark-scale">
                      <span>低 {{ metric.low }}</span>
                      <span>中 {{ metric.medium }}</span>
                      <span>高 {{ metric.high }}</span>
                    </div>
                  </article>
                </div>
              </div>
            </details>
          </div>

          <div class="chip-row" v-if="dimension.highlight_terms.length">
            <span
              v-for="term in dimension.highlight_terms.slice(0, 6)"
              :key="`${dimension.id}-${term.keyword}`"
              class="term-chip"
            >
              {{ term.keyword }} · {{ term.count }}
            </span>
          </div>

          <blockquote v-if="dimension.sample_quotes[0]" class="dimension-quote">
            {{ dimension.sample_quotes[0].text }}
          </blockquote>
        </div>
      </details>
    </section>

    <section class="metrics-grid metrics-grid-six">
      <article class="metric-card">
        <span class="metric-label">底库切片</span>
        <strong class="metric-value">{{ dashboardStore.referenceLibrary.total_excerpts }}</strong>
      </article>
      <article class="metric-card">
        <span class="metric-label">访谈教师</span>
        <strong class="metric-value">{{ dashboardStore.referenceLibrary.total_respondents }}</strong>
      </article>
      <article class="metric-card">
        <span class="metric-label">细化指标</span>
        <strong class="metric-value">{{ totalIndicatorCount }}</strong>
      </article>
      <article class="metric-card">
        <span class="metric-label">当前样本</span>
        <strong class="metric-value">{{ dashboardStore.batchData.summary.total }}</strong>
      </article>
      <article class="metric-card">
        <span class="metric-label">长文本样本</span>
        <strong class="metric-value">{{ longTextCount }}</strong>
      </article>
      <article class="metric-card">
        <span class="metric-label">平均显现度</span>
        <strong class="metric-value accent">{{ formatPercent(dashboardStore.batchData.summary.avg_score) }}</strong>
      </article>
    </section>

    <section class="workspace-grid">
      <section class="control-panel">
        <div class="section-heading compact">
          <div>
            <p class="section-kicker">Live Input</p>
            <h2>长文本与在线内容分析入口</h2>
          </div>
          <p>适合直接粘贴传记、人物小传、访谈长文、课堂叙事和项目材料，系统会自动做分段汇总。</p>
        </div>

        <article class="panel-card action-card">
          <div class="panel-header">
            <span>单条文本映射</span>
            <el-tag effect="plain">{{ dashboardStore.connectionMode === "api" ? "接口" : "本地" }}</el-tag>
          </div>
          <p class="supporting-copy long-text-note">
            建议在这里直接贴入长篇材料。文本长度较长时会自动触发叙事分段，帮助区分不同段落落在哪一层人格与哪些品质/行为上。
          </p>
          <el-input
            v-model="quickDraft"
            type="textarea"
            :autosize="{ minRows: 10, maxRows: 24 }"
            :maxlength="40000"
            show-word-limit
            placeholder="输入一段教师传记、教育叙事、人物小传、教育家生平片段或在线长文本。"
          />
          <div class="action-row action-row-wrap">
            <el-button type="primary" :loading="dashboardStore.loading" @click="dashboardStore.runQuickAnalysis(quickDraft)">
              立即分析
            </el-button>
            <el-button text @click="fillDemoText">填入短文本示例</el-button>
            <el-button text @click="fillBiographyDemo">填入传记示例</el-button>
            <el-button text @click="quickDraft = ''">清空</el-button>
          </div>
          <div v-if="dashboardStore.quickAnalysis" class="quick-result">
            <div class="result-chip-row">
              <span class="solid-chip">{{ dashboardStore.quickAnalysis.category }}</span>
              <span class="solid-chip muted">{{ dashboardStore.quickAnalysis.level }}</span>
              <span class="solid-chip muted">{{ formatPercent(dashboardStore.quickAnalysis.score) }}</span>
              <span class="solid-chip muted">{{ dashboardStore.quickAnalysis.text_length }} 字</span>
              <span
                v-if="dashboardStore.quickAnalysis.is_long_text"
                class="solid-chip muted"
              >
                自动分段 {{ dashboardStore.quickAnalysis.segment_count }} 段
              </span>
            </div>
            <p class="quick-result-copy">{{ dashboardStore.quickAnalysis.llm_explanation }}</p>
            <div class="quick-insight-grid">
              <article
                v-if="topDimensionScores(dashboardStore.quickAnalysis).length"
                class="quick-insight-card"
              >
                <strong class="quick-insight-title">三重人格对比</strong>
                <div class="quick-score-list">
                  <div
                    v-for="item in topDimensionScores(dashboardStore.quickAnalysis)"
                    :key="`quick-dimension-${item.id}`"
                    class="quick-score-item"
                  >
                    <div class="quick-score-row">
                      <span>{{ item.name }}</span>
                      <strong>{{ formatPercent(item.score) }}</strong>
                    </div>
                    <el-progress
                      :percentage="Math.round(item.score * 100)"
                      :show-text="false"
                      color="#207567"
                    />
                  </div>
                </div>
              </article>
              <article
                v-if="topIndicatorScores(dashboardStore.quickAnalysis).length"
                class="quick-insight-card"
              >
                <strong class="quick-insight-title">核心品质 / 行为</strong>
                <div class="quick-indicator-list">
                  <div
                    v-for="item in topIndicatorScores(dashboardStore.quickAnalysis)"
                    :key="`quick-indicator-${item.id}`"
                    class="quick-indicator-item"
                  >
                    <div class="quick-score-row">
                      <div class="indicator-summary-copy">
                        <span class="type-chip">{{ aspectTypeLabel(item.aspect_type) }}</span>
                        <span>{{ item.name }}</span>
                      </div>
                      <strong>{{ formatPercent(item.score) }}</strong>
                    </div>
                    <div class="chip-row" v-if="item.matched_keywords.length">
                      <span
                        v-for="keyword in item.matched_keywords.slice(0, 5)"
                        :key="`quick-${item.id}-${keyword}`"
                        class="term-chip"
                      >
                        {{ keyword }}
                      </span>
                    </div>
                    <p class="quick-metric-line">{{ buildMetricSummary(item) }}</p>
                  </div>
                </div>
              </article>
              <article
                v-if="dashboardStore.quickAnalysis.segment_previews?.length"
                class="quick-insight-card"
              >
                <strong class="quick-insight-title">片段摘要</strong>
                <div class="quick-segment-list">
                  <div
                    v-for="segment in dashboardStore.quickAnalysis.segment_previews.slice(0, 3)"
                    :key="`quick-segment-${segment.index}`"
                    class="quick-segment-item"
                  >
                    <div class="quick-score-row">
                      <span>片段 {{ segment.index }}</span>
                      <strong>{{ segment.category }} / {{ formatPercent(segment.score) }}</strong>
                    </div>
                    <p>{{ segment.excerpt }}</p>
                  </div>
                </div>
              </article>
            </div>
            <PersonalityBreakdownPanel
              :result="dashboardStore.quickAnalysis"
              compact
            />
          </div>
        </article>

        <article class="panel-card action-card">
          <div class="panel-header">
            <span>批量导入</span>
          </div>
          <p class="supporting-copy">
            可导入 `TXT/CSV`。如果文件里存的是较长传记或人物材料，也会按长文本规则自动切分分析。
          </p>
          <div class="stack-row">
            <el-select
              v-model="dashboardStore.selectedDatasetId"
              class="full-width"
              placeholder="选择已有数据集"
            >
              <el-option
                v-for="dataset in dashboardStore.datasets"
                :key="dataset.id"
                :label="dataset.name"
                :value="dataset.id"
              />
            </el-select>
            <el-button type="success" :loading="dashboardStore.datasetLoading" @click="dashboardStore.loadSelectedDataset">
              加载
            </el-button>
          </div>
          <p v-if="dashboardStore.selectedDatasetMeta" class="supporting-copy">
            {{ dashboardStore.selectedDatasetMeta.description }}
          </p>
          <div class="stack-row">
            <el-button type="primary" plain :loading="dashboardStore.loading" @click="openFileDialog">
              选择 TXT/CSV
            </el-button>
            <span v-if="dashboardStore.importFilename" class="inline-note">{{ dashboardStore.importFilename }}</span>
          </div>
          <details v-if="dashboardStore.importSummary" class="mini-fold" open>
            <summary>导入摘要</summary>
            <div class="import-grid">
              <div>
                <strong>{{ dashboardStore.importSummary.total_entries }}</strong>
                <span>读取条目</span>
              </div>
              <div>
                <strong>{{ dashboardStore.importSummary.extracted_count }}</strong>
                <span>有效文本</span>
              </div>
              <div>
                <strong>{{ dashboardStore.importSummary.duplicates_removed }}</strong>
                <span>去重</span>
              </div>
              <div>
                <strong>{{ dashboardStore.importSummary.empty_removed }}</strong>
                <span>空白剔除</span>
              </div>
            </div>
          </details>
          <input
            ref="fileInputRef"
            class="hidden-input"
            type="file"
            accept=".txt,.csv"
            @change="handleFileChange"
          />
        </article>

        <article class="panel-card action-card">
          <div class="panel-header">
            <span>在线源抓取</span>
          </div>
          <div class="stack-row">
            <el-select
              v-model="dashboardStore.selectedPublicSourceId"
              class="full-width"
              placeholder="选择在线文本源"
            >
              <el-option
                v-for="item in dashboardStore.publicSources"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
            <el-button type="warning" :loading="dashboardStore.publicLoading" @click="dashboardStore.fetchSelectedPublicSource">
              抓取
            </el-button>
          </div>
          <p class="supporting-copy">{{ currentPublicSourceDescription }}</p>
        </article>
      </section>

      <section class="charts-panel">
        <DistributionChart
          title="三重人格分布"
          :data="dashboardStore.batchData.summary.category_distribution"
        />
        <DistributionChart
          title="人格显现等级"
          :data="dashboardStore.batchData.summary.level_distribution"
        />
        <WordCloudChart :items="dashboardStore.batchData.summary.wordcloud_keywords" />
      </section>
    </section>

    <details class="fold-card results-fold" open>
      <summary>
        <div>
          <p class="section-kicker">Mapped Corpus</p>
          <h2>在线文本结果</h2>
        </div>
        <span>{{ dashboardStore.filteredResults.length }} 条结果 · 展开 / 收起</span>
      </summary>
      <div class="fold-body results-fold-body">
        <section class="results-shell">
          <section class="panel-card result-table-card">
        <div class="section-heading compact">
          <div>
            <p class="section-kicker">Mapped Corpus</p>
            <h2>在线文本结果</h2>
          </div>
          <p>表格里会直接标出长文本，并保留主人格、显现等级和命中的关键线索。</p>
        </div>

        <div class="filters-row">
          <el-input
            v-model="dashboardStore.searchText"
            placeholder="搜索文本、关键词或人格层面"
            clearable
          />
          <el-select v-model="dashboardStore.categoryFilter">
            <el-option v-for="item in dashboardStore.categories" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select v-model="dashboardStore.levelFilter">
            <el-option v-for="item in dashboardStore.levels" :key="item" :label="item" :value="item" />
          </el-select>
          <el-switch
            v-model="dashboardStore.attentionOnly"
            inline-prompt
            active-text="重点"
            inactive-text="全部"
          />
        </div>

        <el-table
          :data="dashboardStore.filteredResults"
          stripe
          class="mapping-table"
          @row-click="dashboardStore.selectResult"
        >
          <el-table-column label="文本样本" min-width="420">
            <template #default="{ row }">
              <div class="table-text">{{ formatExcerpt(row.text, 170) }}</div>
              <div class="table-meta">
                <span class="meta-inline">{{ row.text_length }} 字</span>
                <span v-if="row.is_long_text" class="meta-inline">长文本 · {{ row.segment_count }} 段</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="category" label="主人格" min-width="120" />
          <el-table-column prop="level" label="显现等级" min-width="120" />
          <el-table-column label="显现度" min-width="110">
            <template #default="{ row }">{{ formatPercent(row.score) }}</template>
          </el-table-column>
          <el-table-column label="关键词" min-width="220">
            <template #default="{ row }">
              <div class="chip-row">
                <span v-for="keyword in row.keywords.slice(0, 4)" :key="`${row.text}-${keyword}`" class="term-chip">
                  {{ keyword }}
                </span>
              </div>
            </template>
          </el-table-column>
        </el-table>
          </section>

          <section class="panel-card detail-card" v-if="dashboardStore.selectedResult">
        <div class="section-heading compact">
          <div>
            <p class="section-kicker">Selected Sample</p>
            <h2>细化指标拆解</h2>
          </div>
          <p>{{ dashboardStore.selectedResult.category }} / {{ dashboardStore.selectedResult.level }}</p>
        </div>

        <p class="detail-text">{{ dashboardStore.selectedResult.text }}</p>
        <div class="result-chip-row">
          <span class="solid-chip">{{ dashboardStore.selectedResult.category }}</span>
          <span class="solid-chip muted">{{ dashboardStore.selectedResult.level }}</span>
          <span class="solid-chip muted">{{ formatPercent(dashboardStore.selectedResult.score) }}</span>
          <span class="solid-chip muted">{{ dashboardStore.selectedResult.text_length }} 字</span>
          <span v-if="dashboardStore.selectedResult.is_long_text" class="solid-chip muted">
            自动分段 {{ dashboardStore.selectedResult.segment_count }} 段
          </span>
        </div>

        <details class="mini-fold" open>
          <summary>分析说明</summary>
          <div class="fold-body">
            <p>{{ dashboardStore.selectedResult.llm_explanation }}</p>
            <p class="supporting-copy">{{ dashboardStore.selectedResult.rule_reason }}</p>
          </div>
        </details>

        <details class="mini-fold" open v-if="dashboardStore.selectedResult.dimension_scores?.length">
          <summary>三重人格占比与具体分析</summary>
          <div class="fold-body">
            <PersonalityBreakdownPanel :result="dashboardStore.selectedResult" />
          </div>
        </details>

        <details class="mini-fold" open v-if="dashboardStore.selectedResult.dimension_scores?.length">
          <summary>三重人格评分</summary>
          <div class="dimension-score-list">
            <div
              v-for="item in dashboardStore.selectedResult.dimension_scores"
              :key="`${dashboardStore.selectedResult.text}-${item.id}`"
              class="dimension-score-item"
            >
              <div class="dimension-score-head">
                <span>{{ item.name }}</span>
                <strong>{{ formatPercent(item.score) }}</strong>
              </div>
              <el-progress
                :percentage="Math.round(item.score * 100)"
                :show-text="false"
                color="#207567"
              />
              <p>{{ item.description }}</p>
              <div class="chip-row" v-if="item.matched_keywords.length">
                <span
                  v-for="keyword in item.matched_keywords.slice(0, 6)"
                  :key="`${item.id}-${keyword}`"
                  class="term-chip"
                >
                  {{ keyword }}
                </span>
              </div>
            </div>
          </div>
        </details>

        <details class="mini-fold" open v-if="dashboardStore.selectedResult.indicator_scores?.length">
          <summary>品质 / 行为细化结果</summary>
          <div class="result-indicator-grid">
            <article
              v-for="item in dashboardStore.selectedResult.indicator_scores"
              :key="`${dashboardStore.selectedResult.text}-${item.id}`"
              class="result-indicator-card"
            >
              <div class="dimension-score-head">
                <div class="indicator-summary-copy">
                  <span class="type-chip">{{ aspectTypeLabel(item.aspect_type) }}</span>
                  <strong>{{ item.name }}</strong>
                </div>
                <strong>{{ formatPercent(item.score) }}</strong>
              </div>
              <p>{{ item.description }}</p>
              <div class="chip-row" v-if="item.matched_keywords.length">
                <span
                  v-for="keyword in item.matched_keywords.slice(0, 8)"
                  :key="`${item.id}-${keyword}`"
                  class="term-chip"
                >
                  {{ keyword }}
                </span>
              </div>
              <div class="metric-result-grid">
                <article
                  v-for="metric in item.metric_results"
                  :key="`${item.id}-${metric.id}`"
                  class="metric-result-card"
                >
                  <div class="metric-result-head">
                    <strong>{{ metric.name }}</strong>
                    <span :class="['metric-band', metricBandClass(metric.band)]">{{ metric.band }}</span>
                  </div>
                  <div class="metric-result-value">{{ metric.value }} {{ metric.unit }}</div>
                  <p>{{ metric.description }}</p>
                  <div class="benchmark-scale">
                    <span>低 {{ metric.low }}</span>
                    <span>中 {{ metric.medium }}</span>
                    <span>高 {{ metric.high }}</span>
                  </div>
                </article>
              </div>
            </article>
          </div>
        </details>

        <details class="mini-fold" open v-if="dashboardStore.selectedResult.segment_previews?.length">
          <summary>长文本分段拆解</summary>
          <div class="segment-list">
            <article
              v-for="segment in dashboardStore.selectedResult.segment_previews"
              :key="`${dashboardStore.selectedResult.text}-${segment.index}`"
              class="segment-card"
            >
              <div class="segment-head">
                <strong>片段 {{ segment.index }}</strong>
                <span>{{ segment.category }} / {{ segment.level }} / {{ formatPercent(segment.score) }}</span>
              </div>
              <p>{{ segment.excerpt }}</p>
              <div class="chip-row">
                <span
                  v-for="keyword in segment.keywords"
                  :key="`${segment.index}-${keyword}`"
                  class="term-chip"
                >
                  {{ keyword }}
                </span>
              </div>
            </article>
          </div>
        </details>

        <details class="mini-fold" v-if="dashboardStore.selectedResult.reference_quotes?.length">
          <summary>底库参照引文</summary>
          <blockquote
            v-for="quote in dashboardStore.selectedResult.reference_quotes"
            :key="quote"
            class="reference-quote"
          >
            {{ quote }}
          </blockquote>
        </details>
          </section>
        </section>
      </div>
    </details>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import PersonalityBreakdownPanel from "../../components/analysis/PersonalityBreakdownPanel.vue";
import DistributionChart from "../../components/charts/DistributionChart.vue";
import WordCloudChart from "../../components/charts/WordCloudChart.vue";
import { useDashboardStore } from "../../stores/dashboard";
import type { AnalysisResult, DimensionScore, IndicatorScore } from "../../types/analysis";

const dashboardStore = useDashboardStore();
const quickDraft = ref("");
const fileInputRef = ref<HTMLInputElement | null>(null);

const pillarIndexMap: Record<string, string> = {
  natural_personality: "01",
  professional_personality: "02",
  moral_personality: "03"
};

const currentPublicSourceDescription = computed(() => {
  const source = dashboardStore.publicSources.find(
    (item) => item.id === dashboardStore.selectedPublicSourceId
  );
  return source?.description ?? "将公开在线文本临时抓取后，再映射到论文中的三重人格结构中。";
});

const totalIndicatorCount = computed(() =>
  dashboardStore.referenceLibrary.dimensions.reduce(
    (sum, dimension) => sum + dimension.indicators.length,
    0
  )
);

const longTextCount = computed(
  () => dashboardStore.batchData.results.filter((item) => item.is_long_text).length
);

function countIndicatorsByType(dimensionId: string, aspectType: string): number {
  const dimension = dashboardStore.referenceLibrary.dimensions.find((item) => item.id === dimensionId);
  return dimension?.indicators.filter((item) => item.aspect_type === aspectType).length ?? 0;
}

function aspectTypeLabel(aspectType: string): string {
  return aspectType === "behavior" ? "行为" : "品质";
}

function metricBandClass(band: string): string {
  if (band === "高") {
    return "band-high";
  }
  if (band === "中") {
    return "band-medium";
  }
  if (band === "低") {
    return "band-low";
  }
  return "band-pending";
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatExcerpt(text: string, limit: number): string {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) {
    return normalized;
  }
  return `${normalized.slice(0, limit)}...`;
}

function topDimensionScores(result: AnalysisResult | null, limit = 3): DimensionScore[] {
  return [...(result?.dimension_scores ?? [])]
    .sort((left, right) => right.score - left.score)
    .slice(0, limit);
}

function topIndicatorScores(result: AnalysisResult | null, limit = 3): IndicatorScore[] {
  return [...(result?.indicator_scores ?? [])]
    .sort((left, right) => right.score - left.score)
    .slice(0, limit);
}

function buildMetricSummary(indicator: IndicatorScore): string {
  return indicator.metric_results
    .slice(0, 4)
    .map((metric) => `${metric.name}${metric.value}${metric.unit}（${metric.band}）`)
    .join(" · ");
}

function fillDemoText(): void {
  quickDraft.value =
    "我会把课堂反馈和项目实践都放进教学设计里，让学生在真实任务中获得回应、修正和成长。";
}

function fillBiographyDemo(): void {
  quickDraft.value = `他早年在乡村小学任教，最初的条件并不好，但始终坚持先理解学生的处境，再决定怎么教。

后来进入师范院校后，他一边持续阅读教育学与心理学著作，一边把新方法带回课堂，反复调整讨论节奏、项目任务和反馈方式，逐渐形成了自己的教学风格。

在学校改革最困难的阶段，他并没有把精力只放在个人成果上，而是主动协调同事、家长和社区资源，希望让更多学生真正受益。

他经常说，教育不仅是知识训练，更是文化传承、责任培育与人格唤醒；如果教师自己不能守住热爱、专业和担当，就很难把这些力量传给下一代。

即使后来获得许多荣誉，他仍然把更多时间投入到青年教师培养、薄弱地区支持和课程改进中，总强调教育者要把光亮留给后来者。`;
}

function openFileDialog(): void {
  fileInputRef.value?.click();
}

function handleFileChange(event: Event): void {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) {
    return;
  }

  void dashboardStore.importTextFile(file);
  target.value = "";
}

onMounted(() => {
  void dashboardStore.bootstrap();
});
</script>
