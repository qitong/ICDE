-- ============================================================================
-- ICDE Database Schema
-- Integrated Clinical-Data Environment
-- Version: 1.0
-- Compatible with: SQLite / PostgreSQL
-- ============================================================================

-- ============================================================================
-- 1. USER & SESSION MANAGEMENT (预留用户系统)
-- ============================================================================

-- 用户表 (MVP阶段预留，暂不实现登录)
CREATE TABLE users (
    id              TEXT PRIMARY KEY,                    -- UUID
    email           TEXT UNIQUE,                         -- 邮箱（可选）
    name            TEXT,                                -- 显示名称
    avatar_url      TEXT,                                -- 头像URL
    role            TEXT DEFAULT 'user',                 -- 角色: user, admin
    preferences     TEXT,                                -- JSON: 用户偏好设置
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会话表 (基于浏览器Session)
CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,                    -- Session ID (UUID)
    user_id         TEXT REFERENCES users(id),           -- 关联用户（可为空，匿名用户）
    device_info     TEXT,                                -- JSON: 设备/浏览器信息
    ip_address      TEXT,                                -- IP地址
    is_active       INTEGER DEFAULT 1,                   -- 是否活跃
    last_activity   TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 最后活动时间
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at      TIMESTAMP                            -- 过期时间
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_is_active ON sessions(is_active);


-- ============================================================================
-- 2. DATASET MANAGEMENT (数据集管理)
-- ============================================================================

-- 数据源/数据集表
CREATE TABLE datasets (
    id              TEXT PRIMARY KEY,                    -- UUID
    name            TEXT NOT NULL,                       -- 数据集名称，如"肺癌示例数据集"
    description     TEXT,                                -- 描述
    domain          TEXT,                                -- 领域：lung_cancer, breast_cancer等
    source_type     TEXT NOT NULL,                       -- 来源类型: sas, csv, simulated
    file_path       TEXT,                                -- 原始文件路径（如有）
    schema_info     TEXT,                                -- JSON: 数据结构信息
    patient_count   INTEGER DEFAULT 0,                   -- 患者数量
    event_count     INTEGER DEFAULT 0,                   -- 事件数量
    status          TEXT DEFAULT 'active',               -- 状态: active, archived, processing
    metadata        TEXT,                                -- JSON: 其他元数据
    created_by      TEXT REFERENCES users(id),           -- 创建者
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_datasets_domain ON datasets(domain);
CREATE INDEX idx_datasets_status ON datasets(status);

-- 数据集变量/字段表
CREATE TABLE dataset_variables (
    id              TEXT PRIMARY KEY,
    dataset_id      TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,                       -- 变量名，如age, gender
    label           TEXT,                                -- 中文标签，如"年龄"
    data_type       TEXT NOT NULL,                       -- 类型: numeric, categorical, date, text
    category        TEXT,                                -- 分类: baseline, event, outcome
    unit            TEXT,                                -- 单位，如"岁"、"mg"
    value_range     TEXT,                                -- JSON: 取值范围或类别列表
    description     TEXT,                                -- 详细描述
    is_required     INTEGER DEFAULT 0,                   -- 是否必填
    display_order   INTEGER DEFAULT 0,                   -- 显示顺序
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dataset_variables_dataset_id ON dataset_variables(dataset_id);
CREATE INDEX idx_dataset_variables_category ON dataset_variables(category);


-- ============================================================================
-- 3. PATIENT DATA (患者数据 - Problem List结构)
-- ============================================================================

-- 患者基线表
CREATE TABLE patients (
    id              TEXT PRIMARY KEY,                    -- 患者ID (如P001)
    dataset_id      TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    external_id     TEXT,                                -- 原始数据中的ID

    -- 基线特征 (常用字段直接存储，便于查询)
    age             REAL,                                -- 年龄
    gender          TEXT,                                -- 性别: M, F
    smoking_status  TEXT,                                -- 吸烟状态
    smoking_pack_years REAL,                             -- 吸烟包年
    ps_score        INTEGER,                             -- ECOG PS评分
    diagnosis_date  DATE,                                -- 首次诊断日期

    -- 扩展基线数据 (JSON存储其他基线变量)
    baseline_data   TEXT,                                -- JSON: 其他基线特征

    -- 汇总信息 (预计算，加速查询)
    event_count     INTEGER DEFAULT 0,                   -- 事件数量
    treatment_lines INTEGER DEFAULT 0,                   -- 治疗线数
    follow_up_days  INTEGER,                             -- 随访天数
    is_deceased     INTEGER DEFAULT 0,                   -- 是否死亡
    death_date      DATE,                                -- 死亡日期

    -- 语义搜索用
    summary_text    TEXT,                                -- 患者事件摘要文本

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_patients_dataset_id ON patients(dataset_id);
CREATE INDEX idx_patients_gender ON patients(gender);
CREATE INDEX idx_patients_age ON patients(age);
CREATE INDEX idx_patients_ps_score ON patients(ps_score);

-- 患者事件表 (Problem List核心)
CREATE TABLE patient_events (
    id              TEXT PRIMARY KEY,
    patient_id      TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    dataset_id      TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,

    -- 事件基本信息
    event_date      DATE NOT NULL,                       -- 事件日期
    event_type      TEXT NOT NULL,                       -- 事件类型 (见下方枚举)
    event_detail    TEXT,                                -- 事件详情描述

    -- 结构化事件数据 (根据event_type不同而不同)
    structured_data TEXT,                                -- JSON: 结构化事件数据

    -- 治疗相关
    treatment_line  INTEGER,                             -- 治疗线数（仅TREATMENT_START）
    treatment_name  TEXT,                                -- 治疗方案名称

    -- 不良事件相关
    ae_grade        INTEGER,                             -- 不良事件等级（1-5）
    ae_serious      INTEGER DEFAULT 0,                   -- 是否严重不良事件

    -- 疗效评估相关
    response_type   TEXT,                                -- 疗效: CR, PR, SD, PD

    -- 进展相关
    progression_site TEXT,                               -- 进展部位

    -- 排序和关联
    sequence_num    INTEGER DEFAULT 0,                   -- 同日事件排序
    parent_event_id TEXT REFERENCES patient_events(id),  -- 关联的父事件

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 事件类型枚举说明:
-- DIAGNOSIS      - 诊断（初诊/复发）
-- MOLECULAR      - 分子检测（基因/表达）
-- TREATMENT_START - 开始治疗
-- TREATMENT_END  - 结束治疗
-- RESPONSE       - 疗效评估
-- PROGRESSION    - 疾病进展
-- ADVERSE_EVENT  - 不良事件
-- SURGERY        - 手术
-- RADIOTHERAPY   - 放疗
-- DEATH          - 死亡
-- LAB_TEST       - 实验室检查
-- IMAGING        - 影像检查
-- OTHER          - 其他

CREATE INDEX idx_patient_events_patient_id ON patient_events(patient_id);
CREATE INDEX idx_patient_events_dataset_id ON patient_events(dataset_id);
CREATE INDEX idx_patient_events_event_type ON patient_events(event_type);
CREATE INDEX idx_patient_events_event_date ON patient_events(event_date);
CREATE INDEX idx_patient_events_treatment_line ON patient_events(treatment_line);


-- ============================================================================
-- 4. COHORT MANAGEMENT (分析集/队列管理)
-- ============================================================================

-- 分析集/队列表
CREATE TABLE cohorts (
    id              TEXT PRIMARY KEY,
    session_id      TEXT REFERENCES sessions(id),        -- 所属会话
    dataset_id      TEXT NOT NULL REFERENCES datasets(id),
    name            TEXT NOT NULL,                       -- 队列名称
    description     TEXT,                                -- 描述

    -- 自然语言定义
    nl_definition   TEXT,                                -- 用户的自然语言描述

    -- 队列统计
    patient_count   INTEGER DEFAULT 0,                   -- 入选患者数
    excluded_count  INTEGER DEFAULT 0,                   -- 排除患者数

    -- 状态
    status          TEXT DEFAULT 'draft',                -- draft, confirmed, archived
    version         INTEGER DEFAULT 1,                   -- 版本号（支持迭代调整）
    parent_id       TEXT REFERENCES cohorts(id),         -- 父版本（如有调整）

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cohorts_session_id ON cohorts(session_id);
CREATE INDEX idx_cohorts_dataset_id ON cohorts(dataset_id);
CREATE INDEX idx_cohorts_status ON cohorts(status);

-- 入排标准表
CREATE TABLE cohort_criteria (
    id              TEXT PRIMARY KEY,
    cohort_id       TEXT NOT NULL REFERENCES cohorts(id) ON DELETE CASCADE,

    criteria_type   TEXT NOT NULL,                       -- inclusion, exclusion
    category        TEXT,                                -- 分类: baseline, treatment, outcome等
    description     TEXT NOT NULL,                       -- 标准描述

    -- 结构化条件 (可选，用于程序化筛选)
    field_name      TEXT,                                -- 字段名
    operator        TEXT,                                -- 操作符: eq, ne, gt, lt, gte, lte, contains, in
    field_value     TEXT,                                -- 值（JSON格式支持多值）

    -- LLM生成的逻辑表达式
    logic_expression TEXT,                               -- 逻辑表达式

    -- 统计
    affected_count  INTEGER DEFAULT 0,                   -- 受影响患者数

    display_order   INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cohort_criteria_cohort_id ON cohort_criteria(cohort_id);
CREATE INDEX idx_cohort_criteria_type ON cohort_criteria(criteria_type);

-- 队列-患者关联表
CREATE TABLE cohort_patients (
    id              TEXT PRIMARY KEY,
    cohort_id       TEXT NOT NULL REFERENCES cohorts(id) ON DELETE CASCADE,
    patient_id      TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,

    is_included     INTEGER DEFAULT 1,                   -- 是否入选
    exclusion_reason TEXT,                               -- 排除原因（如被排除）
    exclusion_criteria_id TEXT REFERENCES cohort_criteria(id),

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(cohort_id, patient_id)
);

CREATE INDEX idx_cohort_patients_cohort_id ON cohort_patients(cohort_id);
CREATE INDEX idx_cohort_patients_patient_id ON cohort_patients(patient_id);
CREATE INDEX idx_cohort_patients_is_included ON cohort_patients(is_included);


-- ============================================================================
-- 5. CONVERSATION & MESSAGES (对话管理)
-- ============================================================================

-- 对话表
CREATE TABLE conversations (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    dataset_id      TEXT REFERENCES datasets(id),        -- 当前使用的数据集
    cohort_id       TEXT REFERENCES cohorts(id),         -- 当前分析集

    title           TEXT,                                -- 对话标题（自动生成或用户设置）

    -- 对话状态
    stage           TEXT DEFAULT 'init',                 -- init, filtering, analysis, output
    status          TEXT DEFAULT 'active',               -- active, completed, archived

    -- 上下文摘要（用于LLM）
    context_summary TEXT,                                -- JSON: 当前状态摘要

    message_count   INTEGER DEFAULT 0,

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_status ON conversations(status);

-- 消息表
CREATE TABLE messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,

    role            TEXT NOT NULL,                       -- user, assistant, system
    content         TEXT NOT NULL,                       -- 消息内容

    -- 结构化内容（assistant消息）
    structured_content TEXT,                             -- JSON: 结构化响应

    -- 意图识别结果
    intent          TEXT,                                -- 识别的意图类型
    intent_params   TEXT,                                -- JSON: 意图参数

    -- 关联的操作
    cohort_update_id TEXT REFERENCES cohorts(id),        -- 产生的队列更新
    analysis_job_id TEXT,                                -- 触发的分析任务

    -- Token统计（用于成本监控）
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0,

    -- 用户反馈
    feedback_rating INTEGER,                             -- 1-5评分
    feedback_text   TEXT,                                -- 反馈文字

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_role ON messages(role);
CREATE INDEX idx_messages_created_at ON messages(created_at);


-- ============================================================================
-- 6. ANALYSIS & CODE EXECUTION (分析执行)
-- ============================================================================

-- 分析任务表
CREATE TABLE analysis_jobs (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id),
    cohort_id       TEXT REFERENCES cohorts(id),

    -- 分析类型和方法
    analysis_type   TEXT NOT NULL,                       -- survival, regression, descriptive, comparison
    method          TEXT NOT NULL,                       -- km, cox, logistic, ttest, chi2, etc.
    method_params   TEXT,                                -- JSON: 方法参数

    -- 变量选择
    outcome_var     TEXT,                                -- 结局变量
    exposure_var    TEXT,                                -- 暴露/分组变量
    covariates      TEXT,                                -- JSON: 协变量列表

    -- 代码和执行
    generated_code  TEXT,                                -- 生成的Python代码
    code_version    INTEGER DEFAULT 1,                   -- 代码版本

    -- 执行状态
    status          TEXT DEFAULT 'pending',              -- pending, running, completed, failed
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    error_message   TEXT,                                -- 错误信息（如失败）

    -- 结果
    result_summary  TEXT,                                -- JSON: 结果摘要
    result_data     TEXT,                                -- JSON: 完整结果数据

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_analysis_jobs_conversation_id ON analysis_jobs(conversation_id);
CREATE INDEX idx_analysis_jobs_cohort_id ON analysis_jobs(cohort_id);
CREATE INDEX idx_analysis_jobs_status ON analysis_jobs(status);

-- 模型推荐记录表
CREATE TABLE model_recommendations (
    id              TEXT PRIMARY KEY,
    analysis_job_id TEXT REFERENCES analysis_jobs(id) ON DELETE CASCADE,

    rank            INTEGER NOT NULL,                    -- 推荐排序（1=首选）
    method          TEXT NOT NULL,                       -- 推荐的方法
    reason          TEXT,                                -- 推荐理由
    pros            TEXT,                                -- JSON: 优点列表
    cons            TEXT,                                -- JSON: 缺点列表
    is_selected     INTEGER DEFAULT 0,                   -- 用户是否选择

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_recommendations_job_id ON model_recommendations(analysis_job_id);


-- ============================================================================
-- 7. OUTPUT MANAGEMENT (输出管理)
-- ============================================================================

-- 输出产物表
CREATE TABLE outputs (
    id              TEXT PRIMARY KEY,
    analysis_job_id TEXT REFERENCES analysis_jobs(id),
    conversation_id TEXT REFERENCES conversations(id),
    cohort_id       TEXT REFERENCES cohorts(id),

    -- 输出类型
    output_type     TEXT NOT NULL,                       -- table, chart, text, document
    output_subtype  TEXT,                                -- km_plot, forest_plot, baseline_table, etc.

    -- 内容
    title           TEXT,                                -- 标题
    content         TEXT,                                -- 内容（文本或JSON配置）

    -- 文件信息
    file_path       TEXT,                                -- 文件路径（如有）
    file_format     TEXT,                                -- png, svg, docx, pdf, html
    file_size       INTEGER,                             -- 文件大小(bytes)

    -- 图表配置（可编辑）
    chart_config    TEXT,                                -- JSON: 图表配置

    -- 表格数据
    table_data      TEXT,                                -- JSON: 表格数据
    table_format    TEXT,                                -- JSON: 表格格式配置

    -- 论文文字
    narrative_text  TEXT,                                -- 生成的论文文字
    narrative_section TEXT,                              -- methods, results, discussion

    -- 版本和状态
    version         INTEGER DEFAULT 1,
    is_final        INTEGER DEFAULT 0,                   -- 是否为最终版本

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_outputs_analysis_job_id ON outputs(analysis_job_id);
CREATE INDEX idx_outputs_conversation_id ON outputs(conversation_id);
CREATE INDEX idx_outputs_output_type ON outputs(output_type);

-- 导出记录表
CREATE TABLE exports (
    id              TEXT PRIMARY KEY,
    session_id      TEXT REFERENCES sessions(id),

    -- 导出配置
    format          TEXT NOT NULL,                       -- word, pdf
    template        TEXT,                                -- 使用的模板

    -- 包含的内容
    included_outputs TEXT,                               -- JSON: 包含的output IDs

    -- 文件信息
    file_path       TEXT,
    file_name       TEXT,
    file_size       INTEGER,

    -- 状态
    status          TEXT DEFAULT 'pending',              -- pending, processing, completed, failed
    error_message   TEXT,

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP
);

CREATE INDEX idx_exports_session_id ON exports(session_id);
CREATE INDEX idx_exports_status ON exports(status);


-- ============================================================================
-- 8. VECTOR EMBEDDINGS (语义搜索)
-- ============================================================================

-- 患者Embedding表
CREATE TABLE patient_embeddings (
    id              TEXT PRIMARY KEY,
    patient_id      TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    dataset_id      TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,

    -- Embedding信息
    model_name      TEXT NOT NULL,                       -- 模型名称: bge-m3, zhipu-embedding
    model_version   TEXT,                                -- 模型版本

    -- 文本来源
    source_text     TEXT,                                -- 生成embedding的原文
    text_type       TEXT DEFAULT 'summary',              -- summary, events, full

    -- Embedding向量（存储为二进制或Base64）
    embedding       BLOB,                                -- 向量数据
    embedding_dim   INTEGER,                             -- 向量维度

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(patient_id, model_name, text_type)
);

CREATE INDEX idx_patient_embeddings_patient_id ON patient_embeddings(patient_id);
CREATE INDEX idx_patient_embeddings_dataset_id ON patient_embeddings(dataset_id);
CREATE INDEX idx_patient_embeddings_model ON patient_embeddings(model_name);

-- 查询Embedding缓存表
CREATE TABLE query_embeddings (
    id              TEXT PRIMARY KEY,

    query_text      TEXT NOT NULL,                       -- 原始查询文本
    query_hash      TEXT NOT NULL,                       -- 查询文本的hash（用于快速查找）

    model_name      TEXT NOT NULL,
    embedding       BLOB,
    embedding_dim   INTEGER,

    hit_count       INTEGER DEFAULT 1,                   -- 命中次数
    last_used_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(query_hash, model_name)
);

CREATE INDEX idx_query_embeddings_hash ON query_embeddings(query_hash);


-- ============================================================================
-- 9. SYSTEM & AUDIT (系统和审计)
-- ============================================================================

-- 系统配置表
CREATE TABLE system_config (
    key             TEXT PRIMARY KEY,
    value           TEXT,
    value_type      TEXT DEFAULT 'string',               -- string, number, boolean, json
    description     TEXT,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 操作审计日志表
CREATE TABLE audit_logs (
    id              TEXT PRIMARY KEY,
    session_id      TEXT,
    user_id         TEXT,

    action          TEXT NOT NULL,                       -- 操作类型
    resource_type   TEXT,                                -- 资源类型: dataset, cohort, analysis
    resource_id     TEXT,                                -- 资源ID

    details         TEXT,                                -- JSON: 操作详情
    ip_address      TEXT,

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_session_id ON audit_logs(session_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- LLM调用记录表（用于成本和调试）
CREATE TABLE llm_calls (
    id              TEXT PRIMARY KEY,
    message_id      TEXT REFERENCES messages(id),

    provider        TEXT NOT NULL,                       -- deepseek, qwen, zhipu
    model           TEXT NOT NULL,                       -- 具体模型名

    -- 请求信息
    prompt_template TEXT,                                -- 使用的prompt模板
    system_prompt   TEXT,                                -- System prompt
    user_prompt     TEXT,                                -- User prompt

    -- 响应信息
    response        TEXT,                                -- 完整响应

    -- Token和成本
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    total_cost      REAL,                                -- 成本（元）

    -- 性能
    latency_ms      INTEGER,                             -- 响应时间（毫秒）

    -- 状态
    status          TEXT DEFAULT 'success',              -- success, error, timeout
    error_message   TEXT,

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_llm_calls_message_id ON llm_calls(message_id);
CREATE INDEX idx_llm_calls_provider ON llm_calls(provider);
CREATE INDEX idx_llm_calls_created_at ON llm_calls(created_at);


-- ============================================================================
-- 10. INITIAL DATA (初始数据)
-- ============================================================================

-- 插入默认系统配置
INSERT INTO system_config (key, value, value_type, description) VALUES
('llm_provider', 'deepseek', 'string', '默认LLM提供商'),
('llm_model', 'deepseek-chat', 'string', '默认LLM模型'),
('embedding_provider', 'bge-m3', 'string', '默认Embedding模型'),
('max_cohort_size', '10000', 'number', '最大队列大小'),
('session_timeout_hours', '24', 'number', '会话超时时间(小时)'),
('enable_audit_log', 'true', 'boolean', '是否启用审计日志');


-- ============================================================================
-- SCHEMA VERSION
-- ============================================================================

CREATE TABLE schema_version (
    version         INTEGER PRIMARY KEY,
    applied_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description     TEXT
);

INSERT INTO schema_version (version, description) VALUES (1, 'Initial schema');
