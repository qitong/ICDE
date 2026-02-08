# ICDE Database Schema

## Overview

ICDE数据库采用关系型设计，支持SQLite（MVP）和PostgreSQL（生产环境）。

## ER Diagram (文本表示)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            USER & SESSION                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐         ┌──────────┐         ┌───────────────┐               │
│   │  users   │ 1 ─── * │ sessions │ 1 ─── * │ conversations │               │
│   └──────────┘         └──────────┘         └───────────────┘               │
│                              │                     │                         │
│                              │                     │                         │
│                              ▼                     ▼                         │
│                        ┌──────────┐         ┌──────────┐                    │
│                        │ exports  │         │ messages │                    │
│                        └──────────┘         └──────────┘                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLINICAL DATA                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐         ┌──────────┐         ┌─────────────────┐             │
│   │ datasets │ 1 ─── * │ patients │ 1 ─── * │ patient_events  │             │
│   └──────────┘         └──────────┘         └─────────────────┘             │
│        │                    │                                                │
│        │                    │                                                │
│        ▼                    ▼                                                │
│   ┌────────────────┐  ┌───────────────────┐                                 │
│   │dataset_variables│  │patient_embeddings │                                 │
│   └────────────────┘  └───────────────────┘                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            COHORT & ANALYSIS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐         ┌─────────────────┐         ┌────────────────┐       │
│   │ cohorts  │ 1 ─── * │ cohort_criteria │         │ cohort_patients│       │
│   └──────────┘         └─────────────────┘         └────────────────┘       │
│        │                                                  ▲                  │
│        │                                                  │                  │
│        └──────────────────────────────────────────────────┘                  │
│        │                                                                     │
│        ▼                                                                     │
│   ┌───────────────┐         ┌──────────────────────┐         ┌─────────┐    │
│   │ analysis_jobs │ 1 ─── * │ model_recommendations│         │ outputs │    │
│   └───────────────┘         └──────────────────────┘         └─────────┘    │
│                                                                    ▲         │
│                                                                    │         │
│                                    ────────────────────────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Table Categories

### 1. User & Session (用户与会话)

| Table | Description |
|-------|-------------|
| `users` | 用户账户（MVP预留，暂不实现登录） |
| `sessions` | 浏览器会话，匿名用户支持 |

### 2. Dataset Management (数据集管理)

| Table | Description |
|-------|-------------|
| `datasets` | 数据源/数据集（如"肺癌示例数据集"） |
| `dataset_variables` | 数据集变量定义（字段元数据） |

### 3. Patient Data (患者数据)

| Table | Description |
|-------|-------------|
| `patients` | 患者基线信息 |
| `patient_events` | 患者事件时间线（Problem List核心） |

**事件类型 (event_type):**
- `DIAGNOSIS` - 诊断（初诊/复发）
- `MOLECULAR` - 分子检测（基因/表达）
- `TREATMENT_START` - 开始治疗
- `TREATMENT_END` - 结束治疗
- `RESPONSE` - 疗效评估 (CR/PR/SD/PD)
- `PROGRESSION` - 疾病进展
- `ADVERSE_EVENT` - 不良事件
- `SURGERY` - 手术
- `RADIOTHERAPY` - 放疗
- `DEATH` - 死亡
- `LAB_TEST` - 实验室检查
- `IMAGING` - 影像检查
- `OTHER` - 其他

### 4. Cohort Management (队列管理)

| Table | Description |
|-------|-------------|
| `cohorts` | 分析集/队列定义 |
| `cohort_criteria` | 入排标准（inclusion/exclusion） |
| `cohort_patients` | 队列-患者关联（多对多） |

### 5. Conversation (对话管理)

| Table | Description |
|-------|-------------|
| `conversations` | 对话会话 |
| `messages` | 对话消息（user/assistant/system） |

**对话阶段 (stage):**
- `init` - 初始化
- `filtering` - 语义筛选中
- `analysis` - 分析执行中
- `output` - 输出生成中

### 6. Analysis (分析执行)

| Table | Description |
|-------|-------------|
| `analysis_jobs` | 分析任务 |
| `model_recommendations` | 模型推荐记录 |

**分析类型 (analysis_type):**
- `survival` - 生存分析
- `regression` - 回归分析
- `descriptive` - 描述性统计
- `comparison` - 组间比较

**统计方法 (method):**
- `km` - Kaplan-Meier
- `cox` - Cox回归
- `logistic` - Logistic回归
- `linear` - 线性回归
- `ttest` - T检验
- `chi2` - 卡方检验
- `wilcoxon` - Wilcoxon检验

### 7. Output (输出管理)

| Table | Description |
|-------|-------------|
| `outputs` | 输出产物（表格/图表/文字） |
| `exports` | 导出记录（Word/PDF） |

**输出类型 (output_type):**
- `table` - 统计表格
- `chart` - 图表
- `text` - 论文文字
- `document` - 完整文档

**图表子类型 (output_subtype):**
- `km_plot` - KM生存曲线
- `forest_plot` - 森林图
- `waterfall_plot` - 瀑布图
- `sankey_diagram` - 桑基图
- `baseline_table` - 基线特征表
- `ae_table` - 不良事件表

### 8. Vector Embeddings (语义搜索)

| Table | Description |
|-------|-------------|
| `patient_embeddings` | 患者文本向量化 |
| `query_embeddings` | 查询向量缓存 |

### 9. System & Audit (系统与审计)

| Table | Description |
|-------|-------------|
| `system_config` | 系统配置 |
| `audit_logs` | 操作审计日志 |
| `llm_calls` | LLM调用记录 |
| `schema_version` | 数据库版本管理 |

## Key Relationships

```
users ─1:N─> sessions ─1:N─> conversations ─1:N─> messages
                │
                └─1:N─> exports

datasets ─1:N─> dataset_variables
    │
    └─1:N─> patients ─1:N─> patient_events
                │
                └─1:N─> patient_embeddings

datasets ─1:N─> cohorts ─1:N─> cohort_criteria
                   │
                   └─N:M─> patients (via cohort_patients)
                   │
                   └─1:N─> analysis_jobs ─1:N─> model_recommendations
                                │
                                └─1:N─> outputs
```

## Data Flow

```
1. 数据加载
   Raw Data (SAS/CSV) → datasets → patients → patient_events

2. 语义预处理
   patient_events → LLM提取 → summary_text → Embedding → patient_embeddings

3. 用户查询
   User Input → query_embeddings → 相似度召回 → LLM精筛 → cohorts

4. 分析执行
   cohorts → analysis_jobs → Python执行 → outputs

5. 结果导出
   outputs → exports → Word/PDF
```

## Usage

### Initialize Database (SQLite)

```bash
sqlite3 icde.db < schema.sql
```

### Initialize Database (PostgreSQL)

```bash
psql -d icde -f schema.sql
```

## Migration Notes

- 使用 `TEXT` 代替 `VARCHAR` 以兼容SQLite
- 使用 `INTEGER` 代替 `BOOLEAN` (0/1)
- 使用 `REAL` 代替 `FLOAT`
- 使用 `BLOB` 存储向量数据
- JSON字段存储为 `TEXT`，应用层解析
