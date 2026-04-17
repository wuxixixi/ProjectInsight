# 推演机制详解

## 概述

觉测·洞鉴支持两种推演模式和两种引擎：

| 维度 | 选项 | 说明 |
|------|------|------|
| 推演模式 | 沙盘/新闻 | 沙盘探索机制，新闻预测现实 |
| 推演引擎 | 数学模型/LLM | 数学模型快速，LLM逼真 |

## 观点表示

每个智能体（Agent）持有 **观点值**（opinion），范围为 `[-1, 1]`：

```
-1 ─────────────────────────────────────────── 0 ─────────────────────────────────────────── 1
  │                                        │                                        │
  │                                        │                                        │
完全相信谣言                              中立                                   完全相信真相
(Rumor Believer)                        (Neutral)                             (Truth Acceptor)
```

## 推演模式

### 沙盘推演模式 (Sandbox)

**目标**：研究传播机制和参数敏感度

**特点**：
- 参数完全可控
- 快速复现实验
- 机制解释性研究

**适用场景**：
- 教学演示
- 参数敏感度分析
- 学术研究

### 新闻推演模式 (News)

**目标**：预测现实舆情演进，支持干预决策

**特点**：
- 真实舆情分布锚定
- 输出预测区间而非单值
- 风险预警和干预建议
- 知识图谱驱动演化

**适用场景**：
- 舆情预警
- 干预时机决策
- 智库专报生成

## 数学模型引擎

### 核心机制

基于社会心理学理论，通过公式计算观点演化：

```
new_opinion = f(social_influence, cocoon_effect, debunking, polarization, knowledge_influence)
```

#### 1. 社交影响 (Social Influence)

个体受邻居观点的影响：

```
social_influence = Σ(w_i * opinion_i) / Σ(w_i)
```

其中 `w_i` 是邻居 i 的影响力权重。

#### 2. 算法茧房效应 (Echo Chamber)

推荐算法强化既有观点倾向：

```
cocoon_adjustment = cocoon_strength * (old_opinion - avg_recommendation)
```

- `cocoon_strength = 0`：无茧房效应
- `cocoon_strength = 1`：完全茧房，只看到同温层内容

#### 3. 官方辟谣 (Official Debunking)

辟谣信息对相信谣言者的影响：

```
if debunking_active:
    if opinion < 0:  # 相信谣言
        adjustment = -debunk_credibility * authority_factor * (1 + backfire)
        # backfire: 逆火效应（部分人反而更相信谣言）
    else:  # 已经相信真相
        adjustment = debunk_credibility * authority_factor
```

#### 4. 群体极化 (Group Polarization)

群体讨论使观点走向极端：

```
polarization = polarization_factor * (avg_opinion - opinion) * |avg_opinion|
```

#### 5. 沉默的螺旋 (Spiral of Silence)

害怕被孤立而不敢表达观点：

```
if perceived_opposition > silence_threshold:
    is_silent = True
    opinion_change = 0  # 不表达观点
```

#### 6. 知识驱动影响（新闻模式）

新闻模式下的知识图谱驱动演化：

```
knowledge_influence = entity_impact * evidence_strength * persona_factor
```

- **实体影响**：重要实体对观点的影响更大
- **证据强度**：可信事件影响更强
- **人设调节**：不同人设受影响程度不同

### 增强版参数

| 参数 | 范围 | 说明 |
|------|------|------|
| debunk_credibility | 0~1 | 辟谣来源可信度 |
| authority_factor | 0~1 | 权威影响力系数 |
| backfire_strength | 0~1 | 逆火效应强度 |
| silence_threshold | 0~1 | 沉默阈值 |
| polarization_factor | 0~1 | 群体极化系数 |
| echo_chamber_factor | 0~1 | 回音室效应系数 |

---

## LLM 驱动引擎

### 智能体架构

每个 LLM Agent 具有以下属性：

```python
class LLMAgent:
    id: int
    opinion: float                    # 观点值 [-1, 1]
    belief_strength: float            # 信念强度 [0, 1]
    susceptibility: float              # 易感性 [0, 1]
    influence: float                  # 影响力 [0, 1]

    # 人设属性
    persona: Persona                  # 7种人设类型

    # 决策相关
    emotion: str                      # 情绪状态
    action: str                       # 行动选择
    generated_comment: str            # 生成的评论
    reasoning: str                    # 决策推理过程
```

### 人设系统 (Persona)

系统内置 7 种人设，影响 Agent 的决策风格：

| 人设类型 | 描述 | 决策特点 |
|----------|------|----------|
| 理性分析者 | 注重逻辑和数据 | 谨慎决策、易被证据说服 |
| 情感驱动者 | 重视情感共鸣 | 易受情绪化内容影响 |
| 权威服从者 | 信任权威来源 | 相信官方辟谣 |
| 怀疑论者 | 质疑一切信息 | 难以被说服、倾向于中立 |
| 社交活跃者 | 频繁互动传播 | 高影响力、带动他人 |
| 沉默观察者 | 较少发言 | 低影响力、被动接受 |
| 极端主义者 | 立场坚定 | 极难改变观点 |

### 决策流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Agent 决策流程                           │
└─────────────────────────────────────────────────────────────────┘

     ┌──────────────┐
     │  输入上下文   │
     │  (邻居观点)  │
     │  (辟谣信息)  │
     │  (接收新闻)  │
     │  (知识图谱)  │ ← 新闻模式专用
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │ 构建 Prompt  │ ← 注入人设特征
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │   调用 LLM   │ → DeepSeek API
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │ 解析响应     │
     │  - 新观点   │
     │  - 情绪     │
     │  - 行动     │
     │  - 评论     │
     │  - 推理过程 │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │ 更新 Agent   │
     └──────────────┘
```

### Prompt 模板示例

```prompt
你是一位{persona_type}，{persona_description}。

【当前事件知识图谱】
- 实体: {entities}
- 关系: {relations}
- 摘要: {summary}

当前信息环境：
- 谣言传播率: {rumor_rate}%
- 真相接受率: {truth_rate}%
- 你收到的信息: {received_news}

你当前的观点: {current_opinion} (-1到1，-1=完全相信谣言，1=完全相信真相)
你的信念强度: {belief_strength} (越高越难改变)
你的易感性: {susceptibility} (越高越容易受他人影响)

邻居们的观点: {neighbor_opinions}

请决定：
1. 你的新观点是什么？（考虑邻居影响、知识图谱和你的信念强度）
2. 你的情绪状态是什么？
3. 你会采取什么行动？（转发/评论/观望/辟谣）
4. 如果评论，你会说什么？
5. 简述你的推理过程。
```

---

## 网络模型

### 单层网络

支持三种网络拓扑：

| 类型 | 算法 | 特点 |
|------|------|------|
| 小世界 | Watts-Strogatz | 高聚类、短路径，模拟真实社交 |
| 无标度 | Barabási-Albert | 存在超级节点，模拟意见领袖 |
| 随机 | Erdős-Rényi | 基准对照 |

### 双层网络

模拟公域（微博）与私域（微信）的信息传播差异：

```
公域网络 (Public Domain)
├── 无标度网络
├── 存在大V/官媒（高影响力节点）
└── 信息传播快、范围广

私域网络 (Private Domain)
├── 多个独立社群 (Community)
├── 社群内连接紧密
└── 跨社群传播较难

跨域传播
├── 部分用户同时活跃于公域和私域
└── 作为信息桥梁
```

---

## 辟谣机制

### 辟谣时机

辟谣延迟以"步"为单位，每步代表一个时间单位（可理解为一天或一个传播周期）：

```
步数: 0    5    10   15   20   25
      │    │    │    │    │    │
      ├────┴────┴────┴────┴────┤
谣言传播                    辟谣发布
      ←── 延迟 = 10 步 ──→
```

### 辟谣效果

辟谣效果受以下因素影响：

1. **可信度** (`debunk_credibility`): 辟谣来源的权威性
2. **权威因子** (`authority_factor`): 发布者的影响力
3. **逆火效应** (`backfire_strength`): 部分人群反而更相信谣言
4. **时机**: 延迟越长，谣言传播范围越广，辟谣越困难

---

## 知识图谱解析

### 概述

知识图谱解析是系统的数据预处理层，将非结构化新闻文本转换为结构化的实体-关系图谱，使 Agent 能够更准确地理解事件内容。

**响应时间**：10-60秒（需调用LLM）

### 解析流程

```
新闻文本 → LLM API 调用 → 实体/关系提取 → 结构化知识图谱
```

### 知识图谱结构

```json
{
  "entities": [
    {"name": "王某杞", "type": "人物", "description": "某科技公司CEO", "importance": 1},
    {"name": "某科技公司", "type": "组织", "description": "新闻中提及的科技公司", "importance": 2},
    {"name": "北京", "type": "地点", "description": "发布会举办地点", "importance": 4},
    {"name": "100亿元", "type": "概念", "description": "公司计划投资的金额", "importance": 3}
  ],
  "relations": [
    {"source": "王某杞", "target": "某科技公司", "action": "担任CEO", "type": "关联"},
    {"source": "某科技公司", "target": "100亿元", "action": "计划投资", "type": "影响"}
  ],
  "summary": "某科技公司CEO王某杞在北京发布会上宣布公司将投资100亿元。",
  "sentiment": "正面",
  "credibility_hint": "高可信"
}
```

### 实体类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 人物 | 事件中涉及的人名 | 王某杞、张三 |
| 组织 | 公司、机构、团体 | 某科技公司、政府部门 |
| 地点 | 地理位置 | 北京、上海 |
| 事件 | 具体发生的事件 | 发布会、事故 |
| 概念 | 抽象概念或数值 | 100亿元、安全隐患 |

### 实体重要性

| 重要性 | 说明 | 对观点影响 |
|--------|------|-----------|
| 1 | 核心实体，主角 | 影响力=1.0 |
| 2 | 重要实体，关键角色 | 影响力=0.8 |
| 3 | 一般实体，有影响 | 影响力=0.6 |
| 4 | 次要实体，背景信息 | 影响力=0.4 |
| 5 | 边缘实体，可忽略 | 影响力=0.2 |

---

## 知识驱动演化

### 机制

知识图谱参与观点演化计算，而非仅作为LLM上下文：

```
观点增量 = f(实体影响力, 证据强度, 人设调节, 茧房效应)
```

### 计算公式

```python
def compute_entity_influence(agent, entity, cocoon_strength):
    # 基础影响力
    base_impact = entity.importance_weight  # 1.0 ~ 0.2

    # 人设调节
    if "意见领袖" in agent.persona:
        base_impact *= authority_factor
    elif "怀疑论者" in agent.persona:
        base_impact *= 0.5
    elif "从众者" in agent.persona:
        base_impact *= 1.2

    # 茧房效应：同向观点影响更大
    cocoon_effect = cocoon_strength * agent.opinion * 0.1

    # 证据强度
    evidence_factor = event.credibility_score  # 0.3 ~ 0.8

    return base_impact * evidence_factor + cocoon_effect
```

### 影响力传递

通过关系网络传递影响力：

```
张三(人物) --指控--> 某公司(组织) --导致--> 股价下跌(概念)
    │                  │                   │
    │                  │                   │
影响力: 1.0          影响力: 0.8         影响力: 0.6

传递衰减: 每增加一层关系，影响力 × 0.7
```

---

## 快速注入模式

### 概述

推演过程中注入事件时，可选择跳过知识图谱解析，秒级响应。

### 对比

| 模式 | 响应时间 | 知识图谱 | 适用场景 |
|------|----------|----------|----------|
| 完整解析 | 10-60秒 | 完整解析 | 首次注入、深度分析 |
| 快速注入 | 1-2秒 | 跳过解析 | 推演中注入、快速测试 |

### 使用方式

前端勾选"快速注入"选项，或API调用时设置 `skip_parse: true`。

---

## 预测机制（新闻模式）

### 预测区间

新闻模式输出置信区间而非单值：

```json
{
  "rumor_spread_rate": {
    "expected": 0.52,      // 最可能值
    "optimistic": 0.38,    // 乐观场景（下界）
    "pessimistic": 0.66,   // 悲观场景（上界）
    "confidence": 0.95      // 置信度
  }
}
```

### 轨迹预测

基于历史数据和趋势外推：

```
┌─────────────────────────────────────────────────────────────────────┐
│                    预测轨迹示意                                      │
└─────────────────────────────────────────────────────────────────────┘

谣言传播率
  │
1.0 ┤                           ╭────────── 悲观场景
    │                      ╭────╯
0.8 ┤                 ╭───╯
    │            ╭────╯      ╭────────── 期望场景
0.6 ┤       ╭───╯      ╭────╯
    │  ╭───╯      ╭───╯
0.4 ┤──╯      ╭───╯         ╭────────── 乐观场景
    │     ╭───╯        ╭────╯
0.2 ┤ ╭───╯       ╭────╯
    │─╯      ╭────╯
0.0 ┴────────┴────────────────────────────────→
    当前      5步      10步     15步    预测步数
```

### 风险预警

基于当前状态和预测趋势计算风险：

| 风险等级 | 条件 | 含义 |
|----------|------|------|
| critical | 谣言率>50% 或 极化>0.8 | 需立即干预 |
| high | 谣言率>35% 或 极化>0.6 | 高度关注 |
| medium | 谣言率>20% 或 极化>0.4 | 持续监控 |
| low | 其他情况 | 正常 |

### 干预时机建议

自动分析最佳干预时机：

```python
def recommend_intervention(current_state, prediction):
    # 计算干预窗口
    if prediction.rumor_rate_at_step(10) > 0.5:
        # 预测10步后谣言失控，建议立即干预
        return {
            "recommended_step": current_step + 3,
            "urgency": "high"
        }

    # 分析干预效果
    for step in range(current_step, current_step + 15):
        simulated_impact = simulate_intervention(step)
        if simulated_impact.effectiveness > 0.3:
            return {
                "recommended_step": step,
                "expected_reduction": simulated_impact.effectiveness
            }
```

---

## 对比：数学模型 vs LLM 驱动

| 维度 | 数学模型 | LLM 驱动 |
|------|----------|----------|
| 速度 | 快（毫秒级/步） | 慢（秒级/步，需API调用） |
| 决策可解释性 | 公式透明 | Prompt + Response |
| 行为多样性 | 有限 | 丰富（LLM 生成） |
| 知识理解 | 基础（参数化） | 深度（知识图谱） |
| 适用场景 | 参数探索、大规模模拟 | 深度分析、专报生成 |
| 成本 | 低 | 高（API 调用费用） |
| 可复现性 | 高 | 中（LLM 输出有随机性） |

---

## 配置建议

### 快速参数探索

使用数学模型模式，设置：
- population_size: 200-500
- use_llm: false

### 深度研究分析

使用 LLM 驱动模式，设置：
- population_size: 50-100（降低成本）
- use_llm: true
- max_concurrent: 20-50（控制并发）

### 新闻模式预测

使用新闻模式，设置：
- init_distribution: 基于真实数据
- use_llm: true（更准确的模拟）
- population_size: 100-200

### 生产部署

- 使用双层网络（use_dual_network: true）
- 根据服务器性能调整 max_concurrent
- 考虑使用本地 LLM（如 Ollama）降低成本
