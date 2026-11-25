# Rest四成分叙事证据分析 系统调整方案与代码逻辑链

初稿日期：2026-10-28；研究范围修订：2026-10-29
状态：基于当前源代码完成的实施设计；本文列出的新模块、接口与数据库表尚未实现。此次仅新增方案文档，不代表完成系统升级或实证分析。

## 1. 本轮目标与研究边界

系统建议名称：中国经典教育家多模态资料与道德行动研究平台。
研究主体：中国经典教育家群体。以现有14位教育家资料作为种子语料，依据明确的纳入标准扩展人物、来源和模态；不据此声称覆盖所有中国教育家或具有总体代表性。
研究目标：通过大规模语料挖掘与跨人物、跨来源分析，提取情境化教育典范，考察叙事中的道德判断、价值权衡与育人行为模式，检验多源、多模态材料带来的信息增益。
分析层级：人物—来源—事件叙述版本—原始证据。事件是基础分析单元；研究结论需在跨人物比较和模式分析中形成。

修订后的研究问题：
- RQ1：不同教育情境下，中国经典教育家资料呈现哪些道德问题、价值权衡和育人行动模式？跨人物有哪些共同点与差异？
- RQ2：多源、多模态材料相较单一传记文本，增加了哪些可核查事实、行动细节、限制条件或相反证据？
- RQ3：理论引导与数据驱动相结合，能否形成稳定、可解释且保留反例的候选教育典范？
- 方法验证：Rest编码、模型抽取与模式发现的结果能否被人工复核，跨来源与抽样条件变化时是否保持稳健？

Rest理论提供功能性过程框架，不提供本项目现成的文本分类器。下述代码本、状态和证据标准是本研究拟定的操作化规则，须经试编码与专家审查。四成分可同时出现，不是互斥类别、四步顺序或四维人格量表。没有记载不等于没有该心理过程；不生成道德人格总分、人物高低排名或四成分占比饼图。

学习迁移工具保留为后续方向。本轮先完成可靠的案例证据层，暂不开展培养效果推断。

## 2. 当前代码核查结果

| 位置 | 已有实现 | 调整判断 |
|---|---|---|
| backend/app/services/analysis_service.py | analyze_text实际调用规则评分，模型主要解释既有类别；请求mode没有在该入口决定三种研究条件 | 新建Rest分析编排服务，显式分派方法；旧接口保留为历史原型 |
| backend/app/services/scoring_service.py | 关键词命中、密度、覆盖和文本长度参与三重人格评分 | 不用于Rest证据判定；长文本不自动获得更强证据 |
| backend/app/engines/foundation_model/engine.py | 保留校园风险类别及校园文本解释提示；90 token解释预算 | 仅复用连接配置，另建结构化Rest抽取器及专用提示 |
| backend/app/utils/text_segmentation.py | 按220/320字符等阈值分段 | 作为旧展示切片；不能直接充当教育事件分割规则 |
| backend/app/db/research_models.py | 有资源、文本片段、视频字幕及原定位；无独立事件编码模型 | 复用原文层，新增不可变事件版本、分析与编码记录 |
| backend/app/services/collection_service.py::analyze_resource | 整份资源分析后用首个关键词字幕或正文前300字构造证据 | Rest入口必须改用确切证据跨度，禁止首段兜底引文 |
| backend/app/services/knowledge_service.py | 中文二元词等词法打分与原文片段检索；Hit@K/MRR按资源评测 | 可用于发现候选片段；另增事件检索与事件级评测，不能冒充语义或人格效度 |
| frontend/src/views/dashboard/DashboardView.vue等 | 主要围绕主人格、显现度、指标和分布展示 | 新建Rest工作台，历史画像单独标注 |

当前工作区已有未提交修改，涉及main.py、knowledge_service.py、App.vue等。实施时基于这些现状做增量修改，避免覆盖。已有导入资料和数据库不进入代码提交。

## 3. 理论编码合同

| component_id | 展示名 | 可支持的叙事证据 | 不充分情形 |
|---|---|---|---|
| sensitivity | 道德敏感性线索 | 主体注意并解释他人的需要、权益、潜在伤害或伦理问题 | 只有作者称其“关心学生”；只有“发现”这个词 |
| judgment | 道德判断线索 | 明确行动理由、伦理原则、责任或方案权衡 | 只有选择/决定，没有可辨认的伦理依据 |
| motivation | 道德价值优先线索 | 明确道德承诺或在竞争目标中赋予道德价值优先性的叙述；标明谁作出此归因 | 仅有资源有限、投入时间或助人行为，不能自动推断动机 |
| implementation | 道德行动实施线索 | 已采取的伦理相关行动、执行安排、应对障碍或持续实践 | 只有将来打算、口号或人物赞誉 |

“发现学生困难后采取行动”可以支持敏感性与实施，但不能自动补出判断和动机。单次行动可编码实施线索；是否持续或克服困难是独立子字段，不能无根据添加。行动未达预期结果不自动等于缺少实施过程。

每个成分保留独立状态：
- supported：在给定文本范围内存在符合代码本的支持证据。
- not_mentioned：给定文本范围内未见相关信息，不解释为人物缺失。
- insufficient：提到相关内容，但含糊、只有赞誉、归属不清或无法支持所作解释。
- counterevidence：有明确反向/受阻证据，须引用；不等同人物不道德。
- mixed：同一范围存在支持与相反证据，均保留并提交复核。

证据采用多个正交属性，不使用一个混合“高/中/低”分数：
- discourse_type：行为叙述、本人引语/自述、他者归因、赞誉、职业规范，可多选。
- epistemic_status：文本明确陈述 / 研究者推断。
- attribution：行为者、说话者、被评价者分别记录。
- span_validation：valid / invalid / ambiguous。
- review_status：pending / accepted / revised / excluded。

可定位只证明引文确实存在，不证明史实、语义解释或真实动机已被验证。叙述事实与经外部核实的历史事实分开。

## 4. 两层数据结构

事实层：主体、受影响者、情境、行动、明示理由、竞争目标、障碍、结果、时间及来源。字段允许为空，每项均带原文跨度；未知使用null并记录原因，不由模型补写。
解释层：四成分编码、支持/相反证据、解释依据、局限、人工审核。

底层片段 → 来源内事件版本 → 分析运行 → 四成分编码 → 引文跨度 → 人工独立编码/裁决 → 冻结数据集 → 统计报告。

一个来源可叙述多个事件，一个事件可涉及多个人物。多个来源描述同一历史事件时，建立event_cluster_id关联各来源版本，不拼成一个看似完整的合成叙事；跨来源关系需人工确认。聚类用于重复计数与分组划分。

## 5. 端到端处理逻辑

1. 选择研究资源与来源范围；读取已有全文/片段/字幕，不从元数据记录伪造全文。
2. 冻结原始文本、数据版本与SHA-256；登记语言、体裁、叙述视角、来源机构及日期。宣传倾向由规则与人工判断记录，不由域名自动决定。
3. 为相邻片段建立候选窗口。根据同一资源、连续位置、主体及时间线索合并；章节或明显事件切换处停止；允许人工拆分/扩展。模型建议的边界也需保留来源映射。
4. 事件资格标为eligible、uncertain或excluded，记录原因。无需四成分齐全，也不强制存在价值冲突或结果。赞誉性材料保留在筛选台账与对照样本中。
5. 冻结事件版本和事实层，按指定方法运行四成分编码。
6. 解析结构化输出，检验枚举、字段、四成分唯一性、引用的segment_id及字符范围。
7. 检验quote与原文切片完全一致。失败则标validation_failed或needs_review，不能用开头300字替代，也不能当作not_mentioned。
8. 保存模型候选，进入人工复核；独立编码模式隐藏模型输出及其他编码者答案。
9. 形成裁决版本，冻结代码本与研究样本，才进入正式统计导出。
10. 报告来源分层、成分覆盖、证据状态、编码一致性与模型性能；保留分母、筛选数量及失败率。

技术执行按步骤进行，不代表Rest心理过程按此顺序发生。

## 6. 代码文件改动清单

### 新增后端

- app/domain/rest_codebook_v1.json：四成分定义、准入排除、正反例、版本；试编码版本号v0.1，冻结后再v1.0。
- app/schemas/moral_analysis.py：事件、跨度、成分状态、请求与响应；严格校验，禁止多余人格score字段。
- app/db/moral_models.py：新增表与约束；在db/__init__.py和alembic/env.py显式注册。
- app/services/narrative_event_service.py：窗口、事件重建、来源快照、版本、去重关联。
- app/services/moral_analysis_service.py：三方法调度、持久化、任务状态、版本与失败处理。
- app/engines/moral/rule_engine.py：冻结的词典/规则基线，不输出人格高低。
- app/engines/moral/llm_engine.py：结构化调用；复用foundation_profile_service配置，不复用校园提示。
- app/engines/moral/prompts/direct_v1.txt与evidence_v1.txt：分别用于直接判断和证据约束；共享定义，实验时冻结提示。
- app/services/evidence_validation_service.py：引文与范围机械校验；语义支持仍由人工审核。
- app/services/moral_review_service.py：A/B独立编码、提交锁定、裁决、修改审计。
- app/services/moral_evaluation_service.py：数据集冻结、分组划分、分类/证据评价、导出。
- app/api/routes/moral_analysis.py：Rest新接口。
- alembic/versions/<next_revision>_moral_evidence.py：只新增研究表；执行前核验当前head，不硬编码假定revision。

### 修改接入点

- app/main.py：注册新路由，更新应用名称和介绍。
- app/services/collection_service.py：资源详情增加新事件分析入口；旧analyze_resource保留为legacy，不自动转换旧结果。
- app/services/knowledge_service.py与schemas/knowledge.py：保留原文搜索；新增事件搜索服务/接口，别改变旧检索结果语义。
- frontend/src/types/moral.ts、api/moral.ts：与后端合同一致。
- frontend/src/views/moral/MoralAnalysisView.vue：事件列表、事实与四成分证据。
- frontend/src/views/moral/EventReviewView.vue：原文高亮、编码、盲法和裁决。
- frontend/src/views/moral/MoralEvaluationView.vue：数据集选择、统计与导出。
- frontend/src/router/index.ts：新路由/analysis、/events/:id、/evaluation；完成验收后/转到/analysis，旧首页移动/legacy-profile。
- frontend/src/App.vue、frontend/index.html：品牌与导航一致；资源库、采集中心、知识检索继续可用。
- ResourceLibraryView.vue、KnowledgeResearchView.vue：资源到事件入口、成分/证据状态过滤与原文定位。

旧的分析服务、15指标、三重人格reference_library及风险提示不进入Rest数据链。可复用HTTP配置和错误处理，不能复用既有类别判定。

## 7. 数据库设计建议

| 新表 | 关键字段及作用 |
|---|---|
| narrative_events | id, resource_id, source_version, source_snapshot_sha256, event_revision, parent_revision_id, event_cluster_id, actor_ids_json, language, genre, narrator_type, eligibility, exclusion_reason, facts_json, created_by |
| event_source_spans | event_id, ordinal, segment_id, transcript_cue_id可空, start_char, end_char, source_text_snapshot, text_sha256, locator_snapshot；保留段落/时间戳，不生成不存在的页码 |
| moral_analysis_runs | event_id与版本, method, model/provider版本, prompt/codebook版本与hash, input_hash, config_json, status, raw_output, error_code, truncated, created_at |
| moral_coding_sets | event_id/version, origin(machine/human/adjudication), run_id可空, coder_id可空, codebook_version, submitted_at, supersedes_id, review_status；独立提交与裁决均形成新版本 |
| moral_component_codes | coding_set_id, component_id, status, rationale, limitations_json；唯一约束(coding_set_id,component_id)，每组必须四条 |
| moral_evidence_spans | component_code_id, event_source_span_id, start_char, end_char, quote, polarity, discourse_types_json, epistemic_status, attribution_json, validation_status |
| moral_review_actions | reviewer_id, coding_set_id, previous_version, new_version, action, reason, created_at；保留修改轨迹 |
| moral_study_datasets | id, name, split_manifest_json, selection_protocol, codebook_version, dataset_hash, frozen_at；样本清单包含事件版本与裁决版本 |
| moral_evaluation_runs | dataset_id/hash, analysis_run_ids, metrics_json, config_json, created_at；结果可复核 |

研究来源元数据以事件数据集快照保存，不能因后来编辑资源机构/体裁而悄悄改变已发表统计。运行记录不保存API密钥。引用资源使用RESTRICT或软删除保护，避免级联删除研究证据。

没有运行记录就表示未分析，不生成四个“未提及”。分析失败不进入已分析分母。一次模型成功不修改所有资源的全局状态为“研究完成”。

## 8. 接口合同与伪代码

建议API（均新增）：
- POST /api/moral/events/build：resource_ids与窗口设置，返回候选事件；批量任务返回202与job_id。
- GET /api/moral/events：按来源、人物、资格、审核状态分页。
- GET /api/moral/events/{id}：原文映射、事实层、版本及当前可见编码。
- POST /api/moral/events/{id}/revisions：调整边界/事实；旧分析保留但标明对应旧版。
- POST /api/moral/analyses：event_ids、event_revision、method、codebook_version；持久化任务。
- GET /api/moral/analyses/{run_id}：queued/running/succeeded/failed/cancelled/needs_review。
- POST /api/moral/codings：人工作答；服务端限制独立编码者读取未解盲答案。
- POST /api/moral/adjudications：保存分歧处理结果与理由。
- POST /api/moral/datasets/freeze：冻结研究清单和划分。
- POST /api/moral/evaluations：冻结集上的模型评价。
- GET /api/moral/exports：导出事件、编码、证据、版本和筛选清单。

```python
# 设计伪代码，不是已实现模块。
def analyze_event(event_id, revision, method, config):
    event = events.get_frozen_revision(event_id, revision)
    codebook = codebooks.get(config.codebook_version)
    inputs = make_model_input(event, codebook, config)
    run = runs.create(event, method, input_hash=sha256(inputs), config=config)
    try:
        candidate = engines[method].analyze(inputs)
        parsed = schema.validate(candidate)  # 失败不能转成“未提及”
        checks = evidence_validator.check(parsed, event.source_spans)
        return runs.save_candidate(run, parsed, checks, review_status="pending")
    except ModelUnavailable as exc:
        return runs.fail(run, "model_unavailable", str(exc))
    except (InvalidSchema, TruncatedOutput) as exc:
        return runs.fail(run, "invalid_output", str(exc))
```

rule、llm_direct、llm_evidence三个条件有明确方法标识。模型不可用时显示失败，可另行启动规则运行，但不能将规则结果伪装成模型结果。长任务使用持久化任务表/运行表与可恢复worker；重启后running任务变为可恢复，不无限挂起。不把整批图书分析放进同步HTTP请求。

证据合同示例：
```json
{
  "component_id": "motivation",
  "status": "not_mentioned",
  "rationale": "当前事件记录了帮助行为，未说明价值优先或承诺。",
  "evidence": [],
  "limitations": ["无此记录不代表主体不存在道德动机"],
  "review_status": "pending"
}
```

引文必须引用本次输入内的source_span_id与其原始文本。start_char包含、end_char不包含；统一Unicode码点计数，前端用Array.from转换，避免JavaScript UTF-16与Python码点错位。不得先清洗原文再对原始字符偏移定位；确需标准化必须保存双向映射。多段证据分别列跨度，不把省略号拼接文本当成逐字引文。出现同句多次必须指定唯一位置。

## 9. 三条件比较与研究统计

- 规则基线：同一冻结事件，按预定义线索运行；词命中只表示候选线索。
- 直接LLM：同一事件与代码本，输出四类状态，不强制引证。
- 证据约束LLM：同一事件与代码本，增加原文引用及证据不足出口。
- 主比较尽量保持同一模型、参数、输入与运行条件；记录重复运行和随机性。
- 三者均可比较状态分类；没有引文输出的直接条件不伪造引文定位分数，也不能用引文缺席定义其分类必然错误。若比较“无依据断言”，由独立人工按照相同标准审核三者所有断言。
- 先做人工A/B编码，报告裁决前一致性；再由裁决版本作为约定参照，而非人格真值。
- 开发集用于代码本和提示迭代，测试集封存。按人物、来源、重复事件簇构造隔离划分，跨组相连样本需同组；划分不足时明确报告限制。
- 来源比较不能只抽检索Top-K；建立分层抽样框，保留未涉及伦理过程的材料及排除理由。各来源未覆盖相同人物/时代时，只能做有边界的描述比较。

统计主单位：来源内事件版本。先报告每成分五状态分布及分母N，再报告支持率=supported事件数/N；mixed单列，可另报包含mixed的敏感性分析。四成分可共现，支持率不要求相加100%。未裁决、失败、排除分别计数，不混入正式分母。

研究报告包括：可编码性、人工一致性（含类别频数与不确定区间）、来源/人物分层状态分布、混合及相反案例、模型各类Precision/Recall/F1与Macro-F1、混淆矩阵、引文机械有效率、人工语义支持率、失败率与耗时。区间/统计推断考虑人物或文档内相关，不能把全部片段当独立样本。

## 10. 页面呈现

导航：事件分析｜研究资源库｜多源采集｜证据检索｜编码与评测。
事件详情左侧原文与定位，右侧事实层及四成分独立状态。点击任何支持/相反证据即可回到原文；“来源陈述”“模型解释”“人工意见”分区显示。

总览显示：资源数、候选事件数、已核验事件数、待复核数、模型失败数；图表为四成分状态矩阵与来源分组图，不用人格雷达图或总分。
审核有两种模式：研究盲法编码、日常辅助复核。后者可看模型建议，前者由服务端隔离建议、姓名遮蔽版本和其他编码者结果；不能只在界面隐藏。

## 11. 分阶段开发与验收

P0 数据与合同：完成代码本v0.1、严格schema、新增表、数据库备份与迁移演练。验收：旧表记录与内容校验不变，新表创建成功，字段可表示空缺/分歧/证据状态。
P1 最小闭环：一条实际资源→人工确认事件→四成分候选→原文定位→人工保存→导出。先支持研究者手工编码，规则作基线；接通一个真实模型后明确显示配置和运行状态。
P2 研究编码：A/B独立编码、版本锁定、裁决、42个候选窗口资格核查及小批量试跑。验收：盲法权限有效、分歧可复现、无覆盖原始判断。
P3 研究评测：冻结数据集、三条件比较、来源分层统计、实验报告导出。验收：相同数据版本可重算指标，失败不伪装成功，无测试集泄漏。
P4 学习应用：在研究证据稳定后，再增加教师困境检索、案例比较和学习效果实验。

最小必要测试：
1. 纯赞誉不自动获得四项supported；只有行动不能自动补出判断与动机。
2. 只有计划不判定已实施；明示冲突、受阻或反例可保存；不同成分可共现。
3. 编造引文、错主体、错片段、重复引文位置歧义进入拒绝/复核；机械校验不宣称通过语义验证。
4. Unicode扩展字符、跨片段引用、字幕时间戳定位正确。
5. 空白输入、无合法全文、模型超时、JSON截断有明确错误，不能静默回退为成功。
6. 事件更新使旧结果可见但不过期冒用；重复任务有幂等控制。
7. 独立编码与裁决权限、版本、分母及冻结集不泄漏。
8. 迁移前后旧资源、正文、字幕数量和内容一致；旧路由仍可用。
9. 端到端用真实短事件检查：引文逐字可回溯、四个状态可编辑、JSON/CSV可复核。此为工程验收，不计为研究实证结果。

正式数据库操作前通过SQLite backup API创建时间戳备份、检查完整性；先在副本演练迁移。实施阶段再安排服务暂停与重启。禁止用CREATE_ALL替代版本迁移；回滚优先切回旧入口，保留新增研究结果，不直接downgrade删除数据。

## 12. 理论来源与材料

用户补充材料：/Users/acai/.codex/attachments/fb1ca62d-7c1f-4a90-8c1e-774f9c4416da/已粘贴的文本.txt

Bebeau, M. J., Rest, J. R., & Narvaez, D. (1999). Beyond the Promise: A Perspective on Research in Moral Education. Educational Researcher, 28(4), 18–26. https://doi.org/10.3102/0013189X028004018
Bebeau, M. J., & Thoma, S. J. (1999). “Intermediate” Concepts and the Connection to Moral Education. Educational Psychology Review, 11, 343–360. https://doi.org/10.1023/A:1022057316180
Narvaez, D., & Duckett, L. (2020). Ethics in Early Life Care and Lactation Practice. Journal of Human Lactation, 36(1), 9–16. https://doi.org/10.1177/0890334419888454

上述专业伦理应用可作为操作化参考，不代表其职业情境与教育家叙事相同。本项目代码本仍需试编码检验。


## 13. 2026-10-29范围修订 大数据挖掘与多模态研究主线

### 13.1 理论约束与开放发现结合

Rest四成分用于组织道德行动过程证据；情境、教育议题、冲突、行动策略、受影响者、约束及结果另行开放编码。四成分不是穷尽所有资料的标签体系。保留无法归类、理论之外和相反案例，避免只得到预设分类的重复。

拟采用两层分析：
1. 理论引导：对来源内事件的四成分线索进行证据编码。
2. 数据驱动：对事件语义表示、主题和行为关系进行挖掘，形成跨人物候选模式，再由研究者解释和核验。

“道德推敲”落实为可审查问题：谁的利益受到影响？有哪些竞争价值？材料记载了什么理由和选择？有哪些行动代价、历史约束与不同解释？哪些理由只是后人归因？不能把研究者提出的可能理由写成教育家当时的真实心理活动。

### 13.2 大规模语料挖掘的可检验价值

- 广度：发现单一人物或单一资料无法呈现的情境、行动策略与反例。
- 比较：分析同类教育问题在不同人物、时代及办学情境中的解决方式。
- 稳健性：通过增加来源、人物留出与不同抽样规模检验候选模式是否保持。
- 稀有证据：记录罕见但重要的价值冲突和行动受阻案例；不以出现频率代替教育价值。

数据量增益评估：在预先定义的分层抽样中逐步增加资料，重复抽样观察新增经核验事件类型、候选模式稳定性、人工复核成本与来源覆盖。样本规模、随机种子及停止规则记录在运行配置。当前资料规模仍作为种子库报告，不因片段数量多便认定已实现大数据创新。

### 13.3 多源与多模态分别设计

多源指传记、自述、书信、档案、报道、口述等来源；多模态指文本、图像、音频、视频等信息形式。视频字幕是语言转写，不能单独证明视觉或听觉信息带来增益。

每份媒体增加origin_type（同期原始记录、后期访谈、纪录片剪辑、重演、解说等）、记录时间、所述事件时间、原始出处及source_family。多次转载或共同引用同一本书不能算独立佐证。历史人物缺少原始影像时如实登记；后期解说不作为直接观察到其历史行为的证据。

模态证据分开保存：
- 文本/字幕：事件、明确理由、价值表达及原文位置。
- 图像/档案：可辨识文字与可见环境、行动信息；OCR校验后回到图像区域。
- 音频：明确言语、说话轮次及时间信息；说话者不确定时保留不确定性。
- 视频：可观察行动、互动、空间和顺序；保留片段范围与是否为重演。

不从表情、声调或音乐直接赋予道德动机。模态之间有差异时记录差异，不强行融合为确定结论。

多模态增益实验优先使用具有配对材料的同一事件：A仅文本/字幕；B文本加实际可用视听/图像证据。在相同事件和任务下比较新增有效证据、事实识别、冲突发现与错误率。另做同类文本多来源比较，以区分“来源增加”与“模态增加”。不能将不同人物、不同内容之间的差异全部归因于模态。

### 13.4 教育典范提取

候选典范结构：教育情境＋核心伦理问题＋价值权衡＋行动策略＋实施条件＋记载的结果＋适用边界＋支持/相反证据。

生成步骤：事件表示→语义召回/聚类→候选模式命名→原文复核→跨人物与来源分层检验→反例及边界分析→专家讨论→发布候选典范。

聚类结果首先称为候选模式；专家审查与资料支持后才作为典范案例。频繁模式不是必然应当效仿的规范；历史可行也不等于当代可直接迁移。支持数同时报告人物、来源家族、事件数量，避免长篇传记或重复报道主导结论。

### 13.5 在既有代码方案上增加的模块

- corpus_sampling_service.py：人物、时代、来源和模态覆盖、分层样本清单、样本规模增益。
- media_evidence_service.py：文本跨度、图像区域、音视频时间段及原始/重演类型的统一证据登记。
- cross_source_alignment_service.py：跨源候选事件关联、同源传播去重、人工确认与冲突保留。
- event_embedding_service.py：事件语义表示，记录模型、输入范围和向量版本；首次实施选一种可评测方法。
- narrative_mining_service.py：候选主题、行为组合及跨人物模式；记录参数、随机种子、抽样与失败状态。
- exemplar_service.py：候选典范、边界、支持证据、反例与专家意见。
- multimodal_evaluation_service.py：配对事件、模态缺失、文本基线及模态增益比较。

数据扩展：source_families、media_observations、event_alignments、event_embeddings、mining_runs、candidate_patterns、pattern_memberships、exemplar_reviews。与第7节事件/编码表关联，模型候选关联与人工确认关联分开。媒体证据必须含asset_id、来源快照、模态、观察内容、定位、审核状态和局限。

首页调整为：语料覆盖→跨人物事件分析→Rest证据→模式发现→典范库→研究评测。人物详情是一个筛选视角；总览不限定单个人物。

实施顺序仍从单事件技术闭环开始，但首轮批量试点必须覆盖多位教育家、若干情境和可获得的来源类型。单事件只是测试系统贯通，不是论文研究范围。待事件层可靠，再增设语义挖掘、跨源核验和配对多模态研究。

### 13.6 拟定题目与成果

工作题目：中国经典教育家的道德行动与育人典范——基于多源多模态资料的计算辅助研究。
若最终仅完成文本分析，标题相应调整为多源叙事，媒体资源建设在方法与展望中准确说明。

成果分为：可追溯研究语料、跨人物情境与行为模式、Rest过程证据分布、多源/多模态信息增益、经复核的典范案例及适用边界。上述是拟研究产出，尚无完成结果。
