# 语义重构映射表

> 目标：将特定的"谣言/辟谣"语义抽象为通用的"负面信念/权威回应"语义，使系统适用于各种新闻事件场景。

## 一、核心概念映射

| 原概念 | 新概念 | 英文命名 | 说明 |
|--------|--------|----------|------|
| 谣言 | 负面信念 | `negative_belief` | 用户相信的错误/有害信息 |
| 真相 | 正面信念 | `positive_belief` | 官方正确/有益信息 |
| 辟谣 | 权威回应 | `authority_response` | 官方发布的纠正信息 |
| 信谣言 | 误信 | `believe_negative` | 相信负面信息的状态 |
| 信真相 | 正确认知 | `believe_positive` | 相信正面信息的状态 |
| 中立 | 未表态/中立 | `neutral` | 未明确表态的状态 |

---

## 二、字段命名映射

### 2.1 数据模型字段（SimulationState / Agent）

| 原命名 | 新命名 | 类型 | 说明 |
|--------|--------|------|------|
| `rumor_spread_rate` | `negative_belief_rate` | float | 负面信念传播率 |
| `truth_acceptance_rate` | `positive_belief_rate` | float | 正面信念接受率 |
| `initial_rumor_spread` | `initial_negative_spread` | float | 初始负面传播率参数 |
| `exposed_to_rumor` | `exposed_to_negative` | bool | 是否接触过负面信息 |
| `public_rumor_rate` | `public_negative_rate` | float | 公域网络负面信念率 |
| `private_rumor_rate` | `private_negative_rate` | float | 私域网络负面信念率 |
| `pro_rumor_ratio` | `pro_negative_ratio` | float | 倾向负面信念的比例 |
| `believe_rumor` | `believe_negative` | float | 相信负面信念的比例 |
| `believe_truth` | `believe_positive` | float | 相信正面信念的比例 |

### 2.2 干预机制字段

| 原命名 | 新命名 | 类型 | 说明 |
|--------|--------|------|------|
| `debunk_delay` | `response_delay` | int | 权威回应延迟步数 |
| `debunked` | `responded` | bool | 权威回应是否已发布 |
| `debunk_credibility` | `response_credibility` | float | 权威回应可信度 |
| `debunk_effectiveness` | `response_effectiveness` | float | 权威回应效果 |

### 2.3 Agent 属性字段

| 原命名 | 新命名 | 类型 | 说明 |
|--------|--------|------|------|
| `rumor_susceptibility` | `negative_susceptibility` | float | 对负面信念的易感性 |
| `rumor_believers` | `negative_believers` | array | 负面信念者列表 |

### 2.4 统计历史字段

| 原命名 | 新命名 | 说明 |
|--------|--------|------|
| `trendHistory.rumorRates` | `trendHistory.negativeRates` | 负面信念率历史 |
| `trendHistory.publicRumorRates` | `trendHistory.publicNegativeRates` | 公域负面信念率历史 |
| `trendHistory.privateRumorRates` | `trendHistory.privateNegativeRates` | 私域负面信念率历史 |

---

## 三、参数命名映射

### 3.1 API 参数

| 原参数 | 新参数 | 默认值 | 说明 |
|--------|--------|--------|------|
| `initial_rumor_spread` | `initial_negative_spread` | 0.3 | 初始负面传播率 |
| `debunk_delay` | `response_delay` | 10 | 权威回应延迟步数 |
| `debunk_credibility` | `response_credibility` | 0.7 | 权威回应可信度 |

### 3.2 配置参数

| 原参数 | 新参数 | 说明 |
|--------|--------|------|
| `rumor_critical_threshold` | `negative_critical_threshold` | 负面信念临界阈值 |
| `rumor_rising_threshold` | `negative_rising_threshold` | 负面信念上升阈值 |

---

## 四、前端文案映射

### 4.1 标签文案

| 原文案 | 新文案 | 位置 |
|--------|--------|------|
| 谣言传播率 | 误信率 | KPI卡片、图表图例 |
| 真相接受率 | 正确认知率 | KPI卡片、图表图例 |
| 初始谣言传播率 | 初始误信率 | 参数面板 |
| 辟谣延迟 | 权威回应延迟 | 参数面板 |
| 官方辟谣 | 官方回应 | 干预按钮 |
| 相信谣言 | 误信 | 分布滑块、观点标签 |
| 相信真相 | 正确认知 | 分布滑块、观点标签 |
| 辟谣反而强化谣言 | 回应可能强化误信（逆火效应） | 提示信息 |

### 4.2 描述文案

| 原文案 | 新文案 |
|--------|--------|
| 当前相信谣言的人群比例...辟谣后应逐渐下降 | 当前误信的人群比例，权威回应后应逐渐下降 |
| 辟谣可能与强信念冲突，反而强化谣言 | 权威回应可能与深层信念冲突，产生逆火效应 |
| 谣言传播多久后发布辟谣 | 负面信息传播多久后发布权威回应 |

### 4.3 干预策略文案

| 原文案 | 新文案 |
|--------|--------|
| 权威辟谣 | 权威回应 |
| 预防性科普 | 预防性沟通 |
| 真相放大 | 正确信息推广 |
| 去极化沟通 | 跨群体对话 |
| 多渠道联动 | 多渠道联合干预 |

---

## 五、风险等级映射

| 原规则名 | 新规则名 | 触发条件 |
|----------|----------|----------|
| `rumor_critical` | `negative_critical` | 负面信念率 > 0.7 |
| `rumor_high` | `negative_high` | 负面信念率 > 0.5 |
| `rumor_rising` | `negative_rising` | 负面信念率连续上升 |
| `debunk_ineffective` | `response_ineffective` | 权威回应后效果不显著 |

---

## 六、方法/函数命名映射

| 原方法 | 新方法 | 说明 |
|--------|--------|------|
| `_release_debunking()` | `_release_authority_response()` | 发布权威回应 |
| `_analyze_debunk_effect()` | `_analyze_response_effect()` | 分析回应效果 |
| `_debunk_with_backfire()` | `_response_with_backfire()` | 带逆火效应的回应 |

---

## 七、向后兼容策略

为保持向后兼容，API 层面将同时支持新旧参数名：

```python
# app.py 中参数兼容处理
initial_negative_spread = params.get('initial_negative_spread') or params.get('initial_rumor_spread', 0.3)
response_delay = params.get('response_delay') or params.get('debunk_delay', 10)
```

前端优先使用新参数名，但向后兼容旧版 API。

---

## 八、实施顺序

1. **测试先行**：编写覆盖核心功能的测试文件
2. **后端模型**：重构 schemas.py 数据模型
3. **后端引擎**：重构 engine.py, engine_dual.py
4. **后端Agent**：重构 agents.py, llm_agents*.py
5. **后端模型**：重构 math_model_enhanced.py
6. **后端模块**：重构 prediction.py, risk_alert.py, analyst_agent.py, knowledge_evolution.py
7. **后端API**：重构 app.py，添加兼容层
8. **后端配置**：重构 persona_config.py
9. **前端**：重构 App.vue 字段和文案
10. **文档**：更新 docs/
11. **验证**：运行测试确保重构正确

---

## 九、预期效果

重构后，系统可适配以下场景：

| 场景 | 负面信念 | 正面信念 | 权威回应 |
|------|----------|----------|----------|
| 谣言传播 | 谣言 | 真相 | 辟谣信息 |
| 争议新闻 | 片面解读 | 完整事实 | 官方澄清 |
| 舆情事件 | 情绪化观点 | 理性分析 | 权威解读 |
| 公共危机 | 恐慌信息 | 指导信息 | 官方通报 |
| 学术争议 | 误导性结论 | 研究共识 | 权威声明 |
