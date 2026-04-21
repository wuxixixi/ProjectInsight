# 信息茧房推演系统 v2.0 设计方案

> 双模式架构：沙盘推演模式 + 新闻推演模式

## 开发状态

| 阶段 | 功能 | 状态 |
|------|------|------|
| Phase 1 | 知识驱动演化 + 实体影响力 | ✅ 已完成 |
| Phase 2 | 预测区间 + 风险预警 + 事件注入 | ✅ 已完成 |
| Phase 3 | 完整新闻模式 + 干预建议 | ✅ 已完成 |
| Phase 4 | 语义重构 + 文档完善 | ✅ 已完成 |

---

## 一、概述

### 1.1 设计背景

当前系统存在一个**核心断层**：

```
新闻注入 → 仅解析为知识图谱 → 未参与观点演化
负面信念定义 → 仅是"初始观点分布"，无具体内容
权威回应机制 → 仅是时间触发，无具体内容
```

这导致：
- 沙盘推演无法与真实新闻关联
- 新闻推演缺乏预测能力
- 知识图谱仅作为 LLM 上下文，未驱动演化

### 1.2 设计目标

| 目标 | 描述 | 状态 |
|------|------|------|
| 双模式支持 | 沙盘推演（假设驱动）+ 新闻推演（现实锚定） | ✅ |
| 知识驱动 | 知识图谱参与观点演化，而非仅作为上下文 | ✅ |
| 预测能力 | 输出置信区间，而非单值 | ✅ |
| 干预锚定 | 权威回应内容具体化，可设置干预时机和内容 | ✅ |

### 1.3 语义抽象

系统采用语义抽象设计，将特定领域概念映射为通用概念：

| UI文案 | 内部命名 | 英文标识 | 示例场景 |
|--------|----------|----------|----------|
| 误信 | 负面信念 | `negative_belief` | 谣言、片面解读、恐慌信息 |
| 正确认知 | 正面信念 | `positive_belief` | 真相、完整事实、指导信息 |
| 权威回应 | 权威回应 | `authority_response` | 辟谣、官方澄清、权威解读 |

---

## 二、系统架构

### 2.1 双模式对比

```
┌─────────────────────────────────────────────────────────────┐
│                    SimulationEngine                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────┐   │
│  │   模式A：沙盘推演    │    │     模式B：新闻推演      │   │
│  │   (Sandbox Mode)     │    │   (News Mode)           │   │
│  ├─────────────────────┤    ├─────────────────────────┤   │
│  │ 目标：研究传播机制    │    │ 目标：预测现实演进       │   │
│  │                     │    │                           │   │
│  │ ·抽象负面信念模型    │    │ ·真实新闻事件             │   │
│  │ ·参数可调           │    │ ·历史节点标注               │   │
│  │ ·假设驱动           │    │ ·事实锚定 + 预测           │   │
│  │                     │    │                           │   │
│  │ 负面信念内容：模板化 │    │ 负面信念内容：新闻文本解析 │   │
│  │  "A事件导致B"       │    │  关联实体、立场、证据     │   │
│  │                     │    │                           │   │
│  │ Agent初始分布       │    │ Agent初始分布             │   │
│  │  按 initial_        │    │  按真实舆情采样           │   │
│  │  negative_spread    │    │  或问卷数据               │   │
│  │                     │    │                           │   │
│  │ 输出：单值结果      │    │ 输出：预测区间 + 风险预警  │   │
│  └─────────────────────┘    └─────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 文件结构

```
backend/
├── simulation/
│   ├── engine.py              # 单层网络引擎
│   ├── engine_dual.py          # 双层网络引擎
│   ├── agents.py               # 数学模型智能体
│   ├── llm_agents.py           # LLM 驱动智能体
│   ├── llm_agents_dual.py      # LLM 驱动智能体(双层)
│   ├── knowledge_evolution.py # 知识图谱驱动演化
│   ├── prediction.py           # 预测模型
│   ├── risk_alert.py          # 风险预警
│   ├── graph_parser_agent.py   # 图谱解析
│   └── analyst_agent.py        # 智库分析师
├── models/
│   └── schemas.py             # 数据模型（含向后兼容）
└── ...

frontend/
└── src/
    └── App.vue                # 主应用（含模式切换和预测面板）

docs/
└── dual_mode_design.md        # 本文档
```

---

## 三、已实现功能

### 3.1 双模式切换 ✅

**实现方式**:
- 模式通过 `SimulationParams.mode` 参数在启动推演时传递
- 前端使用本地状态管理模式切换UI
- 后端 `SimulationEngine` 根据模式参数初始化不同策略

**启动参数示例（沙盘模式）**:
```json
{
  "mode": "sandbox",
  "initial_negative_spread": 0.3,
  "cocoon_strength": 0.5,
  "population_size": 200,
  "use_llm": true
}
```

**启动参数示例（新闻模式）**:
```json
{
  "mode": "news",
  "init_distribution": {
    "believe_negative": 0.30,
    "believe_positive": 0.15,
    "neutral": 0.55
  },
  "cocoon_strength": 0.5,
  "population_size": 200,
  "use_llm": true
}
```

### 3.2 知识驱动演化 ✅

**实体影响力计算**:
```python
def compute_entity_influence(entity, agent, cocoon_strength):
    # 基础影响力（基于重要性）
    base_impact = (6 - entity.importance) / 5  # 1.0 ~ 0.2

    # 人设调节
    if "意见领袖" in agent.persona:
        base_impact *= authority_factor
    elif "怀疑论者" in agent.persona:
        base_impact *= 0.5

    # 茧房效应
    cocoon_effect = cocoon_strength * agent.opinion * 0.1

    return base_impact + cocoon_effect
```

**关系立场映射**:
- 支持/oppose/neutral 三种立场
- 影响观点演化方向

### 3.3 预测区间 ✅

**API 接口**:
- `GET /api/prediction/update` - 获取预测结果
- `GET /api/prediction/timeline` - 获取预测轨迹

**输出格式**:
```json
{
  "negative_belief_rate": {
    "expected": 0.52,
    "optimistic": 0.38,
    "pessimistic": 0.66,
    "confidence": 0.95
  },
  "risk_level": "high",
  "strategies": [...]
}
```

### 3.4 风险预警 ✅

**风险等级**:
| 等级 | 条件 | 含义 |
|------|------|------|
| critical | 误信率>50% 或 极化>0.8 | 危急 |
| high | 误信率>35% 或 极化>0.6 | 高危 |
| medium | 误信率>20% 或 极化>0.4 | 中等 |
| low | 其他 | 低风险 |

### 3.5 干预建议 ✅

**策略类型**:
| 类型 | 说明 | 适用场景 |
|------|------|----------|
| response | 官方权威回应 | 负面信念传播初期 |
| prevent | 预防传播 | 预测负面信念快速扩散 |
| amplify | 放大正面信念 | 正面信念有传播基础 |
| depolarize | 缓解极化 | 群体严重分裂 |
| multi | 多策略组合 | 复杂舆情 |

### 3.6 快速注入模式 ✅

**功能**: 跳过知识图谱解析，秒级响应事件注入

**API 参数**:
```json
{
  "content": "事件内容",
  "source": "public",
  "skip_parse": true
}
```

**响应时间对比**:
| 模式 | 响应时间 |
|------|----------|
| 完整解析 | 10-60秒 |
| 快速注入 | 1-2秒 |

---

## 四、数据模型

### 4.1 SimulationMode 枚举

```python
class SimulationMode(Enum):
    """推演模式"""
    SANDBOX = "sandbox"  # 沙盘推演模式
    NEWS = "news"        # 新闻推演模式
```

### 4.2 SimulationParams 核心字段

```python
class SimulationParams(BaseModel):
    """推演参数"""
    mode: str = "sandbox"
    cocoon_strength: float = 0.5
    response_delay: int = 10          # 权威回应延迟
    initial_negative_spread: float = 0.3
    population_size: int = 200
    use_llm: bool = True
    use_dual_network: bool = True
    init_distribution: Optional[Dict] = None  # 新闻模式专用
    
    # 向后兼容
    @model_validator(mode='before')
    def map_legacy_fields(cls, data):
        if 'debunk_delay' in data:
            data['response_delay'] = data.pop('debunk_delay')
        if 'initial_rumor_spread' in data:
            data['initial_negative_spread'] = data.pop('initial_rumor_spread')
        return data
```

### 4.3 SimulationState 核心字段

```python
class SimulationState(BaseModel):
    """推演状态"""
    step: int
    agents: List[Agent]
    
    # 核心指标（新命名）
    negative_belief_rate: float
    positive_belief_rate: float
    avg_opinion: float
    polarization_index: float
    silence_rate: float
    
    # 双层网络指标
    public_negative_rate: float
    private_negative_rate: float
    num_communities: int
    num_influencers: int
    
    def to_dict(self):
        """输出时同时返回新旧字段名"""
        d = self.model_dump()
        # 向后兼容：同时返回旧字段名
        d['rumor_spread_rate'] = self.negative_belief_rate
        d['truth_acceptance_rate'] = self.positive_belief_rate
        return d
```

---

## 五、核心算法

### 5.1 真实分布锚定

```python
def apply_init_distribution(population, distribution):
    """应用真实分布锚定"""
    n = population.size
    opinions = np.zeros(n)

    believe_negative_count = int(n * distribution["believe_negative"])
    believe_positive_count = int(n * distribution["believe_positive"])

    # 误信: opinion ∈ [-0.8, -0.3]
    opinions[:believe_negative_count] = np.random.uniform(-0.8, -0.3, believe_negative_count)

    # 正确认知: opinion ∈ [0.3, 0.8]
    start = believe_negative_count
    end = start + believe_positive_count
    opinions[start:end] = np.random.uniform(0.3, 0.8, believe_positive_count)

    # 中立: opinion ∈ [-0.2, 0.2]
    opinions[end:] = np.random.uniform(-0.2, 0.2, n - end)

    population.opinions = opinions
```

### 5.2 预测轨迹计算

```python
def compute_prediction_trajectory(history, steps=10):
    """计算预测轨迹"""
    # 线性外推
    recent = history[-5:]
    slope = (recent[-1] - recent[0]) / len(recent)

    # 历史波动
    std = np.std(history)

    trajectory = {
        "expected": [],
        "optimistic": [],
        "pessimistic": []
    }

    current = history[-1]
    for i in range(steps):
        expected = current + slope * (i + 1)
        margin = 1.96 * std * np.sqrt(i + 1)  # 置信区间扩大

        trajectory["expected"].append(expected)
        trajectory["optimistic"].append(max(0, expected - margin))
        trajectory["pessimistic"].append(min(1, expected + margin))

    return trajectory
```

---

## 六、前端界面

### 6.1 模式选择器

```
┌─────────────────────────────────────────────────────────┐
│  推演模式:  [沙盘推演]  [新闻推演]                        │
└─────────────────────────────────────────────────────────┘
```

### 6.2 新闻模式配置

```
┌─────────────────────────────────────────────────────────┐
│  真实分布锚定:                                           │
│  误信: [30]%  正确认知: [15]%  中立: [55]%               │
└─────────────────────────────────────────────────────────┘
```

### 6.3 预测面板

```
┌─────────────────────────────────────────────────────────┐
│  风险等级: 🚨 高危                                       │
│                                                         │
│  误信率预测:                                             │
│  期望: 52%  乐观: 38%  悲观: 66%                         │
│                                                         │
│  建议干预时机: 第8步                                     │
│  推荐策略: 官方权威回应 (预计降低15-25%)                  │
└─────────────────────────────────────────────────────────┘
```

---

## 七、使用流程

### 7.1 沙盘模式流程

1. 选择"沙盘推演"模式
2. 设置推演参数（茧房强度、权威回应延迟等）
3. 点击"开始推演"
4. 观察观点演化
5. 调整参数，对比不同场景

### 7.2 新闻模式流程

1. 选择"新闻推演"模式
2. 输入真实舆情分布
3. （可选）注入事件
4. 点击"开始推演"
5. 观察预测轨迹和风险预警
6. 参考干预建议决策
7. 生成智库专报

---

## 八、性能优化

### 8.1 LLM 并发控制

| Agent 数量 | 推荐并发数 |
|------------|-----------|
| 50         | 25        |
| 100        | 50        |
| 200        | 100       |

### 8.2 快速注入

推演中事件注入建议使用快速模式，避免与推演LLM调用竞争资源。

---

## 九、向后兼容策略

### 9.1 API 兼容

所有API同时接受新旧参数名：

```python
# 新参数名优先，旧参数名兼容
response_delay = params.get('response_delay') or params.get('debunk_delay', 10)
initial_negative_spread = params.get('initial_negative_spread') or params.get('initial_rumor_spread', 0.3)
```

### 9.2 响应包含新旧字段

```json
{
  "negative_belief_rate": 0.45,
  "positive_belief_rate": 0.15,
  "rumor_spread_rate": 0.45,
  "truth_acceptance_rate": 0.15
}
```

---

## 十、后续优化方向

| 方向 | 说明 | 优先级 |
|------|------|--------|
| 蒙特卡洛预测 | 提升预测准确性 | 中 |
| 实时数据接入 | 对接舆情监测API | 低 |
| 多事件关联 | 支持多事件联合推演 | 低 |
| 干预模拟 | 在推演中模拟干预效果 | 中 |
