# 语义重构映射表

> 目标：将特定的"谣言/辟谣"语义抽象为通用的"负面信念/权威回应"语义，使系统适用于各种新闻事件场景。

## 一、核心概念映射

| UI文案 | 内部命名 | 英文标识 | 说明 |
|--------|----------|----------|------|
| 误信 | 负面信念 | `negative_belief` | 用户相信的错误/有害信息 |
| 正确认知 | 正面信念 | `positive_belief` | 官方正确/有益信息 |
| 权威回应 | 权威回应 | `authority_response` | 官方发布的纠正信息 |

### 适用场景示例

| 场景 | 负面信念 | 正面信念 | 权威回应 |
|------|----------|----------|----------|
| 谣言传播 | 谣言 | 真相 | 辟谣信息 |
| 争议新闻 | 片面解读 | 完整事实 | 官方澄清 |
| 舆情事件 | 情绪化观点 | 理性分析 | 权威解读 |
| 公共危机 | 恐慌信息 | 指导信息 | 官方通报 |
| 学术争议 | 误导性结论 | 研究共识 | 权威声明 |

---

## 二、字段命名映射

### 2.1 数据模型字段

| 旧命名 | 新命名 | 类型 | 说明 |
|--------|--------|------|------|
| `rumor_spread_rate` | `negative_belief_rate` | float | 负面信念传播率 |
| `truth_acceptance_rate` | `positive_belief_rate` | float | 正面信念接受率 |
| `initial_rumor_spread` | `initial_negative_spread` | float | 初始负面传播率参数 |
| `exposed_to_rumor` | `exposed_to_negative` | bool | 是否接触过负面信息 |
| `exposed_to_truth` | `exposed_to_positive` | bool | 是否接触过正面信息 |
| `public_rumor_rate` | `public_negative_rate` | float | 公域网络负面信念率 |
| `private_rumor_rate` | `private_negative_rate` | float | 私域网络负面信念率 |
| `public_truth_rate` | `public_positive_rate` | float | 公域网络正面信念率 |
| `private_truth_rate` | `private_positive_rate` | float | 私域网络正面信念率 |

### 2.2 干预机制字段

| 旧命名 | 新命名 | 类型 | 说明 |
|--------|--------|------|------|
| `debunk_delay` | `response_delay` | int | 权威回应延迟步数 |
| `debunked` | `responded` | bool | 权威回应是否已发布 |
| `debunk_credibility` | `response_credibility` | float | 权威回应可信度 |
| `debunk_released` | `response_released` | bool | 权威回应是否已发布（方法参数） |

### 2.3 Agent 属性字段

| 旧命名 | 新命名 | 类型 | 说明 |
|--------|--------|------|------|
| `rumor_susceptibility` | `negative_susceptibility` | float | 对负面信念的易感性 |
| `rumor_believers` | `negative_believers` | array | 负面信念者列表 |
| `pro_rumor_ratio` | `pro_negative_ratio` | float | 倾向负面信念的比例 |

### 2.4 分布锚定字段

| 旧命名 | 新命名 | 说明 |
|--------|--------|------|
| `believe_rumor` | `believe_negative` | 相信负面信念的比例 |
| `believe_truth` | `believe_positive` | 相信正面信念的比例 |

---

## 三、参数命名映射

### 3.1 API 参数

| 旧参数 | 新参数 | 默认值 | 说明 |
|--------|--------|--------|------|
| `initial_rumor_spread` | `initial_negative_spread` | 0.3 | 初始负面传播率 |
| `debunk_delay` | `response_delay` | 10 | 权威回应延迟步数 |
| `debunk_credibility` | `response_credibility` | 0.7 | 权威回应可信度 |

### 3.2 配置参数

| 旧参数 | 新参数 | 说明 |
|--------|--------|------|
| `rumor_critical_threshold` | `negative_critical_threshold` | 负面信念临界阈值 |
| `rumor_rising_threshold` | `negative_rising_threshold` | 负面信念上升阈值 |

---

## 四、前端文案映射

### 4.1 标签文案

| 旧文案 | 新文案 | 位置 |
|--------|--------|------|
| 谣言传播率 | 误信率 | KPI卡片、图表图例 |
| 真相接受率 | 正确认知率 | KPI卡片、图表图例 |
| 初始谣言传播率 | 初始误信率 | 参数面板 |
| 辟谣延迟 | 权威回应延迟 | 参数面板 |
| 官方辟谣 | 官方回应 | 干预按钮 |
| 相信谣言 | 误信 | 分布滑块、观点标签 |
| 相信真相 | 正确认知 | 分布滑块、观点标签 |

### 4.2 描述文案

| 旧文案 | 新文案 |
|--------|--------|
| 当前相信谣言的人群比例...辟谣后应逐渐下降 | 当前误信的人群比例，权威回应后应逐渐下降 |
| 辟谣可能与强信念冲突，反而强化谣言 | 权威回应可能与深层信念冲突，产生逆火效应 |
| 谣言传播多久后发布辟谣 | 负面信息传播多久后发布权威回应 |

---

## 五、风险规则映射

| 旧规则名 | 新规则名 | 触发条件 |
|----------|----------|----------|
| `rumor_critical` | `negative_critical` | 负面信念率 > 0.7 |
| `rumor_high` | `negative_high` | 负面信念率 > 0.5 |
| `rumor_rising` | `negative_rising` | 负面信念率连续上升 |
| `debunk_ineffective` | `response_ineffective` | 权威回应后效果不显著 |

---

## 六、方法/函数命名映射

| 旧方法 | 新方法 | 说明 |
|--------|--------|------|
| `_release_debunking()` | `_release_authority_response()` | 发布权威回应 |
| `_analyze_debunk_effect()` | `_analyze_response_effect()` | 分析回应效果 |
| `_debunk_with_backfire()` | `_response_with_backfire()` | 带逆火效应的回应 |

---

## 七、向后兼容策略

实现完整的向后兼容，确保旧代码和API调用不受影响。

### 7.1 数据模型层（schemas.py）

```python
class SimulationParams(BaseModel):
    # 新字段名
    response_delay: int = 10
    initial_negative_spread: float = 0.3
    
    @model_validator(mode='before')
    def map_legacy_fields(cls, data):
        # 旧参数名映射到新参数名
        if 'debunk_delay' in data:
            data['response_delay'] = data.pop('debunk_delay')
        if 'initial_rumor_spread' in data:
            data['initial_negative_spread'] = data.pop('initial_rumor_spread')
        return data
```

### 7.2 API层（app.py）

```python
# 同时接受新旧参数名
response_delay = params.get('response_delay') or params.get('debunk_delay', 10)
initial_negative_spread = params.get('initial_negative_spread') or params.get('initial_rumor_spread', 0.3)
```

### 7.3 响应输出

```python
def to_dict(self):
    d = self.model_dump()
    # 同时返回新旧两种字段名
    d['rumor_spread_rate'] = self.negative_belief_rate
    d['truth_acceptance_rate'] = self.positive_belief_rate
    d['public_rumor_rate'] = self.public_negative_rate
    d['private_rumor_rate'] = self.private_negative_rate
    return d
```

---

## 八、向后兼容对照表

### 请求参数兼容

| 新参数名 | 旧参数名 | 均可使用 |
|----------|----------|----------|
| `response_delay` | `debunk_delay` | ✅ |
| `initial_negative_spread` | `initial_rumor_spread` | ✅ |
| `response_credibility` | `debunk_credibility` | ✅ |
| `believe_negative` | `believe_rumor` | ✅ |
| `believe_positive` | `believe_truth` | ✅ |

### 响应字段兼容

响应同时包含新旧字段名：

```json
{
  "negative_belief_rate": 0.45,
  "rumor_spread_rate": 0.45,
  "positive_belief_rate": 0.15,
  "truth_acceptance_rate": 0.15
}
```

---

## 九、实施顺序

重构按以下顺序进行，确保每一步都可验证：

1. **测试先行**：编写覆盖核心功能的测试文件
2. **后端模型**：重构 schemas.py 数据模型（添加兼容层）
3. **后端引擎**：重构 engine.py, engine_dual.py（内部变量名）
4. **后端Agent**：重构 agents.py, llm_agents*.py
5. **后端模型**：重构 math_model_enhanced.py（step方法参数）
6. **后端模块**：重构 prediction.py, risk_alert.py, analyst_agent.py
7. **后端API**：重构 app.py，确保API兼容
8. **前端**：重构 App.vue 字段和文案
9. **文档**：更新 docs/
10. **验证**：运行测试确保重构正确

---

## 十、重构陷阱与注意事项

### 10.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 参数名报错 | 函数定义改为新名，但调用处未同步 | 全局搜索旧参数名 |
| 字段双重定义 | 同时定义新旧字段 | 使用 model_validator 映射 |
| 响应缺少旧字段 | 忘记添加 to_dict 兼容 | 检查 to_dict 方法 |

### 10.2 检查清单

- [ ] 所有函数参数名已同步
- [ ] 所有方法调用处已更新
- [ ] API同时接受新旧参数名
- [ ] 响应同时返回新旧字段名
- [ ] 前端文案已更新
- [ ] 测试全部通过

---

## 十一、预期效果

重构后，系统具有以下优势：

1. **通用性**：适用于谣言、争议新闻、舆情事件等多种场景
2. **可扩展**：便于添加新的信息类型和干预机制
3. **向后兼容**：旧代码和API调用无需修改
4. **文档一致**：UI文案与内部命名更贴合用户认知
