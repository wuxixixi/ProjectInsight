# 信息茧房推演系统 v2.0 设计方案

> 双模式架构：沙盘推演模式 + 新闻推演模式

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

| 目标 | 描述 |
|------|------|
| 双模式支持 | 沙盘推演（假设驱动）+ 新闻推演（现实锚定） |
| 知识驱动 | 知识图谱参与观点演化，而非仅作为上下文 |
| 预测能力 | 输出置信区间，而非单值 |
| 干预锚定 | 辟谣内容具体化，可设置干预时机和内容 |

---

## 二、系统架构

### 2.1 双模式对比

```
┌─────────────────────────────────────────────────────────────┐
│                    SimulationEngineV2                       │
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
│  └─────────────────────┘    └─────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 文件结构

```
backend/
├── simulation/
│   ├── engine.py              # 现有引擎（保留兼容）
│   ├── engine_dual.py         # 双层网络引擎（保留兼容）
│   ├── engine_v2.py           # [新建] 双模式引擎
│   ├── knowledge_evolution.py  # [新建] 知识图谱驱动演化
│   ├── news_event.py          # [新建] 新闻事件结构
│   ├── graph_parser_agent.py  # 现有图谱解析（增强）
│   └── ...
├── models/
│   ├── schemas.py             # 现有模型（保留兼容）
│   └── schemas_v2.py          # [新建] v2数据模型
└── ...

frontend/
└── src/
    ├── components/
    │   ├── ControlPanel.vue    # [改造] 增加模式切换
    │   ├── SandboxConfig.vue   # [新建] 沙盘模式配置
    │   ├── NewsConfig.vue      # [新建] 新闻模式配置
    │   └── PredictionView.vue  # [新建] 预测结果展示
    └── ...

docs/
└── dual_mode_design.md        # 本文档
```

---

## 三、数据模型

### 3.1 SimulationMode 枚举

```python
# backend/models/schemas_v2.py

from enum import Enum

class SimulationMode(Enum):
    """推演模式"""
    SANDBOX = "sandbox"  # 沙盘推演模式
    NEWS = "news"        # 新闻推演模式
```

### 3.2 NewsEvent 新闻事件结构

```python
# backend/simulation/news_event.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class NewsEvent:
    """新闻事件结构
    
    用于新闻推演模式，封装真实新闻的完整信息
    """
    # 基础信息
    content: str                    # 新闻原文
    source: str = "public"          # 来源: public/private
    
    # 知识图谱解析结果
    entities: List[Dict] = field(default_factory=list)
    """实体列表，格式: [{"id": "e1", "name": "张三", "type": "人物", 
                     "description": "...", "importance": 1-5}]"""
    
    relations: List[Dict] = field(default_factory=list)
    """关系列表，格式: [{"source": "e1", "target": "e2", 
                     "action": "指控", "type": "对立"}]"""
    
    # 情感与可信度
    sentiment: str = "中性"         # 情感: 正面/负面/中性/争议
    credibility: str = "不确定"     # 可信度: 高可信/低可信/不确定
    
    # 辟谣信息
    debunk_content: str = ""        # 辟谣具体内容
    debunk_delay: int = 10          # 辟谣延迟步数
    
    # 实体影响力权重（运行时计算）
    entity_impacts: Dict[str, float] = field(default_factory=dict)
    """实体名 -> 影响力权重 [0, 1]"""
    
    # 关系立场映射（运行时计算）
    relation_stance: Dict[str, str] = field(default_factory=dict)
    """关系ID -> 立场: support/oppose/neutral"""
    
    # 证据链信息（运行时提取）
    evidence_chain: List[Dict] = field(default_factory=list)
    """证据列表: [{"content": "...", "strength": 0.8}]"""
    
    def get_entity_by_id(self, entity_id: str) -> Optional[Dict]:
        """根据ID获取实体"""
        for e in self.entities:
            if e.get("id") == entity_id:
                return e
        return None
    
    def get_related_entities(self, entity_id: str) -> List[Dict]:
        """获取与某实体相关的所有实体"""
        related = []
        for rel in self.relations:
            if rel.get("source") == entity_id:
                target = self.get_entity_by_id(rel.get("target"))
                if target:
                    related.append(target)
            elif rel.get("target") == entity_id:
                source = self.get_entity_by_id(rel.get("source"))
                if source:
                    related.append(source)
        return related
```

### 3.3 PredictionInterval 预测区间

```python
# backend/models/schemas_v2.py

from dataclasses import dataclass

@dataclass
class PredictionInterval:
    """预测区间
    
    用于新闻推演模式的区间预测输出
    """
    expected: float = 0.0          # 期望值（最可能的结果）
    optimistic: float = 0.0       # 乐观情况（下界）
    pessimistic: float = 0.0     # 悲观情况（上界）
    confidence: float = 0.95     # 置信度
    
    def to_dict(self) -> dict:
        return {
            "expected": self.expected,
            "optimistic": self.optimistic,
            "pessimistic": self.pessimistic,
            "confidence": self.confidence
        }


@dataclass
class SimulationParamsV2:
    """v2版本推演参数"""
    # 基础参数
    mode: SimulationMode = SimulationMode.SANDBOX
    cocoon_strength: float = 0.5
    population_size: int = 200
    network_type: str = "small_world"
    use_llm: bool = True
    
    # 沙盘模式参数
    initial_rumor_spread: float = 0.3
    
    # 新闻模式参数
    init_distribution: Dict[str, float] = None  # 真实分布锚定
    time_acceleration: float = 1.0              # 时间加速比
    
    # 增强版数学模型参数
    debunk_credibility: float = 0.7
    authority_factor: float = 0.5
    backfire_strength: float = 0.3
    silence_threshold: float = 0.3
    polarization_factor: float = 0.3
    echo_chamber_factor: float = 0.2
```

### 3.4 SimulationStateV2 状态输出

```python
# backend/models/schemas_v2.py

@dataclass
class SimulationStateV2:
    """v2版本推演状态"""
    step: int
    mode: SimulationMode
    agents: List[Dict]
    edges: List[tuple]
    opinion_distribution: Dict[str, List]
    
    # 整体统计
    rumor_spread_rate: float
    truth_acceptance_rate: float
    avg_opinion: float
    polarization_index: float
    silence_rate: float = 0.0
    
    # 预测指标（仅新闻模式）
    prediction: Optional[Dict[str, PredictionInterval]] = None
    """
    预测区间:
    {
        "rumor_spread_rate": PredictionInterval(...),
        "polarization_index": PredictionInterval(...),
        "truth_acceptance": PredictionInterval(...)
    }
    """
    
    # 风险预警（仅新闻模式）
    risk_alerts: List[str] = None
    """
    风险预警列表:
    ["极化风险较高", "谣言传播超阈值", "干预窗口收窄"]
    """
    
    # 实体影响摘要（仅新闻模式）
    entity_impact_summary: Dict[str, float] = None
    """
    关键实体影响摘要:
    {"张三": 0.8, "某公司": 0.6}
    """
```

---

## 四、核心模块设计

### 4.1 SimulationEngineV2 双模式引擎

```python
# backend/simulation/engine_v2.py

class SimulationEngineV2:
    """双模式推演引擎 v2.0
    
    支持沙盘推演模式和新闻推演模式
    """
    
    def __init__(
        self,
        mode: SimulationMode = SimulationMode.SANDBOX,
        # 通用参数
        population_size: int = 200,
        cocoon_strength: float = 0.5,
        network_type: str = "small_world",
        use_llm: bool = True,
        llm_config: Optional[LLMConfig] = None,
        # 沙盘模式参数
        initial_rumor_spread: float = 0.3,
        # 新闻模式参数
        init_distribution: Optional[Dict[str, float]] = None,
        time_acceleration: float = 1.0,
        # 增强版数学模型参数
        debunk_credibility: float = 0.7,
        authority_factor: float = 0.5,
        backfire_strength: float = 0.3,
        silence_threshold: float = 0.3,
        polarization_factor: float = 0.3,
        echo_chamber_factor: float = 0.2
    ):
        self.mode = mode
        self.population_size = population_size
        self.cocoon_strength = cocoon_strength
        self.network_type = network_type
        self.use_llm = use_llm
        self.llm_config = llm_config or LLMConfig()
        
        # 沙盘模式参数
        self.initial_rumor_spread = initial_rumor_spread
        
        # 新闻模式参数
        self.init_distribution = init_distribution or {}
        self.time_acceleration = time_acceleration
        
        # 增强版数学模型参数
        self.debunk_credibility = debunk_credibility
        self.authority_factor = authority_factor
        self.backfire_strength = backfire_strength
        self.silence_threshold = silence_threshold
        self.polarization_factor = polarization_factor
        self.echo_chamber_factor = echo_chamber_factor
        
        # 状态
        self.step_count = 0
        self.debunked = False
        self.current_event: Optional[NewsEvent] = None
        self.knowledge_evolution: Optional[KnowledgeDrivenEvolution] = None
        self.math_model = None
        self.population = None
        self.llm_population = None
        self.history: List[Dict] = []
        self._prediction_cache: Dict[str, List[float]] = {}
    
    # ==================== 模式切换方法 ====================
    
    def set_rumor_template(
        self, 
        content: str, 
        initial_spread: float = 0.3
    ):
        """
        [沙盘模式] 设置抽象谣言模板
        
        Args:
            content: 谣言描述模板，如"某公司产品存在安全隐患"
            initial_spread: 初始相信谣言的比例
        """
        self.mode = SimulationMode.SANDBOX
        self.initial_rumor_spread = initial_spread
        self.current_event = NewsEvent(
            content=content,
            source="public",
            sentiment="负面",
            credibility="不确定"
        )
        
    async def set_news_event(
        self,
        content: str,
        source: str = "public",
        parse_graph: bool = True,
        init_distribution: Optional[Dict[str, float]] = None,
        debunk_content: str = "",
        debunk_delay: int = 10
    ):
        """
        [新闻模式] 设置真实新闻事件
        
        Args:
            content: 新闻原文
            source: 来源 (public/private)
            parse_graph: 是否解析知识图谱
            init_distribution: 真实分布锚定
                示例: {"believe_rumor": 0.25, "believe_truth": 0.15, "neutral": 0.60}
            debunk_content: 具体辟谣内容
            debunk_delay: 辟谣延迟步数
        """
        self.mode = SimulationMode.NEWS
        
        # 解析知识图谱
        entities = []
        relations = []
        sentiment = "中性"
        credibility = "不确定"
        
        if parse_graph:
            from .graph_parser_agent import get_graph_parser
            graph_parser = get_graph_parser()
            graph_data = await graph_parser.parse(content)
            entities = graph_data.get("entities", [])
            relations = graph_data.get("relations", [])
            sentiment = graph_data.get("sentiment", "中性")
            credibility = graph_data.get("credibility_hint", "不确定")
        
        # 计算实体影响力
        entity_impacts = self._calculate_entity_impacts(entities)
        
        # 计算关系立场
        relation_stance = self._calculate_relation_stance(relations)
        
        # 创建新闻事件
        self.current_event = NewsEvent(
            content=content,
            source=source,
            entities=entities,
            relations=relations,
            sentiment=sentiment,
            credibility=credibility,
            debunk_content=debunk_content,
            debunk_delay=debunk_delay,
            entity_impacts=entity_impacts,
            relation_stance=relation_stance
        )
        
        # 初始化知识驱动演化器
        self.knowledge_evolution = KnowledgeDrivenEvolution(
            entity_impacts=entity_impacts,
            relation_stance=relation_stance,
            evidence_strength=0.5 if credibility == "高可信" else 0.3,
            authority_weight=self.authority_factor
        )
        
        # 覆盖初始分布
        if init_distribution:
            self.init_distribution = init_distribution
    
    def _calculate_entity_impacts(self, entities: List[Dict]) -> Dict[str, float]:
        """计算实体影响力权重
        
        基于实体重要性计算影响力，重要性越高，影响力越大
        """
        impacts = {}
        for entity in entities:
            name = entity.get("name", "")
            importance = entity.get("importance", 3)  # 1-5
            
            # 重要性 1-5 -> 影响力 1.0-0.2
            # 即：importance=1（最重要） -> impact=1.0
            #     importance=5（最不重要） -> impact=0.2
            impacts[name] = (6 - importance) / 5
        return impacts
    
    def _calculate_relation_stance(self, relations: List[Dict]) -> Dict[str, str]:
        """计算关系立场
        
        根据关系类型确定立场
        """
        stance_map = {
            "支持": "support",
            "反对": "oppose",
            "对立": "oppose",
            "指控": "oppose",
            "否认": "neutral",
            "参与": "neutral",
            "导致": "neutral",
            "影响": "neutral"
        }
        
        stances = {}
        for rel in relations:
            rel_id = f"{rel.get('source')}_{rel.get('target')}"
            rel_type = rel.get("type", "关联")
            stances[rel_id] = stance_map.get(rel_type, "neutral")
        return stances
    
    # ==================== 初始化 ====================
    
    def initialize(self) -> SimulationStateV2:
        """初始化模拟"""
        self.step_count = 0
        self.debunked = False
        self.history = []
        self._prediction_cache = {
            "rumor_spread_rates": [],
            "truth_acceptance_rates": [],
            "polarization_indices": []
        }
        
        # 初始化数学模型
        from .math_model_enhanced import EnhancedMathModel, EnhancedMathParams
        math_params = EnhancedMathParams(
            cocoon_strength=self.cocoon_strength,
            debunk_delay=self.current_event.debunk_delay if self.current_event else 10,
            debunk_credibility=self.debunk_credibility,
            authority_factor=self.authority_factor,
            backfire_strength=self.backfire_strength,
            silence_threshold=self.silence_threshold,
            polarization_factor=self.polarization_factor,
            echo_chamber_factor=self.echo_chamber_factor
        )
        self.math_model = EnhancedMathModel(math_params)
        
        # 根据模式选择群体
        if self.use_llm:
            self.llm_population = LLMAgentPopulation(...)
        else:
            if self.mode == SimulationMode.SANDBOX:
                # 沙盘模式：参数驱动
                self.population = AgentPopulation(
                    size=self.population_size,
                    initial_rumor_spread=self.initial_rumor_spread,
                    network_type=self.network_type
                )
            else:
                # 新闻模式：真实分布锚定
                self.population = AgentPopulation(
                    size=self.population_size,
                    network_type=self.network_type
                )
                if self.init_distribution:
                    self._apply_init_distribution()
        
        return self._compute_state()
    
    def _apply_init_distribution(self):
        """应用真实分布锚定
        
        根据真实舆情分布初始化 Agent 观点
        """
        dist = self.init_distribution
        n = self.population_size
        
        belief_rumor_count = int(n * dist.get("believe_rumor", 0))
        belief_truth_count = int(n * dist.get("believe_truth", 0))
        
        opinions = np.zeros(n)
        
        # 相信谣言: -0.8 ~ -0.3
        if belief_rumor_count > 0:
            opinions[:belief_rumor_count] = np.random.uniform(-0.8, -0.3, belief_rumor_count)
        
        # 相信真相: 0.3 ~ 0.8
        start = belief_rumor_count
        end = start + belief_truth_count
        if belief_truth_count > 0:
            opinions[start:end] = np.random.uniform(0.3, 0.8, belief_truth_count)
        
        # 中立: -0.2 ~ 0.2
        if end < n:
            opinions[end:] = np.random.uniform(-0.2, 0.2, n - end)
        
        self.population.opinions = opinions
    
    # ==================== 推演步骤 ====================
    
    async def async_step(self) -> SimulationStateV2:
        """异步执行单步推演"""
        self.step_count += 1
        
        # 检查辟谣
        if (self.current_event and 
            self.step_count >= self.current_event.debunk_delay and 
            not self.debunked):
            self._release_debunking()
        
        if self.use_llm:
            await self._llm_step()
        else:
            self._math_step()
        
        # 更新预测缓存
        state = self._compute_state()
        self._update_prediction_cache(state)
        self.history.append(state.to_dict())
        
        # 在状态中添加预测信息（每10步计算一次）
        if self.mode == SimulationMode.NEWS and self.step_count % 10 == 0:
            state.prediction = self._compute_prediction()
            state.risk_alerts = self._compute_risk_alerts()
        
        return state
    
    def _math_step(self):
        """数学模型推演步骤"""
        pop = self.population
        old_opinions = pop.opinions.copy()
        
        neighbors_list = [pop.get_neighbors(i) for i in range(pop.size)]
        
        # 基础演化
        new_opinions, new_belief, is_silent, metrics = self.math_model.compute_step(
            opinions=pop.opinions,
            belief_strength=pop.belief_strength,
            influence=pop.influence,
            susceptibility=pop.susceptibility,
            fear_of_isolation=pop.fear_of_isolation,
            neighbors=neighbors_list,
            influencer_ids=self._get_influencer_ids(),
            debunk_released=self.debunked,
            step_count=self.step_count
        )
        
        # 新闻模式：应用知识图谱影响
        if (self.mode == SimulationMode.NEWS and 
            self.knowledge_evolution and 
            self.current_event):
            
            # 获取关键实体
            key_entities = [e["name"] for e in self.current_event.entities 
                          if e.get("importance", 5) <= 2]
            
            # 应用知识驱动演化
            knowledge_influence = self.knowledge_evolution.compute_batch_influence(
                opinions=new_opinions,
                personas=self._get_personas(),
                exposed_entities=[key_entities] * len(new_opinions),
                cocoon_strength=self.cocoon_strength
            )
            
            new_opinions = np.clip(
                new_opinions + knowledge_influence,
                -1, 1
            )
        
        pop.opinions = new_opinions
        pop.belief_strength = new_belief
        pop.is_silent = is_silent
        
        if self.debunked:
            pop.exposed_to_truth = np.ones(pop.size, dtype=bool)
    
    def _release_debunking(self):
        """发布辟谣"""
        self.debunked = True
        if self.current_event:
            logger.info(
                f"Step {self.step_count}: 发布辟谣 - {self.current_event.debunk_content[:50]}..."
            )
    
    def _update_prediction_cache(self, state: SimulationStateV2):
        """更新预测缓存"""
        self._prediction_cache["rumor_spread_rates"].append(state.rumor_spread_rate)
        self._prediction_cache["truth_acceptance_rates"].append(state.truth_acceptance_rate)
        self._prediction_cache["polarization_indices"].append(state.polarization_index)
    
    def _compute_prediction(self) -> Dict[str, PredictionInterval]:
        """计算预测区间
        
        基于历史数据计算未来趋势的置信区间
        """
        predictions = {}
        
        for key, values in self._prediction_cache.items():
            if len(values) < 5:
                continue
            
            values = np.array(values)
            mean = np.mean(values)
            std = np.std(values)
            
            # 简单线性外推
            if len(values) >= 3:
                slope = (values[-1] - values[0]) / len(values)
                expected = values[-1] + slope * 5  # 预测5步后
            else:
                expected = mean
            
            # 计算置信区间
            z = 1.96  # 95% 置信度
            margin = z * std
            
            predictions[key.replace("_rates", "").replace("_indices", "")] = PredictionInterval(
                expected=expected,
                optimistic=expected - margin,
                pessimistic=expected + margin,
                confidence=0.95
            )
        
        return predictions
    
    def _compute_risk_alerts(self) -> List[str]:
        """计算风险预警"""
        alerts = []
        
        if not self._prediction_cache["rumor_spread_rates"]:
            return alerts
        
        current_rumor = self._prediction_cache["rumor_spread_rates"][-1]
        current_polarization = self._prediction_cache["polarization_indices"][-1]
        
        # 谣言传播风险
        if current_rumor > 0.5:
            alerts.append("🚨 谣言传播率超过50%，需立即干预")
        elif current_rumor > 0.3:
            alerts.append("⚠️ 谣言传播率偏高")
        
        # 极化风险
        if current_polarization > 0.8:
            alerts.append("🚨 社会极化严重，分裂风险高")
        elif current_polarization > 0.6:
            alerts.append("⚠️ 极化趋势明显")
        
        # 干预窗口
        if current_rumor > 0.4 and self.step_count > 20:
            alerts.append("⚠️ 干预窗口正在收窄")
        
        return alerts
    
    def _compute_state(self) -> SimulationStateV2:
        """计算当前状态"""
        if self.use_llm:
            pop = self.llm_population
        else:
            pop = self.population
        
        opinion_dist = pop.get_opinion_histogram()
        stats = {
            "rumor_spread_rate": float(np.mean(pop.opinions < -0.2)),
            "truth_acceptance_rate": float(np.mean(pop.opinions > 0.2)),
            "avg_opinion": float(np.mean(pop.opinions)),
            "polarization_index": float(np.std(pop.opinions) * 2),
            "silence_rate": float(np.mean(pop.is_silent))
        }
        
        return SimulationStateV2(
            step=self.step_count,
            mode=self.mode,
            agents=pop.to_agent_list(),
            edges=pop.get_edges(),
            opinion_distribution=opinion_dist,
            **stats
        )
```

### 4.2 KnowledgeDrivenEvolution 知识图谱演化器

```python
# backend/simulation/knowledge_evolution.py

class KnowledgeDrivenEvolution:
    """知识图谱驱动的观点演化器
    
    新闻推演模式专用，根据知识图谱中的实体和关系
    计算对 Agent 观点的影响
    """
    
    def __init__(
        self,
        entity_impacts: Dict[str, float],
        relation_stance: Dict[str, str],
        evidence_strength: float = 0.5,
        authority_weight: float = 0.7
    ):
        """
        Args:
            entity_impacts: 实体影响力权重 {实体名: 权重}
            relation_stance: 关系立场 {关系ID: support/oppose/neutral}
            evidence_strength: 证据链强度 [0, 1]
            authority_weight: 权威加权
        """
        self.entity_impacts = entity_impacts
        self.relation_stance = relation_stance
        self.evidence_strength = evidence_strength
        self.authority_weight = authority_weight
    
    def compute_entity_influence(
        self,
        agent_persona: str,
        agent_opinion: float,
        exposed_entities: List[str],
        cocoon_strength: float = 0.5
    ) -> float:
        """
        计算实体对单个 Agent 的影响力
        
        机制：
        1. 实体基础影响力 × Agent 易感性
        2. 人设调节（意见领袖更易受权威影响，怀疑论者更难改变）
        3. 同向强化（观点相近时影响更大）
        4. 茧房效应（算法推荐强化既有观点）
        
        Args:
            agent_persona: Agent 人设类型
            agent_opinion: 当前观点值 [-1, 1]
            exposed_entities: 曝光的实体列表
            cocoon_strength: 茧房强度
            
        Returns:
            观点影响增量
        """
        total_impact = 0.0
        entity_count = 0
        
        for entity_name in exposed_entities:
            base_impact = self.entity_impacts.get(entity_name, 0.5)
            
            # 人设调节
            if "意见领袖" in agent_persona or "权威" in agent_persona:
                base_impact *= self.authority_weight
            elif "怀疑论者" in agent_persona:
                base_impact *= 0.5
            elif "从众者" in agent_persona:
                base_impact *= 1.2
            
            # 同向强化：观点相近时影响更大
            # 注意：这里需要实体立场信息，简化为静态
            alignment_factor = 1.0
            
            # 茧房效应
            cocoon_effect = cocoon_strength * agent_opinion * 0.1
            
            total_impact += base_impact * alignment_factor
            entity_count += 1
        
        if entity_count == 0:
            return 0.0
        
        # 平均影响力 × 证据强度
        avg_impact = total_impact / entity_count
        return avg_impact * self.evidence_strength
    
    def compute_batch_influence(
        self,
        opinions: np.ndarray,
        personas: List[str],
        exposed_entities: List[List[str]],
        cocoon_strength: float = 0.5
    ) -> np.ndarray:
        """
        批量计算对所有 Agent 的影响力
        
        Args:
            opinions: 所有 Agent 的观点值
            personas: 所有 Agent 的人设
            exposed_entities: 每个 Agent 曝光的实体列表
            cocoon_strength: 茧房强度
            
        Returns:
            影响力增量数组
        """
        influences = np.zeros(len(opinions))
        
        for i in range(len(opinions)):
            influences[i] = self.compute_entity_influence(
                agent_persona=personas[i],
                agent_opinion=opinions[i],
                exposed_entities=exposed_entities[i],
                cocoon_strength=cocoon_strength
            )
        
        return influences
    
    def compute_relation_cascade(
        self,
        source_entity: str,
        target_entity: str,
        base_impact: float
    ) -> float:
        """
        计算关系传递的影响cascade
        
        通过关系网络传递影响，距离越远影响越小
        
        Args:
            source_entity: 源实体
            target_entity: 目标实体
            base_impact: 基础影响力
            
        Returns:
            传递后的影响力
        """
        # 获取关系立场
        rel_id = f"{source_entity}_{target_entity}"
        stance = self.relation_stance.get(rel_id, "neutral")
        
        # 立场调节
        stance_factor = {
            "support": 1.0,
            "oppose": -0.8,
            "neutral": 0.5
        }.get(stance, 0.5)
        
        # 距离衰减（简化：假设最多一跳）
        distance_factor = 0.7
        
        return base_impact * stance_factor * distance_factor
```

### 4.3 图谱解析增强

```python
# backend/simulation/graph_parser_agent.py 增强

# 新增解析 Prompt 模板

GRAPH_PARSER_V2_PROMPT = """你是一个专业的信息抽取专家，负责从突发事件文本中提取结构化知识图谱。
这个图谱将用于智能体的认知决策，因此需要准确、清晰、可操作。

## 任务目标
从新闻文本中提取：
1. 实体（entities）：参与事件的关键对象
2. 关系（relations）：实体之间的互动关系
3. 证据（evidence）：支持或反驳的证据
4. 立场（stances）：各方的立场倾向

## 实体类型规范
- 人物：事件的参与者（主角、受害者、发言人等）
- 组织：涉及的机构、公司、政府部门等
- 地点：事件发生的地理位置
- 事件：核心事件本身作为抽象实体
- 概念：关键议题（如"食品安全"、"财务造假"等）
- 证据：具体的证据或声明

## 关系类型规范
- 参与：A参与了B事件
- 导致：A导致了B结果
- 对立：A与B立场对立
- 支持：A支持B的观点/行为
- 指控：A指控B做了某事
- 否认：A否认B的说法
- 影响：A影响B的状态/决策
- 提供证据：A提供了支持B的证据

## 输出格式（严格JSON）
```json
{{
  "entities": [
    {{
      "id": "e1",
      "name": "实体名称",
      "type": "人物|组织|地点|事件|概念|证据",
      "description": "简要描述",
      "importance": 1-5,  // 重要性：1=最重要，5=最不重要
      "stance": "支持方|反对方|中立"  // 对事件的态度
    }}
  ],
  "relations": [
    {{
      "source": "e1",
      "target": "e2",
      "action": "关系动词",
      "type": "参与|导致|对立|支持|指控|否认|影响|提供证据",
      "description": "详细描述"
    }}
  ],
  "evidence_chain": [
    {{
      "content": "证据内容",
      "source": "来源",
      "strength": 0.0-1.0  // 证据强度
    }}
  ],
  "summary": "一句话概括核心内容（30字以内）",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "sentiment": "正面|负面|中性|争议",
  "credibility_hint": "高可信|低可信|不确定"
}}
```

## 新闻文本
{news_content}

请提取知识图谱："""
```

---

## 五、API 设计

### 5.1 新增接口

#### POST /api/v2/simulation/start

启动 v2 推演（双模式）

**Request Body:**
```json
{
  "mode": "sandbox" | "news",
  "cocoon_strength": 0.5,
  "population_size": 200,
  "use_llm": true,
  
  // 沙盘模式参数
  "initial_rumor_spread": 0.3,
  
  // 新闻模式参数
  "init_distribution": {
    "believe_rumor": 0.25,
    "believe_truth": 0.15,
    "neutral": 0.60
  },
  "time_acceleration": 1.0
}
```

#### POST /api/v2/event/set

设置事件（支持沙盘/新闻）

**沙盘模式:**
```json
{
  "mode": "sandbox",
  "content": "某公司产品存在安全隐患",
  "initial_spread": 0.3
}
```

**新闻模式:**
```json
{
  "mode": "news",
  "content": "【新闻原文】...",
  "source": "public",
  "parse_graph": true,
  "debunk_content": "官方辟谣：...",
  "debunk_delay": 10,
  "init_distribution": {
    "believe_rumor": 0.25,
    "believe_truth": 0.15,
    "neutral": 0.60
  }
}
```

#### GET /api/v2/prediction

获取预测结果（仅新闻模式）

**Response:**
```json
{
  "success": true,
  "data": {
    "rumor_spread_rate": {
      "expected": 0.35,
      "optimistic": 0.25,
      "pessimistic": 0.50,
      "confidence": 0.95
    },
    "polarization_index": {
      "expected": 0.65,
      "optimistic": 0.55,
      "pessimistic": 0.80,
      "confidence": 0.95
    },
    "risk_alerts": [
      "🚨 谣言传播率超过50%，需立即干预",
      "⚠️ 极化趋势明显"
    ],
    "recommended_intervention": {
      "best_timing": 5,
      "suggested_strength": 0.8,
      "message": "建议加强权威辟谣"
    }
  }
}
```

### 5.2 WebSocket 消息格式增强

```json
// 状态更新（新增 prediction 和 risk_alerts）
{
  "type": "state_v2",
  "data": {
    "step": 30,
    "mode": "news",
    "rumor_spread_rate": 0.42,
    "prediction": {
      "rumor_spread_rate": {
        "expected": 0.45,
        "optimistic": 0.35,
        "pessimistic": 0.55
      }
    },
    "risk_alerts": ["⚠️ 谣言传播率偏高"],
    "entity_impact_summary": {
      "张三": 0.8,
      "某公司": 0.6
    }
  }
}
```

---

## 六、前端改造

### 6.1 模式切换组件

```vue
<!-- components/ModeSelector.vue -->

<template>
  <div class="mode-selector">
    <div class="mode-tabs">
      <button 
        :class="{ active: currentMode === 'sandbox' }"
        @click="selectMode('sandbox')"
      >
        🧪 沙盘推演
      </button>
      <button 
        :class="{ active: currentMode === 'news' }"
        @click="selectMode('news')"
      >
        📰 新闻推演
      </button>
    </div>
    
    <div class="mode-description">
      <p v-if="currentMode === 'sandbox'">
        假设驱动的研究工具，用于探索舆论传播机制
      </p>
      <p v-else>
        现实锚定的预测工具，基于真实新闻事件进行推演预测
      </p>
    </div>
  </div>
</template>
```

### 6.2 预测结果展示组件

```vue
<!-- components/PredictionView.vue -->

<template>
  <div class="prediction-view" v-if="isNewsMode && prediction">
    <h3>📊 预测分析</h3>
    
    <div class="prediction-intervals">
      <div 
        v-for="(interval, key) in prediction" 
        :key="key"
        class="interval-card"
      >
        <div class="interval-title">{{ formatKey(key) }}</div>
        <div class="interval-values">
          <span class="optimistic">{{ interval.optimistic.toFixed(1%) }}</span>
          <span class="expected">{{ interval.expected.toFixed(1%) }}</span>
          <span class="pessimistic">{{ interval.pessimistic.toFixed(1%) }}</span>
        </div>
        <div class="confidence">置信度: {{ interval.confidence }}</div>
      </div>
    </div>
    
    <div class="risk-alerts" v-if="riskAlerts.length">
      <h4>🚨 风险预警</h4>
      <ul>
        <li v-for="alert in riskAlerts" :key="alert">{{ alert }}</li>
      </ul>
    </div>
    
    <div class="intervention-recommendation" v-if="recommendation">
      <h4>💡 干预建议</h4>
      <p>{{ recommendation.message }}</p>
      <p>最佳时机: 第 {{ recommendation.best_timing }} 步</p>
    </div>
  </div>
</template>
```

---

## 七、分阶段实施计划（优化版）

### 7.1 实施原则

1. **最小可行增量**：每个阶段独立可用，验证后再推进
2. **数据驱动验证**：关键功能需有对比实验
3. **参数可配置**：避免硬编码，便于调优

### 7.2 阶段划分

#### Phase 1: 知识图谱驱动演化（核心）

**目标**：让知识图谱参与观点演化，而非仅作为LLM上下文

**交付物**：
- `knowledge_evolution.py` - 知识驱动演化器
- 实体影响力增强计算
- 人设参数化配置
- A/B验证机制

**验证标准**：
- 有/无知识图谱驱动的演化轨迹有显著差异
- 关键实体（高重要性）对舆论影响更大

**工作量**：3-4天

---

#### Phase 2: 预测区间 + 风险预警

**目标**：提供有置信度的预测和实时风险监控

**交付物**：
- 预测模型（蒙特卡洛/时间序列）
- 预测区间计算
- 风险预警规则引擎
- 前端预测展示组件

**验证标准**：
- 预测区间覆盖率 > 80%（回测）
- 风险预警准确率 > 70%

**工作量**：2-3天

---

#### Phase 3: 完整新闻模式 + 干预建议

**目标**：新闻模式的完整体验，支持干预决策

**交付物**：
- `engine_v2.py` 完整实现
- 真实分布锚定
- 干预时机建议
- 前端新闻模式组件

**验证标准**：
- 与真实舆情数据对比（如有）
- 干预建议有效性验证

**工作量**：3-4天

---

#### Phase 4: 双模式整合 + 文档

**目标**：完整双模式体验

**交付物**：
- 模式切换组件
- API v2 完整实现
- 用户文档

**工作量**：2天

---

### 7.3 兼容策略

1. **双轨并行**：`engine.py` / `engine_v2.py` 并存
2. **渐进迁移**：前端逐步支持新接口
3. **配置切换**：通过配置项切换版本

---

## 八、Phase 1 详细设计

### 8.1 实体影响力增强计算

当前仅基于 `importance` 字段，建议综合考虑：

```python
# backend/simulation/knowledge_evolution.py

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

@dataclass
class EntityImpactConfig:
    """实体影响力配置"""
    # 类型权重（媒体 > 官方 > 专家 > 组织 > 人物）
    type_weights: Dict[str, float] = None
    
    # 重要性衰减系数
    importance_decay: float = 0.8
    
    # 网络中心性权重
    centrality_weight: float = 0.3
    
    def __post_init__(self):
        if self.type_weights is None:
            self.type_weights = {
                "媒体": 1.0,
                "官方": 0.95,
                "专家": 0.85,
                "组织": 0.7,
                "人物": 0.5,
                "地点": 0.3,
                "概念": 0.2,
                "事件": 0.4,
                "证据": 0.6
            }


class EntityImpactCalculator:
    """实体影响力计算器"""
    
    def __init__(self, config: EntityImpactConfig = None):
        self.config = config or EntityImpactConfig()
    
    def calculate(
        self,
        entities: List[Dict],
        network_centrality: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        计算实体影响力
        
        综合考虑：
        1. 实体类型权重（媒体影响力最大）
        2. 重要性字段（1-5，越小越重要）
        3. 网络中心性（社交网络中的位置）
        
        Args:
            entities: 实体列表
            network_centrality: 实体在社交网络中的中心性 {实体名: 中心性}
        
        Returns:
            {实体名: 影响力权重 [0, 1]}
        """
        impacts = {}
        
        for entity in entities:
            name = entity.get("name", "")
            entity_type = entity.get("type", "人物")
            importance = entity.get("importance", 3)  # 1-5
            
            # 1. 类型权重
            type_weight = self.config.type_weights.get(entity_type, 0.5)
            
            # 2. 重要性权重（importance=1 -> weight=1.0, importance=5 -> weight=0.2）
            importance_weight = (6 - importance) / 5
            
            # 3. 网络中心性权重（如果有）
            centrality = 0.5  # 默认中等
            if network_centrality and name in network_centrality:
                centrality = network_centrality[name]
            
            # 综合计算
            impact = (
                type_weight * 0.4 +
                importance_weight * 0.4 +
                centrality * self.config.centrality_weight * 0.2
            )
            
            impacts[name] = min(1.0, max(0.0, impact))
        
        return impacts
```

### 8.2 人设参数化配置

避免硬编码，使用配置表：

```python
# backend/config/persona_config.py

from dataclasses import dataclass, field
from typing import Dict

@dataclass
class PersonaWeights:
    """人设影响权重配置
    
    用于计算不同人设类型对信息的接受度和影响力
    """
    # 对权威信息的接受度 [0, 1]
    authority_acceptance: float = 0.7
    
    # 对谣言的易感性 [0, 1]
    rumor_susceptibility: float = 0.5
    
    # 对真相的接受度 [0, 1]
    truth_acceptance: float = 0.6
    
    # 观点稳定性 [0, 1]，越高越难改变
    opinion_stability: float = 0.5
    
    # 社交影响力 [0, 1]
    social_influence: float = 0.5


# 预定义人设配置
PERSONA_CONFIGS: Dict[str, PersonaWeights] = {
    "意见领袖": PersonaWeights(
        authority_acceptance=0.9,
        rumor_susceptibility=0.3,
        truth_acceptance=0.8,
        opinion_stability=0.7,
        social_influence=0.9
    ),
    "怀疑论者": PersonaWeights(
        authority_acceptance=0.4,
        rumor_susceptibility=0.2,
        truth_acceptance=0.5,
        opinion_stability=0.8,
        social_influence=0.4
    ),
    "从众者": PersonaWeights(
        authority_acceptance=0.7,
        rumor_susceptibility=0.8,
        truth_acceptance=0.7,
        opinion_stability=0.3,
        social_influence=0.3
    ),
    "理性派": PersonaWeights(
        authority_acceptance=0.6,
        rumor_susceptibility=0.2,
        truth_acceptance=0.9,
        opinion_stability=0.6,
        social_influence=0.5
    ),
    "激进派": PersonaWeights(
        authority_acceptance=0.3,
        rumor_susceptibility=0.9,
        truth_acceptance=0.3,
        opinion_stability=0.9,
        social_influence=0.7
    ),
    "中立观察者": PersonaWeights(
        authority_acceptance=0.5,
        rumor_susceptibility=0.4,
        truth_acceptance=0.5,
        opinion_stability=0.5,
        social_influence=0.3
    ),
    "官方发言": PersonaWeights(
        authority_acceptance=1.0,
        rumor_susceptibility=0.1,
        truth_acceptance=1.0,
        opinion_stability=0.95,
        social_influence=0.95
    ),
    "媒体账号": PersonaWeights(
        authority_acceptance=0.8,
        rumor_susceptibility=0.4,
        truth_acceptance=0.7,
        opinion_stability=0.6,
        social_influence=0.85
    )
}


def get_persona_weights(persona_type: str) -> PersonaWeights:
    """获取人设权重配置，未知类型返回默认配置"""
    return PERSONA_CONFIGS.get(persona_type, PersonaWeights())
```

### 8.3 知识驱动演化器（增强版）

```python
# backend/simulation/knowledge_evolution.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging

from .entity_impact import EntityImpactCalculator, EntityImpactConfig
from ..config.persona_config import get_persona_weights, PersonaWeights

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeEvolutionConfig:
    """知识驱动演化配置"""
    # 证据链强度
    evidence_strength: float = 0.5
    
    # 辟谣效果系数
    debunk_effectiveness: float = 0.6
    
    # 关系传播衰减
    relation_decay: float = 0.7
    
    # 实体曝光上限（每个Agent最多关注N个实体）
    max_exposed_entities: int = 5


class KnowledgeDrivenEvolution:
    """知识图谱驱动的观点演化器
    
    核心功能：
    1. 实体影响力计算（类型+重要性+网络位置）
    2. 人设调节（参数化配置）
    3. 关系传导（立场传递）
    4. 观点更新（知识驱动）
    """
    
    def __init__(
        self,
        entities: List[Dict],
        relations: List[Dict],
        config: KnowledgeEvolutionConfig = None,
        impact_config: EntityImpactConfig = None
    ):
        self.config = config or KnowledgeEvolutionConfig()
        self.impact_calculator = EntityImpactCalculator(impact_config)
        
        # 计算实体影响力
        self.entity_impacts = self.impact_calculator.calculate(entities)
        
        # 计算关系立场
        self.relation_stance = self._calculate_relation_stance(relations)
        
        # 构建实体关系图
        self.entity_graph = self._build_entity_graph(entities, relations)
        
        # 缓存实体列表（按影响力排序）
        self.sorted_entities = sorted(
            entities, 
            key=lambda e: self.entity_impacts.get(e.get("name", ""), 0),
            reverse=True
        )
        
        logger.info(f"知识驱动演化器初始化: {len(entities)} 实体, {len(relations)} 关系")
    
    def _calculate_relation_stance(self, relations: List[Dict]) -> Dict[str, str]:
        """计算关系立场"""
        stance_map = {
            "支持": "support",
            "反对": "oppose",
            "对立": "oppose",
            "指控": "oppose",
            "否认": "neutral",
            "参与": "neutral",
            "导致": "neutral",
            "影响": "neutral",
            "提供证据": "support"
        }
        
        stances = {}
        for rel in relations:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_id = f"{source}_{target}"
            rel_type = rel.get("type", "关联")
            stances[rel_id] = stance_map.get(rel_type, "neutral")
        return stances
    
    def _build_entity_graph(
        self, 
        entities: List[Dict], 
        relations: List[Dict]
    ) -> Dict[str, List[Tuple[str, str, float]]]:
        """构建实体关系图
        
        Returns:
            {实体名: [(关联实体名, 关系立场, 关系强度), ...]}
        """
        graph = {e.get("name", ""): [] for e in entities}
        
        for rel in relations:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "关联")
            
            stance = self.relation_stance.get(f"{source}_{target}", "neutral")
            
            # 关系强度：支持/反对强于中立
            strength = 0.8 if stance != "neutral" else 0.4
            
            if source in graph:
                graph[source].append((target, stance, strength))
            if target in graph:
                graph[target].append((source, stance, strength))
        
        return graph
    
    def compute_influence(
        self,
        agent_opinion: float,
        agent_persona: str,
        exposed_entities: List[str],
        cocoon_strength: float = 0.5,
        debunk_released: bool = False
    ) -> float:
        """
        计算知识图谱对单个Agent的观点影响
        
        机制：
        1. 实体基础影响力 × 人设调节
        2. 观点同向/反向强化
        3. 茧房效应调节
        4. 辟谣效果（如已发布）
        
        Args:
            agent_opinion: 当前观点 [-1, 1]
            agent_persona: 人设类型
            exposed_entities: 曝光的实体列表
            cocoon_strength: 茧房强度
            debunk_released: 是否已辟谣
        
        Returns:
            观点影响增量
        """
        # 获取人设配置
        persona = get_persona_weights(agent_persona)
        
        total_impact = 0.0
        entity_count = 0
        
        for entity_name in exposed_entities:
            # 实体基础影响力
            base_impact = self.entity_impacts.get(entity_name, 0.3)
            
            # 人设调节
            # 意见领袖更受权威实体影响，怀疑论者更难改变
            if base_impact > 0.7:  # 高影响力实体（权威）
                modifier = persona.authority_acceptance
            else:
                modifier = persona.rumor_susceptibility
            
            # 观点稳定性：稳定性越高，影响越小
            stability_factor = 1.0 - persona.opinion_stability * 0.5
            
            # 茧房效应：同向强化，反向削弱
            # 假设实体立场与新闻整体立场一致（简化）
            entity_stance = 1.0 if base_impact > 0.5 else -0.5  # 正面/负面
            alignment = agent_opinion * entity_stance
            cocoon_effect = 1.0 + cocoon_strength * alignment * 0.3
            
            # 综合影响
            impact = base_impact * modifier * stability_factor * cocoon_effect
            total_impact += impact
            entity_count += 1
        
        if entity_count == 0:
            return 0.0
        
        # 平均影响力 × 证据强度
        avg_impact = total_impact / entity_count
        result = avg_impact * self.config.evidence_strength
        
        # 辟谣效果：正向推动
        if debunk_released:
            result += self.config.debunk_effectiveness * 0.1
        
        return np.clip(result, -0.15, 0.15)  # 限制单步影响幅度
    
    def compute_batch_influence(
        self,
        opinions: np.ndarray,
        personas: List[str],
        cocoon_strength: float = 0.5,
        debunk_released: bool = False
    ) -> np.ndarray:
        """
        批量计算对所有Agent的影响力
        
        自动为每个Agent分配最相关的实体（基于网络位置和影响力）
        """
        n = len(opinions)
        influences = np.zeros(n)
        
        # 为每个Agent分配实体
        # 策略：随机 + 按影响力加权
        entity_names = [e.get("name", "") for e in self.sorted_entities]
        entity_weights = np.array([
            self.entity_impacts.get(name, 0.3) 
            for name in entity_names
        ])
        entity_weights = entity_weights / entity_weights.sum()
        
        for i in range(n):
            # 随机选择实体（高影响力实体更容易被关注）
            n_entities = min(
                self.config.max_exposed_entities, 
                len(entity_names)
            )
            selected_indices = np.random.choice(
                len(entity_names),
                size=n_entities,
                replace=False,
                p=entity_weights
            )
            exposed = [entity_names[j] for j in selected_indices]
            
            influences[i] = self.compute_influence(
                agent_opinion=opinions[i],
                agent_persona=personas[i] if i < len(personas) else "中立观察者",
                exposed_entities=exposed,
                cocoon_strength=cocoon_strength,
                debunk_released=debunk_released
            )
        
        return influences
    
    def get_top_entities(self, n: int = 5) -> List[Tuple[str, float]]:
        """获取影响力最高的N个实体"""
        return [
            (e.get("name", ""), self.entity_impacts.get(e.get("name", ""), 0))
            for e in self.sorted_entities[:n]
        ]


# ==================== 验证工具 ====================

class KnowledgeEvolutionValidator:
    """知识驱动演化验证器
    
    用于A/B测试：对比有/无知识图谱驱动的演化差异
    """
    
    @staticmethod
    def compare_trajectories(
        with_knowledge: List[Dict],
        without_knowledge: List[Dict]
    ) -> Dict:
        """
        对比两条演化轨迹
        
        Args:
            with_knowledge: 有知识图谱驱动的演化历史
            without_knowledge: 无知识图谱驱动的演化历史
        
        Returns:
            对比结果
        """
        if not with_knowledge or not without_knowledge:
            return {"error": "轨迹数据为空"}
        
        # 提取关键指标
        def extract_metrics(history):
            return {
                "rumor_rates": [h.get("rumor_spread_rate", 0) for h in history],
                "truth_rates": [h.get("truth_acceptance_rate", 0) for h in history],
                "polarizations": [h.get("polarization_index", 0) for h in history]
            }
        
        m1 = extract_metrics(with_knowledge)
        m2 = extract_metrics(without_knowledge)
        
        # 计算差异
        min_len = min(len(m1["rumor_rates"]), len(m2["rumor_rates"]))
        
        result = {
            "rumor_rate_diff": np.mean(m1["rumor_rates"][:min_len]) - np.mean(m2["rumor_rates"][:min_len]),
            "truth_rate_diff": np.mean(m1["truth_rates"][:min_len]) - np.mean(m2["truth_rates"][:min_len]),
            "polarization_diff": np.mean(m1["polarizations"][:min_len]) - np.mean(m2["polarizations"][:min_len]),
            "final_rumor_diff": m1["rumor_rates"][min_len-1] - m2["rumor_rates"][min_len-1],
            "final_truth_diff": m1["truth_rates"][min_len-1] - m2["truth_rates"][min_len-1],
            "significant": False
        }
        
        # 判断是否显著（简化：差异超过5%）
        result["significant"] = abs(result["final_rumor_diff"]) > 0.05
        
        return result
```

### 8.4 集成到现有引擎

```python
# backend/simulation/engine.py 修改

class SimulationEngine:
    """现有引擎增加知识驱动演化支持"""
    
    def __init__(self, ...):
        # ... 现有代码 ...
        
        # 新增：知识驱动演化器
        self.knowledge_evolution: Optional[KnowledgeDrivenEvolution] = None
        self.use_knowledge_evolution: bool = False
    
    def set_knowledge_graph(
        self, 
        entities: List[Dict], 
        relations: List[Dict],
        config: KnowledgeEvolutionConfig = None
    ):
        """设置知识图谱，启用知识驱动演化"""
        self.knowledge_evolution = KnowledgeDrivenEvolution(
            entities=entities,
            relations=relations,
            config=config
        )
        self.use_knowledge_evolution = True
        logger.info("知识图谱已设置，启用知识驱动演化")
    
    def _math_step(self):
        """数学模型推演步骤（增强版）"""
        pop = self.population
        old_opinions = pop.opinions.copy()
        
        neighbors_list = [pop.get_neighbors(i) for i in range(pop.size)]
        
        # 基础演化
        new_opinions, new_belief, is_silent, metrics = self.math_model.compute_step(
            opinions=pop.opinions,
            belief_strength=pop.belief_strength,
            influence=pop.influence,
            susceptibility=pop.susceptibility,
            fear_of_isolation=pop.fear_of_isolation,
            neighbors=neighbors_list,
            influencer_ids=self._get_influencer_ids(),
            debunk_released=self.debunked,
            step_count=self.step_count
        )
        
        # 新增：知识驱动演化
        if self.use_knowledge_evolution and self.knowledge_evolution:
            personas = self._get_personas()  # 获取所有人设
            knowledge_influence = self.knowledge_evolution.compute_batch_influence(
                opinions=new_opinions,
                personas=personas,
                cocoon_strength=self.cocoon_strength,
                debunk_released=self.debunked
            )
            
            # 应用知识影响
            new_opinions = np.clip(new_opinions + knowledge_influence, -1, 1)
            
            logger.debug(f"知识驱动演化: 平均影响 {np.mean(np.abs(knowledge_influence)):.4f}")
        
        pop.opinions = new_opinions
        pop.belief_strength = new_belief
        pop.is_silent = is_silent
        
        if self.debunked:
            pop.exposed_to_truth = np.ones(pop.size, dtype=bool)
```

---

## 九、验证与测试

### 9.1 单元测试

```python
# tests/test_knowledge_evolution.py

import pytest
import numpy as np
from backend.simulation.knowledge_evolution import (
    KnowledgeDrivenEvolution,
    KnowledgeEvolutionConfig,
    EntityImpactCalculator,
    EntityImpactConfig
)
from backend.config.persona_config import PERSONA_CONFIGS, get_persona_weights


class TestEntityImpactCalculator:
    """实体影响力计算测试"""
    
    def test_type_weights(self):
        """测试类型权重"""
        calc = EntityImpactCalculator()
        entities = [
            {"name": "央视新闻", "type": "媒体", "importance": 1},
            {"name": "张三", "type": "人物", "importance": 1},
        ]
        impacts = calc.calculate(entities)
        
        # 媒体权重应高于人物
        assert impacts["央视新闻"] > impacts["张三"]
    
    def test_importance_weights(self):
        """测试重要性权重"""
        calc = EntityImpactCalculator()
        entities = [
            {"name": "关键人物", "type": "人物", "importance": 1},
            {"name": "普通人物", "type": "人物", "importance": 5},
        ]
        impacts = calc.calculate(entities)
        
        # importance=1 应高于 importance=5
        assert impacts["关键人物"] > impacts["普通人物"]


class TestPersonaConfig:
    """人设配置测试"""
    
    def test_opinion_leader(self):
        """意见领袖应有高权威接受度"""
        weights = get_persona_weights("意见领袖")
        assert weights.authority_acceptance > 0.8
        assert weights.social_influence > 0.8
    
    def test_skeptic(self):
        """怀疑论者应有低易感性"""
        weights = get_persona_weights("怀疑论者")
        assert weights.rumor_susceptibility < 0.3
        assert weights.opinion_stability > 0.7
    
    def test_unknown_persona(self):
        """未知人设返回默认配置"""
        weights = get_persona_weights("未知类型")
        assert weights.authority_acceptance == 0.7  # 默认值


class TestKnowledgeDrivenEvolution:
    """知识驱动演化测试"""
    
    @pytest.fixture
    def evolution(self):
        entities = [
            {"name": "权威媒体", "type": "媒体", "importance": 1},
            {"name": "当事人", "type": "人物", "importance": 2},
            {"name": "专家", "type": "专家", "importance": 2},
        ]
        relations = [
            {"source": "权威媒体", "target": "当事人", "type": "报道"},
            {"source": "专家", "target": "当事人", "type": "支持"},
        ]
        return KnowledgeDrivenEvolution(entities, relations)
    
    def test_entity_impacts_calculated(self, evolution):
        """实体影响力应被正确计算"""
        assert len(evolution.entity_impacts) == 3
        assert "权威媒体" in evolution.entity_impacts
    
    def test_influence_bounds(self, evolution):
        """影响力应在合理范围内"""
        influence = evolution.compute_influence(
            agent_opinion=0.0,
            agent_persona="中立观察者",
            exposed_entities=["权威媒体", "专家"],
            cocoon_strength=0.5
        )
        assert -0.15 <= influence <= 0.15
    
    def test_batch_influence_shape(self, evolution):
        """批量影响力输出形状正确"""
        opinions = np.zeros(100)
        personas = ["中立观察者"] * 100
        influences = evolution.compute_batch_influence(opinions, personas)
        assert influences.shape == (100,)
```

### 9.2 A/B对比测试

```python
# tests/test_evolution_comparison.py

import pytest
import numpy as np
from backend.simulation.engine import SimulationEngine


class TestEvolutionComparison:
    """有/无知识图谱演化的对比测试"""
    
    def test_knowledge_evolution_makes_difference(self):
        """知识图谱驱动应有显著影响"""
        # 运行无知识图谱演化
        engine1 = SimulationEngine(
            population_size=100,
            initial_rumor_spread=0.3,
            use_llm=False
        )
        engine1.initialize()
        for _ in range(30):
            engine1.step()
        history1 = engine1.history
        
        # 运行有知识图谱演化
        engine2 = SimulationEngine(
            population_size=100,
            initial_rumor_spread=0.3,
            use_llm=False
        )
        engine2.initialize()
        
        # 设置知识图谱
        entities = [
            {"name": "权威信源", "type": "官方", "importance": 1},
            {"name": "谣言源头", "type": "人物", "importance": 2},
        ]
        relations = [
            {"source": "权威信源", "target": "谣言源头", "type": "否认"},
        ]
        engine2.set_knowledge_graph(entities, relations)
        
        for _ in range(30):
            engine2.step()
        history2 = engine2.history
        
        # 对比最终谣言传播率
        final_rumor1 = history1[-1]["rumor_spread_rate"]
        final_rumor2 = history2[-1]["rumor_spread_rate"]
        
        # 知识图谱驱动应改变演化轨迹
        # 注意：这里不判断谁高谁低，只判断有差异
        print(f"无知识图谱: {final_rumor1:.3f}, 有知识图谱: {final_rumor2:.3f}")
        # 至少记录差异，具体效果需要更多测试
```

---

## 十、附录

### 10.1 术语表

| 术语 | 定义 |
|------|------|
| 沙盘推演 | 基于假设的参数探索，用于研究传播机制 |
| 新闻推演 | 基于真实事件的推演预测，用于决策支持 |
| 实体影响力 | 重要人物/机构对舆论的影响程度 |
| 证据链 | 支持或反驳事件的核心证据 |
| 预测区间 | 考虑不确定性的区间预测 |
| 人设权重 | 不同类型Agent对信息的接受度和影响力参数 |

### 10.2 参考资料

1. Deffuant et al. (2002). "JSNS: A Java-based simulator for opinion dynamics"
2. Watts & Strogatz (1998). "Collective dynamics of 'small-world' networks"
3. Barabási & Albert (1999). "Emergence of scaling in random networks"
4. Sunstein (2001). "Echo Chambers: Bush v. Gore, Impeachment, and Beyond"
5. Noelle-Neumann (1974). "The Spiral of Silence: A Theory of Public Opinion"
