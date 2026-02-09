# 数据集版本控制与脚本系统

本文档描述了 ICDE 中数据集版本控制和脚本执行系统的设计与实现。

## 概述

系统支持两个维度的数据组织：
- **时间维度（版本）**：同一数据集的多个版本（如 CRF 更新）
- **逻辑维度（派生）**：通过脚本从源数据集派生分析集（如 FAS、PPS、ITT）

## 数据模型

### Dataset 扩展字段

```python
class Dataset:
    # 类型
    type: DatasetType  # RAW | DERIVED

    # 版本血缘（时间维度）
    parent_dataset_id: str | None  # 指向上一个版本
    crf_version: str | None        # CRF 版本号

    # 派生血缘（逻辑维度）
    source_dataset_id: str | None  # 源数据集
    script_id: str | None          # 使用的脚本

    # 患者标识
    patient_id_column: str | None  # 患者 ID 列名，默认 "SUBJID"

    # 过期状态
    is_stale: bool                 # 是否过期
    stale_reason: str | None       # 过期原因
```

### Script 模型

```python
class Script:
    id: str
    name: str           # 唯一标识，如 "create_fas"
    display_name: str   # 显示名称，如 "FAS 生成脚本"
    description: str    # 详细描述，用于 LLM 匹配
    keywords: list[str] # 关键词，支持中文搜索

    code: str           # Python 代码，必须包含 transform(df) 函数
    language: str       # 默认 "python"

    created_by: str     # "user" | "llm"
    created_from_prompt: str | None  # LLM 生成时的原始 prompt

    usage_count: int    # 使用次数
    last_used_at: datetime | None

    version: int        # 脚本版本
    parent_script_id: str | None  # 父脚本（用于版本追踪）
```

## API 端点

### 脚本管理

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/scripts` | 创建脚本 |
| GET | `/api/scripts` | 列出所有脚本 |
| GET | `/api/scripts/{id}` | 获取脚本详情 |
| GET | `/api/scripts/search?q=` | 搜索脚本（支持中文） |
| PUT | `/api/scripts/{id}` | 更新脚本 |
| DELETE | `/api/scripts/{id}` | 删除脚本 |

### 数据集版本

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/datasets` | 创建数据集（支持 `parent_dataset_id`） |
| GET | `/api/datasets/{id}/versions` | 获取版本历史 |

### 数据集派生

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/datasets/{id}/derive` | 使用脚本派生新数据集 |
| GET | `/api/datasets/{id}/derived` | 获取派生数据集列表 |

### 血缘追踪

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/datasets/{id}/lineage` | 获取完整血缘（祖先和后代） |

## 脚本规范

### transform 函数

所有脚本必须定义 `transform(df)` 函数：

```python
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    生成 FAS（全分析集）。
    纳入：RANDFL = 'Y'
    排除：PPROTFL = 'Y'
    """
    fas = df[
        (df['RANDFL'] == 'Y') &
        (df['PPROTFL'] != 'Y')
    ].copy()
    return fas
```

### 执行环境

- 脚本在隔离的命名空间中执行
- 预置模块：`pandas`（作为 `pd` 和 `pandas`）
- 返回值必须是 `pd.DataFrame`

## 服务层

### ScriptExecutor

```python
class ScriptExecutor:
    def execute(self, code: str, input_file: Path) -> ExecutionResult
    def execute_and_save(self, script, source_dataset, output_name, output_dir, db) -> ExecutionResult
    def validate_syntax(self, code: str) -> tuple[bool, str | None]
    def extract_referenced_columns(self, code: str) -> list[str]
```

### DiffCalculator

```python
class DiffCalculator:
    def calculate(self, v1_path: Path, v2_path: Path) -> dict
    def generate_summary_text(self, diff: dict) -> str
```

计算结果包括：
- `patients_added`: 新增患者列表
- `patients_removed`: 删除患者列表
- `patients_modified`: 修改患者列表
- `columns_added`: 新增列
- `columns_removed`: 删除列
- `total_cells_changed`: 变更单元格总数

## 使用示例

### 创建新版本

```bash
curl -X POST http://localhost:8000/api/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Study_ABC_2024-03-15",
    "crf_version": "v1.1",
    "parent_dataset_id": "原版本ID"
  }'
```

### 创建脚本

```bash
curl -X POST http://localhost:8000/api/scripts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "create_fas",
    "display_name": "FAS 生成",
    "description": "生成全分析集，纳入随机化患者，排除主要方案违背",
    "keywords": ["FAS", "全分析集", "efficacy"],
    "code": "def transform(df):\n    return df[(df[\"RANDFL\"]==\"Y\") & (df[\"PPROTFL\"]!=\"Y\")]"
  }'
```

### 派生数据集

```bash
curl -X POST http://localhost:8000/api/datasets/{source_id}/derive \
  -H "Content-Type: application/json" \
  -d '{
    "script_id": "脚本ID",
    "output_name": "Study_ABC_2024-03-15_FAS"
  }'
```

### 搜索脚本

```bash
# 英文搜索
curl "http://localhost:8000/api/scripts/search?q=FAS"

# 中文搜索
curl "http://localhost:8000/api/scripts/search?q=全分析集"
```

### 获取血缘

```bash
curl http://localhost:8000/api/datasets/{id}/lineage
```

响应示例：
```json
{
  "dataset": {
    "id": "xxx",
    "name": "Study_ABC_FAS",
    "type": "DERIVED"
  },
  "ancestors": [
    {
      "id": "yyy",
      "name": "Study_ABC_2024-03-15",
      "type": "RAW",
      "relationship": "derivation_source"
    }
  ],
  "descendants": []
}
```

## 测试

运行所有测试：

```bash
cd backend
python -m pytest tests/ -v
```

测试覆盖：
- 模型测试 (11 tests)
- 脚本执行测试 (12 tests)
- API 测试 (12 tests)

## 前端类型

```typescript
interface Script {
  id: string;
  name: string;
  display_name: string;
  description: string;
  code: string;
  keywords: string[] | null;
  language: string;
  created_by: 'user' | 'llm';
  usage_count: number;
  // ...
}

interface Dataset {
  // 新增字段
  type: 'RAW' | 'DERIVED';
  parent_dataset_id: string | null;
  source_dataset_id: string | null;
  script_id: string | null;
  crf_version: string | null;
  patient_id_column: string | null;
  is_stale: boolean;
  stale_reason: string | null;
  // ...
}
```

## 后续工作

1. **前端 UI**：血缘关系可视化、脚本编辑器
2. **LLM 集成**：根据用户描述自动匹配或生成脚本
3. **级联更新**：源数据更新时自动标记派生数据集为过期
4. **Diff 可视化**：版本间差异的可视化展示
