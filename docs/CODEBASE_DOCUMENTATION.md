# ICDE 代码库文档

> 版本：v0.1.0 (MVP Phase 1)
> 更新日期：2026-02-08

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [目录结构](#3-目录结构)
4. [后端模块详解](#4-后端模块详解)
5. [前端模块详解](#5-前端模块详解)
6. [API 接口文档](#6-api-接口文档)
7. [数据流图](#7-数据流图)
8. [功能对照表](#8-功能对照表)
9. [运行指南](#9-运行指南)
10. [待开发功能](#10-待开发功能)

---

## 1. 项目概述

ICDE (Integrated Clinical-Data Environment) 是一个临床数据分析IDE，旨在让临床医生/PI通过自然语言完成数据分析，输出可发表的图表和论文草稿。

### 1.1 当前实现状态

| 产品模块 | 实现状态 | 说明 |
|---------|---------|------|
| 三栏IDE布局 | ✅ 已完成 | 左栏文件导航、中栏工作区、右栏对话 |
| 数据集上传 | ✅ 已完成 | 支持CSV/Excel，自动解析列类型 |
| 文件导航 | ✅ 已完成 | 显示上传的数据集和文件列表 |
| 对话界面 | ✅ 已完成 | 基础聊天UI，模拟响应 |
| 语义筛选 | ❌ 待开发 | M2里程碑内容 |
| 统计分析 | ❌ 待开发 | M3里程碑内容 |
| 输出生成 | ❌ 待开发 | M4里程碑内容 |

---

## 2. 技术栈

### 2.1 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 主语言 |
| FastAPI | ≥0.109.0 | Web框架 |
| SQLAlchemy | ≥2.0.0 | ORM |
| SQLite | - | 数据库 |
| Pandas | ≥2.0.0 | 数据处理 |
| Pydantic | ≥2.0.0 | 数据验证 |

### 2.2 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19.2.0 | UI框架 |
| TypeScript | 5.9.3 | 类型安全 |
| Tailwind CSS | 4.1.18 | 样式 |
| Vite | 7.2.4 | 构建工具 |
| Lucide React | 0.563.0 | 图标库 |

---

## 3. 目录结构

```
PIS/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI入口
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库连接
│   │   ├── models/            # SQLAlchemy模型
│   │   │   ├── base.py
│   │   │   └── dataset.py
│   │   ├── schemas/           # Pydantic模型
│   │   │   └── dataset.py
│   │   ├── routers/           # API路由
│   │   │   └── datasets.py
│   │   └── services/          # 业务逻辑
│   │       └── file_parser.py
│   ├── uploads/               # 文件存储目录
│   ├── requirements.txt
│   └── run.py                 # 启动脚本
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── App.tsx            # 应用入口
│   │   ├── main.tsx           # React挂载点
│   │   ├── index.css          # 全局样式
│   │   ├── types/             # TypeScript类型
│   │   │   └── index.ts
│   │   ├── contexts/          # React Context
│   │   │   └── AppContext.tsx
│   │   ├── services/          # API客户端
│   │   │   └── api.ts
│   │   └── components/
│   │       ├── layout/        # 布局组件
│   │       ├── sidebar/       # 侧边栏组件
│   │       ├── workspace/     # 工作区组件
│   │       ├── chat/          # 对话组件
│   │       ├── upload/        # 上传组件
│   │       └── ui/            # 通用UI组件
│   └── package.json
│
└── docs/                       # 文档
    └── plans/
        └── 2026-02-06-icde-mvp-design.md
```

---

## 4. 后端模块详解

### 4.1 config.py - 配置管理

**路径**: `backend/app/config.py`

**功能**: 集中管理所有配置项

```python
# 关键配置项
BASE_DIR          # 项目根目录
DATABASE_URL      # 数据库连接URL (默认: sqlite:///icde.db)
UPLOAD_DIR        # 文件上传目录 (默认: backend/uploads/)
ALLOWED_EXTENSIONS # 允许的文件类型: {".csv", ".xlsx", ".xls"}
MAX_FILE_SIZE     # 最大文件大小: 50MB
PREVIEW_ROWS      # 预览行数: 10
MAX_SAMPLE_VALUES # 样本值数量: 5
```

---

### 4.2 database.py - 数据库连接

**路径**: `backend/app/database.py`

**功能**: SQLAlchemy数据库会话管理

| 函数/对象 | 用途 |
|----------|------|
| `engine` | SQLAlchemy引擎实例 |
| `SessionLocal` | 会话工厂 |
| `get_db()` | FastAPI依赖注入，提供数据库会话 |
| `init_db()` | 初始化数据库表结构 |

---

### 4.3 models/dataset.py - 数据模型

**路径**: `backend/app/models/dataset.py`

#### Dataset 模型（数据集）

| 字段 | 类型 | 说明 |
|-----|------|------|
| `id` | String(36) | 主键，UUID |
| `name` | String(255) | 数据集名称 |
| `description` | Text | 描述（可选） |
| `folder_path` | String(512) | 文件夹路径 |
| `file_count` | Integer | 文件数量 |
| `total_size` | Integer | 总大小（字节） |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |
| `files` | Relationship | 关联的DatasetFile列表 |

#### DatasetFile 模型（数据集文件）

| 字段 | 类型 | 说明 |
|-----|------|------|
| `id` | String(36) | 主键，UUID |
| `dataset_id` | String(36) | 外键，关联Dataset |
| `file_name` | String(255) | 存储文件名 |
| `original_name` | String(255) | 原始文件名 |
| `file_path` | String(512) | 文件完整路径 |
| `file_type` | String(10) | 文件类型：csv/xlsx/xls |
| `file_size` | Integer | 文件大小（字节） |
| `row_count` | Integer | 行数 |
| `column_count` | Integer | 列数 |
| `column_info` | Text | 列元数据（JSON） |
| `parse_status` | String(20) | 解析状态：pending/parsed/error |
| `parse_error` | Text | 解析错误信息 |
| `created_at` | DateTime | 创建时间 |

---

### 4.4 schemas/dataset.py - Pydantic模型

**路径**: `backend/app/schemas/dataset.py`

**用途**: API请求/响应的数据验证

| Schema | 用途 | 关键字段 |
|--------|------|----------|
| `DatasetCreate` | 创建数据集请求 | name, description |
| `ColumnInfo` | 列元数据 | name, data_type, non_null_count, unique_count, sample_values |
| `DatasetFileResponse` | 文件响应 | id, original_name, file_type, row_count, parse_status |
| `DatasetResponse` | 数据集响应（含文件） | id, name, file_count, files[] |
| `DatasetListResponse` | 数据集列表项 | id, name, file_count (不含文件详情) |
| `FilePreview` | 文件预览 | columns[], sample_rows[] |

---

### 4.5 services/file_parser.py - 文件解析服务

**路径**: `backend/app/services/file_parser.py`

**功能**: 解析Excel/CSV文件，提取元数据

#### FileParser 类

| 方法 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `read_file(file_path)` | Path | DataFrame | 读取CSV/Excel文件 |
| `infer_data_type(series)` | pd.Series | str | 推断数据类型 |
| `get_sample_values(series)` | pd.Series | List[str] | 获取样本值 |
| `parse_file(file_path)` | Path | Tuple | 返回(row_count, column_count, columns, json) |
| `get_preview(file_path, ...)` | Path, str, str | dict | 获取完整预览（含样本行） |

#### 数据类型推断规则

| 类型 | 判断条件 |
|------|----------|
| `numeric` | pandas数值类型 |
| `date` | datetime类型或可解析为日期 |
| `categorical` | 唯一值占比<10%且唯一值<50个 |
| `text` | 其他情况 |

---

### 4.6 routers/datasets.py - API路由

**路径**: `backend/app/routers/datasets.py`

**前缀**: `/api/datasets`

详见 [6. API接口文档](#6-api-接口文档)

---

### 4.7 main.py - FastAPI应用入口

**路径**: `backend/app/main.py`

**功能**:
- 创建FastAPI应用实例
- 配置CORS中间件（允许前端 localhost:5173 访问）
- 注册路由
- 应用启动时初始化数据库

---

## 5. 前端模块详解

### 5.1 types/index.ts - 类型定义

**路径**: `frontend/src/types/index.ts`

#### 核心类型

```typescript
// 数据集
interface Dataset {
  id: string;
  name: string;
  description: string | null;
  file_count: number;
  total_size: number;
  files?: DatasetFile[];
  created_at: string;
  updated_at: string;
}

// 数据集文件
interface DatasetFile {
  id: string;
  original_name: string;
  file_type: string;
  file_size: number;
  row_count: number | null;
  column_count: number | null;
  parse_status: 'pending' | 'parsed' | 'error';
}

// 列信息
interface ColumnInfo {
  name: string;
  data_type: 'numeric' | 'categorical' | 'date' | 'text';
  non_null_count: number;
  unique_count: number;
  sample_values: string[];
}

// 文件预览
interface FilePreview {
  file_id: string;
  file_name: string;
  row_count: number;
  column_count: number;
  columns: ColumnInfo[];
  sample_rows: Record<string, unknown>[];
}

// 应用状态
interface AppState {
  selectedFileId: string | null;
  expandedFolders: Set<string>;
  files: FileNode[];
  sidebarCollapsed: boolean;
  activeTab: TabType;
  canvasContent: CanvasContent | null;
  messages: Message[];
  isProcessing: boolean;
  analysisStatus: AnalysisStatus;
  currentDataSource: string;
  uploadModalOpen: boolean;
  datasets: Dataset[];
}
```

---

### 5.2 services/api.ts - API客户端

**路径**: `frontend/src/services/api.ts`

**功能**: 封装与后端的HTTP通信

| 方法 | HTTP | 端点 | 说明 |
|------|------|------|------|
| `createDataset(name, description?)` | POST | `/api/datasets` | 创建数据集 |
| `listDatasets()` | GET | `/api/datasets` | 获取所有数据集 |
| `getDataset(id)` | GET | `/api/datasets/{id}` | 获取单个数据集 |
| `deleteDataset(id)` | DELETE | `/api/datasets/{id}` | 删除数据集 |
| `uploadFiles(datasetId, files)` | POST | `/api/datasets/{id}/files` | 上传文件 |
| `getFilePreview(datasetId, fileId)` | GET | `/api/datasets/{id}/files/{fileId}/preview` | 获取文件预览 |

---

### 5.3 contexts/AppContext.tsx - 状态管理

**路径**: `frontend/src/contexts/AppContext.tsx`

**功能**: 全局状态管理（React Context + useReducer）

#### 提供的函数

| 函数 | 用途 |
|------|------|
| `selectFile(id)` | 选中文件 |
| `toggleFolder(id)` | 展开/折叠文件夹 |
| `toggleSidebar()` | 展开/折叠侧边栏 |
| `setActiveTab(tab)` | 切换工作区Tab |
| `sendMessage(content)` | 发送聊天消息 |
| `openUploadModal()` | 打开上传弹窗 |
| `closeUploadModal()` | 关闭上传弹窗 |
| `loadDatasets()` | 从后端加载数据集列表 |

#### Action类型

```typescript
type AppAction =
  | { type: 'SELECT_FILE'; payload: string }
  | { type: 'TOGGLE_FOLDER'; payload: string }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_ACTIVE_TAB'; payload: TabType }
  | { type: 'SET_CANVAS_CONTENT'; payload: CanvasContent }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'SET_PROCESSING'; payload: boolean }
  | { type: 'SET_ANALYSIS_STATUS'; payload: AnalysisStatus }
  | { type: 'SET_DATA_SOURCE'; payload: string }
  | { type: 'SET_UPLOAD_MODAL_OPEN'; payload: boolean }
  | { type: 'SET_DATASETS'; payload: Dataset[] }
  | { type: 'ADD_DATASET'; payload: Dataset };
```

---

### 5.4 components/layout/ - 布局组件

#### Sidebar.tsx

**功能**: 左侧边栏，包含文件导航和上传按钮

| 元素 | 说明 |
|------|------|
| Explorer标题 | 带折叠按钮 |
| 搜索框 | 文件搜索（UI已实现，功能待开发） |
| FileTree | 文件树组件 |
| Upload Dataset按钮 | 触发上传弹窗 |

#### MainWorkspace.tsx

**功能**: 中央工作区

| 元素 | 说明 |
|------|------|
| TabBar | 图表/表格/文字/代码 切换 |
| Canvas | 主内容区域 |
| ExportBar | 导出按钮（Word/PDF） |

#### ChatPanel.tsx

**功能**: 右侧对话面板

| 元素 | 说明 |
|------|------|
| MessageList | 消息列表 |
| ChatInput | 输入框 |

---

### 5.5 components/sidebar/ - 侧边栏组件

#### FileTree.tsx

**功能**: 显示文件树结构

| 部分 | 说明 |
|------|------|
| Uploaded Datasets区域 | 显示从后端加载的真实数据集 |
| Mock Files区域 | 显示静态演示数据 |

#### DatasetItem组件（内嵌）

| 功能 | 说明 |
|------|------|
| 展开/折叠 | 点击显示/隐藏文件列表 |
| 删除按钮 | 悬停显示，确认后删除 |
| 文件计数 | 右侧显示文件数量 |

#### FileItem.tsx

**功能**: 单个文件/文件夹项

| 功能 | 说明 |
|------|------|
| 图标 | 根据类型显示不同图标 |
| 选中状态 | 高亮显示 |
| 展开子项 | 文件夹可展开 |

---

### 5.6 components/upload/ - 上传组件

#### UploadModal.tsx

**功能**: 数据集上传弹窗

| 步骤 | 说明 |
|------|------|
| input | 输入名称、描述，选择文件 |
| uploading | 显示上传进度 |
| preview | 显示解析结果和列预览 |

**特性**:
- 拖放上传
- 多文件支持
- 文件类型验证（.csv, .xlsx, .xls）
- 上传进度条
- 错误处理

#### TablePreview.tsx

**功能**: 表格结构预览组件

| 显示内容 | 说明 |
|----------|------|
| 文件名 | 标题栏 |
| 行数/列数 | 统计信息 |
| 列表格 | 列名、类型、非空数、唯一数、样本值 |

**类型图标**:
- 🔢 Numeric (蓝色)
- 📝 Text (绿色)
- 📅 Date (紫色)
- 📋 Categorical (橙色)

---

### 5.7 components/chat/ - 对话组件

#### MessageList.tsx
显示消息列表，自动滚动到底部

#### MessageBubble.tsx
单条消息气泡，区分用户/助手/系统消息

#### ChatInput.tsx
输入框，支持Enter发送

---

### 5.8 components/workspace/ - 工作区组件

#### TabBar.tsx
Tab切换：图表 | 表格 | 文字 | 代码

#### Canvas.tsx
主内容展示区域（当前为占位符）

#### ExportBar.tsx
导出按钮：Word | PDF（功能待实现）

---

### 5.9 App.tsx - 应用入口

**功能**: 组合所有组件，渲染应用

| 部分 | 说明 |
|------|------|
| Header | 顶部导航栏，Logo，数据源选择器，状态指示 |
| 三栏布局 | Sidebar + MainWorkspace + ChatPanel |
| UploadModal | 上传弹窗（条件渲染） |

---

## 6. API接口文档

### 基础URL
```
http://localhost:8000
```

### 6.1 健康检查

```
GET /health

Response 200:
{
  "status": "healthy",
  "service": "icde-api"
}
```

### 6.2 创建数据集

```
POST /api/datasets

Request Body:
{
  "name": "Study ABC-123",        // 必填
  "description": "Clinical trial data"  // 可选
}

Response 201:
{
  "id": "uuid",
  "name": "Study ABC-123",
  "description": "Clinical trial data",
  "file_count": 0,
  "total_size": 0,
  "files": [],
  "created_at": "2026-02-07T12:00:00",
  "updated_at": "2026-02-07T12:00:00"
}
```

### 6.3 上传文件

```
POST /api/datasets/{dataset_id}/files

Content-Type: multipart/form-data
Body: files[] (multiple files allowed)

Response 200:
[
  {
    "id": "uuid",
    "file_name": "uuid.csv",
    "original_name": "patients.csv",
    "file_type": "csv",
    "file_size": 1024,
    "row_count": 100,
    "column_count": 5,
    "parse_status": "parsed",
    "parse_error": null,
    "created_at": "2026-02-07T12:00:00"
  }
]

Errors:
- 404: Dataset not found
- 400: File type not allowed / File too large
```

### 6.4 获取数据集列表

```
GET /api/datasets

Response 200:
[
  {
    "id": "uuid",
    "name": "Study ABC-123",
    "description": "...",
    "file_count": 3,
    "total_size": 10240,
    "files": [...],
    "created_at": "...",
    "updated_at": "..."
  }
]
```

### 6.5 获取单个数据集

```
GET /api/datasets/{dataset_id}

Response 200:
{
  "id": "uuid",
  "name": "Study ABC-123",
  "description": "...",
  "file_count": 3,
  "total_size": 10240,
  "files": [
    {
      "id": "uuid",
      "original_name": "patients.csv",
      ...
    }
  ],
  "created_at": "...",
  "updated_at": "..."
}

Errors:
- 404: Dataset not found
```

### 6.6 获取文件预览

```
GET /api/datasets/{dataset_id}/files/{file_id}/preview

Response 200:
{
  "file_id": "uuid",
  "file_name": "patients.csv",
  "row_count": 100,
  "column_count": 5,
  "columns": [
    {
      "name": "patient_id",
      "data_type": "text",
      "non_null_count": 100,
      "unique_count": 100,
      "sample_values": ["P001", "P002", "P003"]
    },
    {
      "name": "age",
      "data_type": "numeric",
      "non_null_count": 98,
      "unique_count": 45,
      "sample_values": ["58", "62", "45"]
    }
  ],
  "sample_rows": [
    {"patient_id": "P001", "age": 58, ...},
    {"patient_id": "P002", "age": 62, ...}
  ]
}

Errors:
- 404: File not found
- 400: File parsing failed
```

### 6.7 删除数据集

```
DELETE /api/datasets/{dataset_id}

Response 204: No Content

Errors:
- 404: Dataset not found
```

---

## 7. 数据流图

### 7.1 数据集上传流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   用户       │     │   前端       │     │   后端       │
└─────────────┘     └─────────────┘     └─────────────┘
      │                    │                    │
      │ 1. 点击上传按钮     │                    │
      │ ─────────────────> │                    │
      │                    │                    │
      │ 2. 输入名称，选择文件│                   │
      │ ─────────────────> │                    │
      │                    │                    │
      │                    │ 3. POST /api/datasets
      │                    │ ─────────────────> │
      │                    │                    │ 4. 创建文件夹
      │                    │                    │ 5. 插入Dataset记录
      │                    │ <───────────────── │
      │                    │    dataset_id      │
      │                    │                    │
      │                    │ 6. POST /datasets/{id}/files
      │                    │ ─────────────────> │
      │                    │                    │ 7. 保存文件
      │                    │                    │ 8. Pandas解析
      │                    │                    │ 9. 提取列元数据
      │                    │                    │ 10. 更新DatasetFile记录
      │                    │ <───────────────── │
      │                    │    file previews   │
      │                    │                    │
      │ 11. 显示列预览      │                    │
      │ <───────────────── │                    │
      │                    │                    │
      │ 12. 点击完成        │                    │
      │ ─────────────────> │                    │
      │                    │                    │
      │                    │ 13. GET /api/datasets
      │                    │ ─────────────────> │
      │                    │ <───────────────── │
      │                    │                    │
      │ 14. 更新侧边栏      │                    │
      │ <───────────────── │                    │
```

### 7.2 应用状态流

```
┌─────────────────────────────────────────────────────────────┐
│                      AppContext                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    AppState                          │    │
│  │  - datasets: Dataset[]      ← loadDatasets()        │    │
│  │  - uploadModalOpen: boolean ← open/closeUploadModal │    │
│  │  - files: FileNode[]        ← static mock data      │    │
│  │  - messages: Message[]      ← sendMessage()         │    │
│  │  - ...                                               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
    ┌──────────┐         ┌──────────┐         ┌──────────┐
    │ Sidebar  │         │ Workspace│         │ ChatPanel│
    └──────────┘         └──────────┘         └──────────┘
           │
           ▼
    ┌──────────┐
    │ FileTree │ ← 显示 datasets + files
    └──────────┘
```

---

## 8. 功能对照表

### 对照产品文档 MVP 范围

| 产品文档功能 | 代码实现 | 状态 | 文件位置 |
|-------------|---------|------|----------|
| **M1: 基础框架** | | | |
| 三栏UI布局 | ✅ | 完成 | `App.tsx`, `layout/` |
| - 左栏文件导航 | ✅ | 完成 | `Sidebar.tsx`, `FileTree.tsx` |
| - 中栏主工作区 | ✅ | 完成 | `MainWorkspace.tsx` |
| - 右栏对话 | ✅ | 完成 | `ChatPanel.tsx` |
| 对话交互 | ✅ | 基础UI | `chat/`, `AppContext.tsx` |
| 数据加载 | ✅ | 完成 | `api.ts`, `file_parser.py` |
| **M1扩展: 数据集上传** | | | |
| 创建数据集 | ✅ | 完成 | `datasets.py` (router) |
| 上传CSV/Excel | ✅ | 完成 | `datasets.py`, `UploadModal.tsx` |
| 文件解析 | ✅ | 完成 | `file_parser.py` |
| 列类型推断 | ✅ | 完成 | `FileParser.infer_data_type()` |
| 结构预览 | ✅ | 完成 | `TablePreview.tsx` |
| 侧边栏显示 | ✅ | 完成 | `FileTree.tsx` |
| 删除数据集 | ✅ | 完成 | `datasets.py`, `FileTree.tsx` |
| **M2: 语义筛选** | | | |
| Problem List生成 | ❌ | 待开发 | - |
| Embedding | ❌ | 待开发 | - |
| LLM筛选 | ❌ | 待开发 | - |
| **M3: 统计分析** | | | |
| 模型推荐 | ❌ | 待开发 | - |
| 代码执行 | ❌ | 待开发 | - |
| 结果展示 | ❌ | 待开发 | - |
| **M4: 输出生成** | | | |
| 表格生成 | ❌ | 待开发 | - |
| 图表生成 | ❌ | 待开发 | - |
| 论文文字 | ❌ | 待开发 | - |
| Word导出 | ❌ | 待开发 | - |

---

## 9. 运行指南

### 9.1 后端启动

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务 (端口 8000)
python run.py
```

### 9.2 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器 (端口 5173)
npm run dev
```

### 9.3 访问应用

打开浏览器访问: http://localhost:5173

---

## 10. 待开发功能

### 10.1 近期优先 (M2准备)

| 功能 | 说明 | 涉及模块 |
|------|------|----------|
| 数据预览面板 | 点击文件在工作区显示数据表 | Canvas.tsx, 新API |
| 文件搜索 | 侧边栏搜索功能 | Sidebar.tsx |
| LLM对话集成 | 替换mock响应为真实LLM | AppContext.tsx, 新service |

### 10.2 M2里程碑

| 功能 | 说明 |
|------|------|
| Problem List数据结构 | 患者事件时间线 |
| 事件提取服务 | LLM从原始数据提取事件 |
| Embedding服务 | 事件向量化 |
| 语义筛选API | 自然语言 → SQL/过滤条件 |

### 10.3 M3-M4里程碑

| 功能 | 说明 |
|------|------|
| 统计模型推荐 | 根据研究意图推荐分析方法 |
| Python代码执行 | 安全执行统计代码 |
| 图表渲染 | Matplotlib/ECharts集成 |
| 论文段落生成 | Methods/Results模板 |
| Word/PDF导出 | python-docx集成 |

---

## 附录：数据库Schema

```sql
-- 数据集表
CREATE TABLE datasets (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    folder_path     TEXT NOT NULL,
    file_count      INTEGER DEFAULT 0,
    total_size      INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 数据集文件表
CREATE TABLE dataset_files (
    id              TEXT PRIMARY KEY,
    dataset_id      TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    file_name       TEXT NOT NULL,
    original_name   TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    file_type       TEXT NOT NULL,
    file_size       INTEGER NOT NULL,
    row_count       INTEGER,
    column_count    INTEGER,
    column_info     TEXT,
    parse_status    TEXT DEFAULT 'pending',
    parse_error     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

*文档结束*
