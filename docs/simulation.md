# 推演机制详解

## 概述

觉测·洞鉴支持两种推演模式：数学模型模式和 LLM 驱动模式。两者都模拟群体观点演化，但实现机制和适用场景不同。

## 观点表示

每个智能体（Agent）持有 **观点值**（opinion），范围为 `[-1, 1]`：

```
-1 ─────────────────────────────────────────── 0 ─────────────────────────────────────────── 1
  │                                        │                                        │
  │                                        │                                        │
完全相信谣言                              中立                                   完全相信真相
(Rumor Believer)                        (Neutral)                             (Truth Acceptor)
```

## 数学模型模式

### 核心机制

基于社会心理学理论，通过公式计算观点演化：

```
new_opinion = f(social_influence, cocoon_effect, debunking, polarization)
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

### 增强版参数

| 参数 | 范围 | 说明 |
|------|------|------|
| debunk_credibility | 0~1 | 辟谣来源可信度 |
| authority_factor | 0~1 | 权威影响力系数 |
| backfire_strength | 0~1 | 逆火效应强度 |
| silence_threshold | 0~1 | 沉默阈值 |
| polarization_factor | 0~1 | 群体极化系数 |
| echo_chamber_factor | 0~1 | 回音室效应系数 |

## LLM 驱动模式

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

当前信息环境：
- 谣言传播率: {rumor_rate}%
- 真相接受率: {truth_rate}%
- 你收到的信息: {received_news}

你当前的观点: {current_opinion} (-1到1，-1=完全相信谣言，1=完全相信真相)
你的信念强度: {belief_strength} (越高越难改变)
你的易感性: {susceptibility} (越高越容易受他人影响)

邻居们的观点: {neighbor_opinions}

请决定：
1. 你的新观点是什么？（考虑邻居影响和你的信念强度）
2. 你的情绪状态是什么？
3. 你会采取什么行动？（转发/评论/观望/辟谣）
4. 如果评论，你会说什么？
```

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

## 观点演化可视化

### 观点分布直方图

```
人数
  │
  │       ■■■
  │    ■■■■■■■■■■■
  │ ■■■■■■■■■■■■■■■■■■■
  │■■■■■■■■■■■■■■■■■■■■■■
  └────────────────────
   -1  -0.6  -0.2  0.2  0.6   1
    │← 谣言 →│    │← 真相 →│
```

- 红色区域：相信谣言 (opinion < -0.2)
- 橙色区域：中立 (-0.2 ≤ opinion ≤ 0.2)
- 绿色区域：相信真相 (opinion > 0.2)

### 趋势曲线

```
指标值
  │
1.0 ┤                    ╭──── 真相接受率
    │               ╭──╯
0.8 ┤          ╭──╯
    │     ╭──╯     ╭────── 极化指数
0.6 ┤───╯     ╭──╯    ╰────
    │         │
0.4 ┤         ╰──────────────
    │
0.2 ┤
    │╭────────────────────────
0.0 ┴╯────────────────────────
    └─────────┬──────────────→
      0       10      20      30  步数
              ↑
           辟谣发布
```

## 对比：数学模型 vs LLM 驱动

| 维度 | 数学模型 | LLM 驱动 |
|------|----------|----------|
| 速度 | 快（毫秒级/步） | 慢（秒级/步，需API调用） |
| 决策可解释性 | 公式透明 | Prompt + Response |
| 行为多样性 | 有限 | 丰富（LLM 生成） |
| 适用场景 | 参数探索、大规模模拟 | 深度分析、专报生成 |
| 成本 | 低 | 高（API 调用费用） |
| 可复现性 | 高 | 中（LLM 输出有随机性） |

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

### 生产部署

- 使用双层网络（use_dual_network: true）
- 根据服务器性能调整 max_concurrent
- 考虑使用本地 LLM（如 Ollama）降低成本
