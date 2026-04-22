# 信息茧房推演系统 v3.0 优化设计方案

> 基于 AgentSociety 架构启发的系统性升级

## 一、概述

### 1.1 优化背景

当前系统已实现双模式（沙盘/新闻）和双引擎（数学/LLM）架构，但仍存在以下提升空间：

| 现状 | 优化方向 |
|------|----------|
| 观点状态仅用数值表示 | 引入结构化信念模型 |
| 记忆系统薄弱 | 三层记忆架构 |
| 环境交互单一 | 分层环境感知机制 |
| 技能系统缺失 | Skill Pipeline 模式 |

### 1.2 设计目标

| 目标 | 描述 | 优先级 |
|------|------|--------|
| 认知增强 | 引入结构化信念与记忆系统 | P0 |
| 环境分层 | Algorithm/Social/Truth 三维度感知 | P0 |
| 技能管道 | Skill Pipeline 懒加载模式 | P1 |
| 通信增强 | P2P/P2G/GroupChat 多模式 | P1 |
| 心理学整合 | 马斯洛、计划行为理论 | P2 |

---

## 二、系统架构（AgentSociety 启发）

### 2.1 分层架构对比

**当前架构：**
```
Interface → Engine → Agents → Network
```

**优化后架构：**
```
Interface Layer → Orchestration Layer → Agent Layer → Environment Layer → LLM Layer
```

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Information Cocoon Simulation                  │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Interface Layer                             │  │
│  │    WebSocket (/ws/simulation) + REST API                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                 ↓                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                Orchestration Layer                             │  │
│  │    SimulationEngine + PredictionEngine + RiskAlert           │  │
│  │    [Dual Mode: Math Model / LLM-Driven]                       │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                 ↓                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Agent Layer                                  │  │
│  │    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │  │
│  │    │   Persona   │ │   Memory    │ │  Skills    │           │  │
│  │    │ (人设+信念)  │ │ (三层记忆)   │ │ (技能管道)  │           │  │
│  │    └─────────────┘ └─────────────┘ └─────────────┘           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                 ↓                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                  Environment Layer                             │  │
│  │    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │  │
│  │    │  Algorithm  │ │   Social    │ │    Truth    │           │  │
│  │    │  (算法茧房)  │ │  (社交网络)  │ │  (官方辟谣)  │           │  │
│  │    └─────────────┘ └─────────────┘ └─────────────┘           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                 ↓                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     LLM Layer                                   │  │
│  │    DeepSeek-V3 (via litellm router)                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、Agent Layer 增强

### 3.1 PersonAgent 设计

```python
class PersonAgent:
    """LLM驱动的智能体 - 基于 AgentSociety PersonAgent 模式"""
    
    def __init__(self, agent_id: str, profile: AgentProfile):
        self.id = agent_id
        self.name = profile.name
        self.profile = profile
        
        # 观点状态（增强）
        self.belief_state = BeliefState(
            rumor_trust: float,      # 信任谣言程度 [-1, 1]
            truth_trust: float,     # 信任真相程度 [-1, 1]
            belief_strength: float, # 信念强度 [0, 1]
            cognitive_closed_need: float  # 认知闭合需求 [0, 1]
        )
        
        # 三层记忆系统
        self.memory = AgentMemory(
            short_term: Deque[N],    # 最近N轮交互
            long_term: SQLite,      # 持久化信念历史
            cognition_buffer: List  # 认知处理缓冲
        )
        
        # 技能管道
        self.skills: Dict[str, Skill] = {}
        
        # 环境交互
        self.env_router: EnvRouter = None
```

### 3.2 BeliefState 结构

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class BeliefState(BaseModel):
    """结构化信念状态"""
    
    # 核心观点
    rumor_trust: float = 0.0        # 谣言信任度 [-1, 1]
    truth_trust: float = 0.0        # 真相信任度 [-1, 1]
    
    # 信念属性
    belief_strength: float = 0.5    # 信念强度 [0, 1]
    cognitive_closed_need: float = 0.5  # 认知闭合需求
    
    # 信息暴露历史
    exposure_history: List[ExposureEvent] = []
    
    # 最后更新时间
    last_updated: datetime = None
    
    def to_opinion(self) -> float:
        """转换为单一观点值 [-1, 1]"""
        return self.truth_trust - self.rumor_trust

class ExposureEvent(BaseModel):
    """信息暴露事件"""
    timestamp: datetime
    source: str  # "algorithm" | "social" | "truth"
    content: str
    trust_delta: float  # 观点变化量
```

### 3.3 三层记忆架构

```
┌─────────────────────────────────────────────┐
│              Agent Memory                    │
├─────────────────────────────────────────────┤
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  Short-term Memory (短时记忆)          │  │
│  │  - 最近 N 轮交互                       │  │
│  │  - 算法推荐内容                         │  │
│  │  - 社交圈观点                          │  │
│  │  - 可配置窗口大小                      │  │
│  └───────────────────────────────────────┘  │
│                    ↓                        │
│  ┌───────────────────────────────────────┐  │
│  │  Long-term Memory (长时记忆)           │  │
│  │  - 信念演化历史                        │  │
│  │  - 关键事件记录                        │  │
│  │  - SQLite 持久化                       │  │
│  └───────────────────────────────────────┘  │
│                    ↓                        │
│  ┌───────────────────────────────────────┐  │
│  │  Cognition Buffer (认知缓冲)           │  │
│  │  - 临时推理结果                        │  │
│  │  - LLM 生成内容                        │  │
│  │  - close() 时 flush 到长时记忆         │  │
│  └───────────────────────────────────────┘  │
│                                             │
└─────────────────────────────────────────────┘
```

**实现代码：**

```python
from collections import deque
from datetime import datetime
import sqlite3

class AgentMemory:
    """三层记忆系统"""
    
    def __init__(self, agent_id: str, short_window: int = 10):
        self.agent_id = agent_id
        
        # 短时记忆：最近N轮
        self.short_term = deque(maxlen=short_window)
        
        # 长时记忆：SQLite持久化
        self.long_term = self._init_long_term(agent_id)
        
        # 认知缓冲
        self.cognition_buffer: List[Dict] = []
    
    def add_interaction(self, event: ExposureEvent):
        """添加交互事件到短时记忆"""
        self.short_term.append(event)
    
    def store_belief(self, belief: BeliefState):
        """存储信念到长时记忆"""
        self._save_to_db(belief)
    
    def add_cognition(self, cognition: Dict):
        """添加认知结果到缓冲"""
        self.cognition_buffer.append(cognition)
    
    def flush_cognition(self):
        """Flush认知缓冲到长时记忆"""
        for cognition in self.cognition_buffer:
            self._save_cognition(cognition)
        self.cognition_buffer.clear()
    
    def retrieve_relevant(self, query: str, limit: int = 5) -> List[Dict]:
        """检索相关记忆"""
        # 简化实现：返回最近N条
        return list(self.short_term)[-limit:]
```

---

## 四、Skill Pipeline 设计

### 4.1 技能架构（AgentSociety 启发）

**核心模式：元数据优先 + 懒加载**

```python
# 技能选择流程
class PersonAgent:
    async def step(self):
        # 1. Skill Selection - LLM基于metadata选择
        selected = await self.select_skills()
        
        # 2. On-demand Loading - 仅加载选中的技能
        for skill_name in selected:
            if skill_name not in self.skills:
                self.skills[skill_name] = await self.load_skill(skill_name)
        
        # 3. Priority Execution - 按优先级执行
        for skill in sorted(selected, key=lambda s: s.priority):
            result = await skill.execute()
            self.memory.add_cognition(result)
        
        return result
```

### 4.2 内建认知技能

| 技能 | 优先级 | 功能 | 输出 |
|------|--------|------|------|
| **observation** | 10 | 感知环境信息 | ExposureEvent[] |
| **memory** | 20 | 检索相关记忆 | MemoryResult |
| **needs** | 30 | 马斯洛需求分析 | NeedState |
| **cognition** | 40 | 推理观点变化 | BeliefDelta |
| **plan** | 50 | 规划响应策略 | ActionPlan |

### 4.3 技能定义格式

```
agent/skills/
├── observation/
│   ├── SKILL.yaml          # 元数据
│   └── scripts/observation.py
├── memory/
│   ├── SKILL.yaml
│   └── scripts/memory.py
├── needs/
│   ├── SKILL.yaml
│   └── scripts/needs.py
├── cognition/
│   ├── SKILL.yaml
│   └── scripts/cognition.py
└── plan/
    ├── SKILL.yaml
    └── scripts/plan.py
```

**SKILL.yaml 格式：**

```yaml
name: cognition
description: 推理观点变化，基于信息暴露和社会影响
priority: 40
requires:
  - observation
  - memory
provides:
  - belief_delta
  - reasoning_trace
config:
  reasoning_depth: 3
  include_uncertainty: true
```

---

## 五、Environment Layer 设计

### 5.1 环境分层

```
┌─────────────────────────────────────────────────────────────┐
│                  Environment Layer                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  AlgorithmEnv    │  │    SocialEnv     │               │
│  │  (算法茧房)       │  │    (社交网络)     │               │
│  ├──────────────────┤  ├──────────────────┤               │
│  │ exposure_history │  │ network_topology │               │
│  │ diversity_index  │  │ influence_matrix │               │
│  │ recommendation   │  │ peer_opinions   │               │
│  │ cocoon_strength  │  │ communityDetect │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
│  ┌──────────────────┐                                      │
│  │    TruthEnv      │                                      │
│  │   (官方辟谣)      │                                      │
│  ├──────────────────┤                                      │
│  │ interventions    │                                      │
│  │ credibility_score│                                      │
│  │ debunk_content   │                                      │
│  │ timing_analysis │                                      │
│  └──────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 环境模块基类

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from functools import wraps

def tool(readonly: bool = True, kind: str = None):
    """环境工具装饰器"""
    def decorator(func):
        func._is_tool = True
        func._readonly = readonly
        func._kind = kind
        return func
    return decorator

class EnvBase(ABC):
    """环境模块基类"""
    
    @tool(readonly=True, kind="observe")
    async def observe(self, agent_id: str) -> str:
        """感知环境状态"""
        pass
    
    @tool(readonly=True, kind="statistics")
    async def get_statistics(self) -> Dict:
        """获取统计信息"""
        pass
    
    @tool(readonly=False, kind="interact")
    async def interact(self, agent_id: str, action: str, **kwargs):
        """环境交互"""
        pass
```

### 5.3 AlgorithmEnv 实现

```python
class AlgorithmEnv(EnvBase):
    """算法推荐环境 - 模拟信息茧房"""
    
    def __init__(self, cocoon_strength: float = 0.5):
        self.cocoon_strength = cocoon_strength
        self.exposure_history: Dict[str, List[ExposureEvent]] = {}
        self.diversity_index: float = 1.0
    
    @tool(readonly=True, kind="observe")
    async def observe(self, agent_id: str, belief_state: BeliefState) -> str:
        """感知算法推荐内容"""
        # 基于茧房强度和当前信念生成推荐
        recommended = self._generate_recommendation(agent_id, belief_state)
        return recommended
    
    @tool(readonly=True, kind="statistics")
    async def get_statistics(self) -> Dict:
        return {
            "diversity_index": self.diversity_index,
            "cocoon_strength": self.cocoon_strength,
            "total_exposure": sum(len(v) for v in self.exposure_history.values())
        }
    
    def _generate_recommendation(self, agent_id: str, belief: BeliefState) -> str:
        """生成符合茧房效应的推荐内容"""
        # 简化：推荐与当前观点一致的内容
        opinion = belief.to_opinion()
        
        if opinion < -0.3:  # 倾向负面
            return "相关负面分析：专家警告局势将进一步恶化..."
        elif opinion > 0.3:  # 倾向正面
            return "官方最新通报：情况已得到有效控制"
        else:
            return "多方观点交织，建议理性看待"
```

### 5.4 EnvRouter 实现

```python
class ReActRouter:
    """ReAct式环境路由 - AgentSociety启发"""
    
    def __init__(self, env_modules: List[EnvBase], llm_client):
        self.env_modules = {m.__class__.__name__: m for m in env_modules}
        self.llm = llm_client
    
    async def ask(self, question: str, agent_id: str, 
                  belief: BeliefState = None, readonly: bool = True) -> str:
        """Agent向环境提问"""
        
        # 1. 收集可用工具
        tools = self._collect_tools(readonly)
        
        # 2. LLM生成工具调用
        response = await self.llm.generate(
            prompt=self._build_prompt(question, tools),
            tools=tools
        )
        
        # 3. 执行工具调用
        result = await self._execute(response, agent_id, belief)
        
        # 4. 格式化返回
        return self._format_result(result)
    
    def _collect_tools(self, readonly: bool) -> List[Dict]:
        """收集可用工具"""
        tools = []
        for name, module in self.env_modules.items():
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if hasattr(attr, '_is_tool'):
                    if readonly or not attr._readonly:
                        tools.append({
                            "name": f"{name}_{attr_name}",
                            "description": attr.__doc__,
                            "parameters": inspect.signature(attr).parameters
                        })
        return tools
```

---

## 六、通信模式设计

### 6.1 消息类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| **P2P** | Agent间私聊 | 观点交流、影响力传播 |
| **P2G** | Agent→群体广播 | 意见领袖发声 |
| **GroupChat** | 多Agent讨论组 | 社会验证、观点碰撞 |

### 6.2 消息格式

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class MessageType(Enum):
    P2P = "peer_to_peer"
    P2G = "peer_to_group"
    GROUP_CHAT = "group_chat"

class Message(BaseModel):
    """Agent消息"""
    id: str
    sender_id: str
    receiver_ids: List[str]
    message_type: MessageType
    content: str
    timestamp: datetime
    belief_state: Optional[BeliefState]  # 发送时的观点
    
    # 传播相关
   传播概率: Optional[float] = None
    已读: Optional[bool] = False
```

### 6.3 信息传播模型

```python
def compute_propagation_probability(
    sender_belief: BeliefState,
    receiver_belief: BeliefState,
    content_alignment: float
) -> float:
    """计算信息传播概率"""
    
    # 发送者可信度
    credibility = sender_belief.belief_strength * 0.5 + 0.5
    
    # 观点相似度（-1到1）
    similarity = 1 - abs(sender_belief.to_opinion() - receiver_belief.to_opinion()) / 2
    
    # 内容匹配度
    content_factor = content_alignment
    
    # 综合概率
    p = credibility * 0.3 + similarity * 0.4 + content_factor * 0.3
    
    return clamp(p, 0, 1)
```

---

## 七、心理学理论整合

### 7.1 可整合理论

| 理论 | 应用 | 建模方式 |
|------|------|----------|
| **马斯洛需求层次** | 信息寻求动机 | 需求优先级影响信息接受度 |
| **计划行为理论** | 观点→行为意图 | 态度+主观规范+感知控制 |
| **认知失调** | 信息冲突处理 | 失调度→观点调整 |
| **社会认同** | 群体极化 | 群体内同质化 |

### 7.2 需求层次驱动

```python
class NeedsDrivenCognition:
    """基于马斯洛需求层次的信息处理"""
    
    NEED_LEVELS = ["physiological", "safety", "love", "esteem", "cognitive"]
    
    def process_information(
        self, 
        content: str, 
        agent_needs: List[str]
    ) -> float:
        """处理信息，返回观点影响度"""
        
        # 匹配内容与需求层次
        need_match = self._classify_content_by_need(content)
        
        # 高层次需求满足 → 观点更易改变
        if need_match in agent_needs:
            base_impact = 0.3
        else:
            base_impact = 0.1
        
        # 当前需求层次影响
        current_level = agent_needs[0] if agent_needs else "safety"
        level_index = self.NEED_LEVELS.index(current_level)
        level_factor = (level_index + 1) / len(self.NEED_LEVELS)
        
        return base_impact * level_factor
```

---

## 八、数据流设计

### 8.1 推演流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Simulation Flow                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐                  │
│  │  Start   │────▶│  Init    │────▶│  Step    │                  │
│  │  Sim     │     │  Agents  │     │  Loop    │                  │
│  └──────────┘     └──────────┘     └────┬─────┘                  │
│                                          │                         │
│                    ┌─────────────────────┼─────────────────────┐  │
│                    │                     │                     │  │
│                    ▼                     ▼                     ▼  │
│           ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│           │   Observe    │    │   Social    │    │  Truth   │  │
│           │  (Algorithm) │    │  (Network)  │    │ (Debunk) │  │
│           └──────┬───────┘    └──────┬───────┘    └────┬─────┘  │
│                  │                    │                   │        │
│                  └────────────────────┼───────────────────┘        │
│                                         │                          │
│                                         ▼                          │
│                              ┌────────────────────┐               │
│                              │   Skill Pipeline   │               │
│                              │  observation       │               │
│                              │  memory            │               │
│                              │  needs             │               │
│                              │  cognition         │               │
│                              │  plan              │               │
│                              └─────────┬──────────┘               │
│                                        │                          │
│                                        ▼                          │
│                              ┌────────────────────┐               │
│                              │   Belief Update    │               │
│                              │  + Memory Store    │               │
│                              └─────────┬──────────┘               │
│                                        │                          │
│                                        ▼                          │
│                              ┌────────────────────┐               │
│                              │   Message Broadcast│               │
│                              │   (P2P/P2G/Group)  │               │
│                              └─────────┬──────────┘               │
│                                        │                          │
│                                        ▼                          │
│                               ┌────────────────┐                  │
│                               │  Save State    │                  │
│                               │  + Metrics     │                  │
│                               └────────┬───────┘                  │
│                                        │                          │
│                                        ▼                          │
│                               ┌────────────────┐                  │
│                               │   Continue?    │───No──────────▶ End
│                               └───────┬────────┘                  │
│                                       │Yes                         │
│                                       └─────────────────────────┐   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 状态持久化

```python
class ReplayWriter:
    """基于 AgentSociety ReplayWriter 的状态持久化"""
    
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()
    
    def _init_tables(self):
        """初始化表结构"""
        # Agent Profile
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_profile (
                agent_id TEXT PRIMARY KEY,
                name TEXT,
                persona TEXT,
                created_at TIMESTAMP
            )
        """)
        
        # Belief History
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS belief_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                step INTEGER,
                rumor_trust REAL,
                truth_trust REAL,
                belief_strength REAL,
                timestamp TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agent_profile(agent_id)
            )
        """)
        
        # Message Log
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS message_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT,
                receiver_ids TEXT,
                message_type TEXT,
                content TEXT,
                timestamp TIMESTAMP
            )
        """)
    
    def save_belief(self, agent_id: str, step: int, belief: BeliefState):
        """保存信念状态"""
        self.conn.execute(
            """INSERT INTO belief_history 
               (agent_id, step, rumor_trust, truth_trust, belief_strength, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (agent_id, step, belief.rumor_trust, belief.truth_trust, 
             belief.belief_strength, datetime.now())
        )
        self.conn.commit()
```

---

## 九、文件结构规划

```
backend/
├── simulation/
│   ├── engine.py                  # 模拟引擎（保留）
│   ├── engine_dual.py             # 双层网络引擎（保留）
│   ├── agents.py                  # 数学模型Agent（保留）
│   │
│   ├── agent/                     # [NEW] Agent系统
│   │   ├── __init__.py
│   │   ├── base.py               # AgentBase抽象类
│   │   ├── person_agent.py       # PersonAgent实现
│   │   ├── belief_state.py       # 信念状态模型
│   │   ├── memory.py              # 三层记忆
│   │   └── skills/               # [NEW] 技能系统
│   │       ├── __init__.py
│   │       ├── base.py            # Skill基类
│   │       ├── observation.py     # 观察技能
│   │       ├── memory.py          # 记忆技能
│   │       ├── needs.py           # 需求技能
│   │       ├── cognition.py       # 认知技能
│   │       └── plan.py            # 规划技能
│   │
│   ├── env/                       # [NEW] 环境系统
│   │   ├── __init__.py
│   │   ├── base.py                # EnvBase抽象类
│   │   ├── router.py              # EnvRouter实现
│   │   ├── algorithm_env.py       # 算法茧房环境
│   │   ├── social_env.py          # 社交网络环境
│   │   └── truth_env.py           # 辟谣环境
│   │
│   ├── message/                   # [NEW] 通信系统
│   │   ├── __init__.py
│   │   ├── models.py              # 消息模型
│   │   ├── p2p.py                 # P2P通信
│   │   ├── p2g.py                 # 广播通信
│   │   └── group_chat.py          # 群组讨论
│   │
│   ├── storage/                   # [NEW] 持久化
│   │   ├── __init__.py
│   │   ├── replay_writer.py       # 状态持久化
│   │   └── queries.py             # 查询接口
│   │
│   └── (existing files preserved)
│       ├── llm_agents.py
│       ├── llm_agents_dual.py
│       ├── knowledge_evolution.py
│       ├── prediction.py
│       ├── risk_alert.py
│       ├── graph_parser_agent.py
│       └── analyst_agent.py
```

---

## 十、实施路线图

| 阶段 | 任务 | 依赖 | 预计工时 |
|------|------|------|----------|
| **Phase 1** | 三层记忆系统 | - | 2d |
| | Agent基类重构 | 记忆系统 | 1d |
| **Phase 2** | BeliefState建模 | Agent基类 | 1d |
| | Environment基类 | - | 1d |
| **Phase 3** | AlgorithmEnv实现 | Environment基类 | 2d |
| | SocialEnv实现 | Environment基类 | 2d |
| | TruthEnv实现 | Environment基类 | 1d |
| **Phase 4** | EnvRouter实现 | Environment模块 | 2d |
| | Skill基类+Pipeline | Agent基类 | 2d |
| **Phase 5** | 内建技能实现 | Skill Pipeline | 3d |
| | 通信模式实现 | Agent基类 | 2d |
| **Phase 6** | 心理学整合 | Skills | 2d |
| | 持久化增强 | - | 1d |
| **Phase 7** | 集成测试 | 所有模块 | 2d |

---

## 十一、向后兼容策略

### 11.1 接口兼容

```python
# 新旧接口映射
class SimulationEngine:
    """兼容模式：支持新旧接口"""
    
    async def step(self, params: StepParams = None):
        # 新接口
        if hasattr(params, 'belief_state'):
            return await self._step_v3(params)
        
        # 旧接口兼容
        legacy_params = self._convert_legacy(params)
        return await self._step_v2(legacy_params)
```

### 11.2 数据兼容

```python
# 信念状态转换
class BeliefState:
    def to_legacy_opinion(self) -> float:
        """转换为旧版单一观点值"""
        # 新: rumor_trust, truth_trust ∈ [-1, 1]
        # 旧: opinion ∈ [-1, 1]
        return self.truth_trust - self.rumor_trust
    
    @classmethod
    def from_legacy_opinion(cls, opinion: float, strength: float = 0.5):
        """从旧版观点值构造"""
        if opinion > 0:
            return cls(truth_trust=opinion, rumor_trust=0, belief_strength=strength)
        else:
            return cls(truth_trust=0, rumor_trust=-opinion, belief_strength=strength)
```

---

## 十二、附录

### A. AgentSociety 关键参考

- **论文**: arXiv:2502.08691
- **架构**: Model → Agent → Message → Environment → LLM → Tool
- **Skill Pipeline**: metadata-first, lazy loading
- **Memory**: Short-term + Long-term + Cognition buffer

### B. 外部依赖

```python
# requirements.txt 新增
litellm>=1.0.0  # LLM路由
sqlmodel>=0.0.0  # ORM
```

### C. 参考文档

- [AgentSociety README](../AgentSociety_README.md)
- [AgentSociety CLAUDE](../AgentSociety_CLAUDE.md)
- [项目现有文档](./)

---

> 设计方案版本: v3.0  
> 基于: AgentSociety 架构启发  
> 更新日期: 2026-04-22
