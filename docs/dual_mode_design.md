# 信息茧房推演系统 v2.0 设计方案

> 双模式架构：沙盘推演模式 + 新闻推演模式

## 开发状态

| 阶段 | 功能 | 状态 |
|------|------|------|
| Phase 1 | 知识驱动演化 + 实体影响力 | ✅ 已完成 |
| Phase 2 | 预测区间 + 风险预警 + 事件注入 | ✅ 已完成 |
| Phase 3 | 完整新闻模式 + 干预建议 | ✅ 已完成 |
| Phase 4 | 双模式整合 + 文档完善 | ✅ 已完成 |

---

## 一、概述

### 1.1 设计背景

当前系统存在一个**核心断层**：

```
新闻注入 → 仅解析为知识图谱 → 未参与观点演化
谣言定义 → 仅是"初始观点分布"，无具体内容
辟谣机制 → 仅是时间触发，无具体内容
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
| 干预锚定 | 辟谣内容具体化，可设置干预时机和内容 | ✅ |

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
│  │   (Rumor Sandbox)   │    │   (News Simulation)     │   │
│  ├─────────────────────┤    ├─────────────────────────┤   │
│  │ 目标：研究传播机制    │    │ 目标：预测现实演进       │   │
│  │                     │    │                           │   │
│  │ ·抽象谣言模型        │    │ ·真实新闻事件             │   │
│  │ ·参数可调           │    │ ·历史节点标注               │   │
│  │ ·假设驱动           │    │ ·事实锚定 + 预测           │   │
│  │                     │    │                           │   │
│  │ 谣言内容：模板化     │    │ 谣言内容：新闻文本解析     │   │
│  │  "A事件导致B"       │    │  关联实体、立场、证据     │   │
│  │                     │    │                           │   │
│  │ Agent初始分布       │    │ Agent初始分布             │   │
│  │  按 initial_        │    │  按真实舆情采样           │   │
│  │  rumor_spread       │    │  或问卷数据               │   │
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
│   ├── engine.py              # 单层网络引擎（保留兼容）
│   ├── engine_dual.py         # 双层网络引擎（保留兼容）
│   ├── knowledge_evolution.py # [已实现] 知识图谱驱动演化
│   ├── prediction.py          # [已实现] 预测模型
│   ├── risk_alert.py          # [已实现] 风险预警
│   ├── graph_parser_agent.py  # 图谱解析（增强）
│   └── ...
├── models/
│   └── schemas.py             # 数据模型（已扩展）
└── ...

frontend/
└── src/
    ├── App.vue                # [已改造] 增加模式切换和预测面板
    └── components/
        └── PredictionChart.vue # [已实现] 预测轨迹图

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

**前端交互**:
- 沙盘/新闻模式选择器（`App.vue:149-163`）
- 新闻模式支持真实分布锚定输入

**启动参数**:
```json
{
  "mode": "news",
  "init_distribution": {
    "believe_rumor": 0.30,
    "believe_truth": 0.15,
    "neutral": 0.55
  }
}
```

**后端处理**:
```python
# backend/simulation/engine.py
self.mode = SimulationMode(mode) if isinstance(mode, str) else mode

# 新闻模式应用真实分布锚定
if self.mode == SimulationMode.NEWS and self.init_distribution:
    self._apply_init_distribution()
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
- `GET /api/prediction` - 获取预测结果
- `GET /api/prediction/trajectory` - 获取预测轨迹

**输出格式**:
```json
{
  "prediction": {
    "rumor_spread_rate": {
      "expected": 0.52,
      "optimistic": 0.38,
      "pessimistic": 0.66,
      "confidence": 0.95
    }
  },
  "risk_level": "high",
  "strategies": [...]
}
```

### 3.4 风险预警 ✅

**风险等级**:
| 等级 | 条件 | 含义 |
|------|------|------|
| critical | 谣言率>50% 或 极化>0.8 | 危急 |
| high | 谣言率>35% 或 极化>0.6 | 高危 |
| medium | 谣言率>20% 或 极化>0.4 | 中等 |
| low | 其他 | 低风险 |

### 3.5 干预建议 ✅

**策略类型**:
| 类型 | 说明 | 适用场景 |
|------|------|----------|
| debunk | 官方辟谣 | 谣言传播初期 |
| prevent | 预防传播 | 预测快速扩散 |
| amplify | 放大真相 | 真相有传播基础 |
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

### 4.2 NewsEvent 新闻事件结构

```python
@dataclass
class NewsEvent:
    """新闻事件结构"""
    content: str                    # 新闻原文
    source: str = "public"          # 来源

    # 知识图谱
    entities: List[Dict] = field(default_factory=list)
    relations: List[Dict] = field(default_factory=list)

    # 分析结果
    sentiment: str = "中性"
    credibility: str = "不确定"

    # 辟谣信息
    debunk_content: str = ""
    debunk_delay: int = 10

    # 运行时计算
    entity_impacts: Dict[str, float] = field(default_factory=dict)
    relation_stance: Dict[str, str] = field(default_factory=dict)
```

### 4.3 PredictionInterval 预测区间

```python
@dataclass
class PredictionInterval:
    """预测区间"""
    expected: float = 0.0          # 期望值
    optimistic: float = 0.0        # 乐观场景
    pessimistic: float = 0.0       # 悲观场景
    confidence: float = 0.95       # 置信度
```

---

## 五、核心算法

### 5.1 真实分布锚定

```python
def apply_init_distribution(population, distribution):
    """应用真实分布锚定"""
    n = population.size
    opinions = np.zeros(n)

    belief_rumor_count = int(n * distribution["believe_rumor"])
    belief_truth_count = int(n * distribution["believe_truth"])

    # 相信谣言: opinion ∈ [-0.8, -0.3]
    opinions[:belief_rumor_count] = np.random.uniform(-0.8, -0.3, belief_rumor_count)

    # 相信真相: opinion ∈ [0.3, 0.8]
    start = belief_rumor_count
    end = start + belief_truth_count
    opinions[start:end] = np.random.uniform(0.3, 0.8, belief_truth_count)

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

### 5.3 干预时机建议

```python
def recommend_intervention(current_state, prediction):
    """推荐干预时机"""
    # 检查预测风险
    if prediction.pessimistic_rumor_rate > 0.6:
        return {
            "recommended_step": current_state.step + 2,
            "urgency": "critical"
        }

    # 计算干预效果曲线
    best_step = None
    best_effect = 0

    for step in range(current_state.step, current_state.step + 15):
        # 模拟干预效果
        effect = simulate_intervention_impact(step, current_state)
        if effect > best_effect:
            best_effect = effect
            best_step = step

    return {
        "recommended_step": best_step,
        "expected_effectiveness": best_effect
    }
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
│  相信谣言: [30]%  相信真相: [15]%  中立: [55]%           │
└─────────────────────────────────────────────────────────┘
```

### 6.3 预测面板

```
┌─────────────────────────────────────────────────────────┐
│  风险等级: 🚨 高危                                       │
│                                                         │
│  谣言传播率预测:                                         │
│  期望: 52%  乐观: 38%  悲观: 66%                         │
│                                                         │
│  建议干预时机: 第8步                                     │
│  推荐策略: 官方辟谣 (预计降低15-25%)                     │
└─────────────────────────────────────────────────────────┘
```

### 6.4 预测轨迹图

```
谣言传播率
  │
70% ┤              ╭─── 悲观场景
    │         ╭───╯
50% ┤    ╭───╯    ╭─── 期望场景
    │╭──╯    ╭───╯
30% ┤╯  ╭───╯    ╭─── 乐观场景
    │╭─╯    ╭───╯
10% ┴┴─────┴────────────────────→
    当前  5步   10步
```

---

## 七、使用流程

### 7.1 沙盘模式流程

1. 选择"沙盘推演"模式
2. 设置推演参数（茧房强度、辟谣延迟等）
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

### 8.3 预测缓存

预测结果每10步更新一次，减少计算开销。

---

## 九、后续优化方向

| 方向 | 说明 | 优先级 |
|------|------|--------|
| 蒙特卡洛预测 | 提升预测准确性 | 中 |
| 实时数据接入 | 对接舆情监测API | 低 |
| 多事件关联 | 支持多事件联合推演 | 低 |
| 干预模拟 | 在推演中模拟干预效果 | 中 |
