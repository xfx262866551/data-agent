# data-agent

> Natural-language-to-SQL agent for e-commerce analytics.
> 自然语言问数智能体：输入一句大白话，自动完成查询改写、元数据召回、SQL 生成、语法校验与执行，SSE 流式返回全过程。

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C?logo=langchain&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-1.16-DC382D)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8-005571?logo=elasticsearch&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

**13 节点 LangGraph 工作流 · 元数据三层存储 · 单轮评估 10/10 · 多轮评估 5/5**

## 目录

- [功能特性](#功能特性)
- [架构](#架构)
- [快速开始](#快速开始)
- [接口](#接口)
- [评估](#评估)
- [配置说明](#配置说明)
- [目录结构](#目录结构)
- [设计要点](#设计要点)
- [限制与规划](#限制与规划)
- [License](#license)

## 功能特性

| 能力 | 说明 |
|---|---|
| 元数据知识库 | 表/字段/指标结构存 MySQL，字段与指标语义向量存 Qdrant，字段真实取值存 Elasticsearch(ik)——分别解决结构查询、说法与字段名不一致、where 条件枚举值匹配 |
| 问数工作流 | 13 节点 LangGraph 图：改写 → 抽词 → 三路并行召回 → 合并 → 双线并行过滤 → 补上下文 → 生成 SQL → EXPLAIN 校验 → 条件边自纠 → 执行 |
| 多轮对话 | 任务 = 会话（`thread_id`），checkpointer 持久化 state；入口改写节点把省略追问补成独立问题，继承上一轮的时间/指标条件 |
| 任务体系 | 5 个 REST 接口（新建/列表/改名/删除/任务内提问），任务数据存独立业务库，与可重建的知识库物理隔离 |
| 流式输出 | SSE 逐节点推送进度；流开始后异常包装为流内消息 |
| 自动评估 | 单轮 10 题 + 多轮 5 例，按期望数字判分，可一键重跑 |

## 架构

### 执行链路

```
用户问题
  └─ rewrite_query            多轮追问 → 独立问题
      └─ extract_keywords     jieba 抽词（不用 LLM：零成本、确定性、毫秒级）
          ├─ recall_column   关键词扩展 → 向量化 → Qdrant 字段召回
          ├─ recall_value    关键词扩展 → 向量化 → ES 取值召回          ── 三路并行
          └─ recall_metric   关键词扩展 → 向量化 → Qdrant 指标召回
              └─ merge_retrieved_info    按 id 合并，补依赖字段/主外键/表结构
                  ├─ filter_table        模型只选"保留哪些"，裁剪由程序完成   ── 双线并行
                  └─ filter_metric       同上
                      └─ add_extra_context    日期 + 数据库方言/版本
                          └─ generate_sql    五份上下文 → SQL
                              └─ validate_sql    EXPLAIN 预校验
                                  ├─ 通过 → run_sql
                                  └─ 失败 → correct_sql → run_sql
```

### 数据分层

```
┌────────────────────────────── API 层 ──────────────────────────────┐
│  FastAPI 路由 · SSE 流式响应 · 依赖注入 · request_id 日志追踪        │
├───────────────────────────── Service 层 ───────────────────────────┤
│  QueryService（问数编排）  MetaKnowledgeService（知识构建）         │
│  TaskService（任务管理）                                            │
├───────────────────────────── Agent 层 ─────────────────────────────┤
│  LangGraph 13 节点 · State / Context 分离 · RetryPolicy            │
├─────────────────────────── Repository 层 ──────────────────────────┤
│  session / client 全部外部传入，仓储不创建连接                      │
├──────────────┬──────────────────┬──────────────────┬───────────────┤
│ meta (MySQL) │   dw (MySQL)     │   biz (MySQL)    │ Qdrant / ES   │
│ 知识库(可重建)│  数仓业务数据     │  任务(不可丢)     │ 向量 / 全文    │
└──────────────┴──────────────────┴──────────────────┴───────────────┘
```

### 技术栈

| 层 | 选型 | 选型理由 |
|---|---|---|
| Web | FastAPI + uvicorn | 原生 async，异步生成器直接对接 SSE |
| 编排 | LangGraph | 并行扇出/扇入、条件边自纠循环、checkpointer 会话记忆 |
| 模型接入 | LangChain `init_chat_model` | 统一工厂，换模型/厂商只改一处 |
| 结构存储 | MySQL 8（meta/dw/biz 三库） | 知识库与业务数据分库，知识库可随时重建 |
| 向量检索 | Qdrant | 字段/指标语义召回，uuid5 派生 point id 保证幂等 |
| 全文检索 | Elasticsearch + ik | 字段真实取值匹配（中文分词） |
| 分词 | jieba | 机械抽词零成本、确定性，不占模型调用 |
| 配置 | omegaconf + dotenv | `.env` / YAML / dataclass 三层分离 |

## 快速开始

### 前置要求

| 依赖 | 版本 | 端口 |
|---|---|---|
| Python | 3.10+ | — |
| Docker + Compose | 最新稳定版 | — |
| MySQL | 8.0（compose 提供） | 3306 |
| Qdrant | v1.16（compose 提供） | 6333 |
| Elasticsearch | 8.x + ik 插件（compose 提供） | 9200 |
| OpenAI 兼容 API | chat + embeddings 各一个 key | — |

### 步骤

```bash
# 1. 起依赖服务（ES 镜像自带 ik 分词插件）
cd docker && docker compose up -d && cd ..

# 2. 配置密钥
cp .env.example .env      # 填入 LLM/EMBED 的 key 与 base_url、DB_PASSWORD

# 3. 安装依赖
pip install -e .

# 4. 构建元数据知识库（幂等，可重复执行）
py -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml

# 5. 启动服务
py main.py                # http://127.0.0.1:8000 ，接口文档 /docs
```

模型名称在 `conf/app_config.yaml` 中配置（默认 `step-3.7-flash` + `BAAI/bge-m3`），任何 OpenAI 兼容接口都可接入。

### 验证

```bash
curl -N -s -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" -d '{"query":"2025年1月各大区的销售额是多少"}'
```

返回 SSE 流（节选）：

```
data: {"type": "progress", "step": "改写问题", "status": "success"}
data: {"type": "progress", "step": "抽取关键词", "status": "success"}
data: {"type": "progress", "step": "召回字段信息", "status": "success"}
data: {"type": "progress", "step": "生成SQL", "status": "success"}
data: {"type": "progress", "step": "校验SQL", "status": "success"}
data: {"type": "progress", "step": "执行SQL", "status": "success"}
data: {"type": "result", "data": [{"大区": "华东", "销售额": 54924.0},
                                  {"大区": "华南", "销售额": 28096.5},
                                  {"大区": "华中", "销售额": 11397.0}]}
```

多轮追问（同一 `task_id` 自动继承上一轮的时间条件）：

```bash
# 1. 建任务
curl -s -X POST http://127.0.0.1:8000/api/tasks \
  -H "Content-Type: application/json" -d '{"question":"2025年1月各大区销售额"}'

# 2. 在该任务下连续追问
curl -N -s -X POST http://127.0.0.1:8000/api/tasks/<task_id>/query \
  -H "Content-Type: application/json" -d '{"query":"那华南区呢"}'
# → 改写为「2025年1月华南区的销售额是多少」→ [{"销售额": 28096.5}]
```

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/query` | 无状态单轮提问（一次性 thread，不继承历史） |
| POST | `/api/tasks` | 新建任务 |
| GET | `/api/tasks` | 任务列表（按更新时间倒序） |
| PATCH | `/api/tasks/{task_id}` | 任务改名 |
| DELETE | `/api/tasks/{task_id}` | 删除任务 |
| POST | `/api/tasks/{task_id}/query` | 任务内多轮提问（同 thread 继承历史） |

统一约定：请求体 JSON，字段 `query` / `question`；流式接口返回 `text/event-stream`，消息类型为 `progress` / `result` / `error`。

## 评估

```bash
py -m app.scripts.run_eval              # 单轮 10 题
py -m app.scripts.run_multi_turn_eval   # 多轮 5 例
```

| 评估集 | 题量 | 覆盖类型 | 当前结果 |
|---|---|---|---|
| `data/eval_set.json` | 10 | 按月/全年汇总、最高最低大区、枚举值映射、最畅销商品、空数据边界 | 10/10 |
| `data/eval_set_multi_turn.json` | 5 例（两轮） | 换区域继承时间条件、继承指标、完整问题不漂移 | 5/5 |

判分口径：提取结果中的数值，期望数字全部出现（容差 0.01）即通过；无数据题要求结果为空或全 null。评估集可自行扩充，重跑即回归。

## 配置说明

三层分离，密钥不进代码：

| 层 | 文件 | 内容 |
|---|---|---|
| 密钥 | `.env`（不入 Git，模板 `.env.example`） | `LLM_API_KEY` / `LLM_BASE_URL` / `EMBED_API_KEY` / `EMBED_BASE_URL` / `DB_PASSWORD` |
| 参数 | `conf/app_config.yaml` | 日志、三个库连接、Qdrant/ES/Embedding/LLM 参数与模型名 |
| 元数据 | `conf/meta_config.yaml` | 表结构（角色/别名/是否同步取值）与指标口径 |
| 代码 | `app/conf/*.py` | dataclass 强类型 + omegaconf 结构化加载 |

## 目录结构

```
app/
├── conf/            配置加载（dataclass + omegaconf）
├── clients/         外部客户端单例（Qdrant / ES / MySQL×3 / Embedding）
├── entities/        业务实体（dataclass，面向提示词）
├── models/          SQLAlchemy ORM 映射
├── repositories/    仓储层
│   ├── mysql/       meta / dw / biz 三个库
│   ├── qdrant/      字段与指标向量（uuid5 确定性 point id）
│   └── es/          字段取值全文索引（ik 分词）
├── services/        业务编排（知识构建 / 问数 / 任务）
├── agent/           LangGraph：state + context + llm + 13 节点 + 图组装
├── api/             FastAPI：lifespan / dependencies / routers / schemas
├── core/            日志（request_id 链路追踪）与请求上下文
├── prompt/          提示词加载器
└── scripts/         知识构建与评估入口
prompts/             8 个提示词模板
data/                评估集
docker/              compose + ES 镜像（ik 插件）
```

## 设计要点

**1. 模型只选择，程序做裁剪。** 召回与过滤环节模型只输出"保留哪些 id/名称"，数据裁剪由代码完成——从机制上避免模型编造表结构或字段。

**2. 三层存储各自解决一类问题。** MySQL 存结构与口径（可靠、可事务）、Qdrant 存语义向量（解决"用户说法 ≠ 字段名"）、ES+ik 存真实取值（解决 where 里的枚举匹配）。混用单一存储必然在其中一类上妥协。

**3. 全链路幂等。** MySQL 先删后插（同事务）、Qdrant point id 由业务 id 经 uuid5 派生（同内容同 id，upsert 即覆盖）、ES 用业务 id 作 `_id` 并显式 refresh。知识库可随时重建而不产生重复数据。

**4. 异常分层，只重试可自愈错误。** 节点只抛不吞，编排层统一捕获（问数服务包装成 SSE 错误消息，评估脚本按题记录失败）；仅对 429/5xx/超时重试（节点级 `RetryPolicy`），4xx 不重试。

## 限制与规划

| 当前限制 | 影响 | 规划 |
|---|---|---|
| 会话记忆用 `InMemorySaver`（进程内存） | 服务重启会话丢失 | 换 `PostgresSaver` / `RedisSaver`，只改 `compile()` 一处 |
| SQL 校验仅 `EXPLAIN` 语法检查 | 查不出业务语义错误（如时间条件写进 `LEFT JOIN ... ON`） | 加结果集合理性校验（行数/量级/空值率）+ 抽样人工复核 |
| 未做登录鉴权（`user_id` 固定 `demo`） | 多用户数据不隔离 | 接 SSO/JWT，任务查询按 user 过滤 |
| 历史仅保留最近 3 轮原始提问 | 长会话上下文不足 | 超长历史做滚动摘要 |
| 单机部署，无应用级限流 | 依赖模型服务端并发限制 | 加请求队列 + 降级提示 |

## License

[MIT](./LICENSE)
