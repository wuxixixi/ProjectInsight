"""
AgentMemory - 三层记忆系统

架构:
- Short-term Memory: 最近 N 轮交互，deque 实现
- Long-term Memory: 信念历史持久化，SQLite 实现
- Cognition Buffer: LLM 推理临时缓冲，flush 到长时记忆

参考: AgentSociety Memory 设计
"""
from collections import deque
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import sqlite3
import json
import logging

from .belief_state import BeliefState, ExposureEvent

logger = logging.getLogger(__name__)


class AgentMemory:
    """
    三层记忆系统
    
    设计理念:
    1. 短时记忆: 保持最近 N 轮交互，快速访问
    2. 长时记忆: 持久化信念历史，支持事后分析
    3. 认知缓冲: LLM 推理结果暂存，close 时 flush
    """
    
    def __init__(
        self,
        agent_id: int,
        short_window: int = 10,
        db_path: Optional[str] = None
    ):
        """
        Args:
            agent_id: Agent ID
            short_window: 短时记忆窗口大小
            db_path: SQLite 数据库路径（None 则使用默认路径）
        """
        self.agent_id = agent_id
        
        # 短时记忆: 最近 N 轮交互
        self.short_term: deque = deque(maxlen=short_window)
        
        # 认知缓冲: LLM 推理结果
        self.cognition_buffer: List[Dict[str, Any]] = []
        
        # 长时记忆: SQLite 持久化
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "memory.db"
        self.db_path = Path(db_path)
        self._init_db()
        
        # 统计信息
        self._write_count = 0
        self._read_count = 0
    
    def _init_db(self):
        """初始化 SQLite 数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # 创建表（不带 INDEX）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS belief_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                step INTEGER NOT NULL,
                rumor_trust REAL,
                truth_trust REAL,
                belief_strength REAL,
                cognitive_closed_need REAL,
                opinion REAL,
                reasoning TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS exposure_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                step INTEGER NOT NULL,
                source TEXT,
                content TEXT,
                alignment REAL,
                trust_delta REAL,
                sender_id INTEGER,
                credibility REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cognition_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                step INTEGER NOT NULL,
                skill_name TEXT,
                input_data TEXT,
                output_data TEXT,
                reasoning TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引（分开）
        try:
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_step ON belief_history(agent_id, step)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_exposure ON exposure_log(agent_id, step)")
        except:
            pass  # 索引可能已存在
        
        self.conn.commit()
    
    # ==================== 短时记忆操作 ====================
    
    def add_interaction(self, event: ExposureEvent):
        """添加交互事件到短时记忆"""
        self.short_term.append(event)
    
    def add_belief_snapshot(self, belief: BeliefState, step: int):
        """添加信念快照到短时记忆"""
        snapshot = {
            "type": "belief",
            "step": step,
            "belief": belief.to_dict(),
            "timestamp": datetime.now()
        }
        self.short_term.append(snapshot)
    
    def get_recent_interactions(self, n: int = 5) -> List[ExposureEvent]:
        """获取最近 N 条交互记录"""
        events = [e for e in self.short_term if isinstance(e, ExposureEvent)]
        return events[-n:]
    
    def get_recent_beliefs(self, n: int = 3) -> List[Dict]:
        """获取最近 N 条信念快照"""
        beliefs = [e for e in self.short_term if isinstance(e, dict) and e.get("type") == "belief"]
        return beliefs[-n:]
    
    # ==================== 长时记忆操作 ====================
    
    def store_belief(self, belief: BeliefState, step: int):
        """存储信念到长时记忆"""
        self.conn.execute("""
            INSERT INTO belief_history 
            (agent_id, step, rumor_trust, truth_trust, belief_strength, 
             cognitive_closed_need, opinion, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.agent_id,
            step,
            belief.rumor_trust,
            belief.truth_trust,
            belief.belief_strength,
            belief.cognitive_closed_need,
            belief.to_opinion(),
            belief.reasoning_trace
        ))
        self.conn.commit()
        self._write_count += 1
    
    def store_exposure(self, event: ExposureEvent, step: int):
        """存储暴露事件到长时记忆"""
        self.conn.execute("""
            INSERT INTO exposure_log
            (agent_id, step, source, content, alignment, trust_delta, 
             sender_id, credibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.agent_id,
            step,
            event.source.value,
            event.content,
            event.alignment,
            event.trust_delta,
            event.sender_id,
            event.credibility
        ))
        self.conn.commit()
        self._write_count += 1
    
    def get_belief_history(
        self, 
        start_step: Optional[int] = None,
        end_step: Optional[int] = None
    ) -> List[Dict]:
        """查询信念历史"""
        query = "SELECT * FROM belief_history WHERE agent_id = ?"
        params = [self.agent_id]
        
        if start_step is not None:
            query += " AND step >= ?"
            params.append(start_step)
        if end_step is not None:
            query += " AND step <= ?"
            params.append(end_step)
        
        query += " ORDER BY step ASC"
        
        rows = self.conn.execute(query, params).fetchall()
        self._read_count += 1
        
        return [dict(row) for row in rows]
    
    def get_exposure_history(
        self,
        source: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """查询暴露历史"""
        query = "SELECT * FROM exposure_log WHERE agent_id = ?"
        params = [self.agent_id]
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        query += f" ORDER BY timestamp DESC LIMIT {limit}"
        
        rows = self.conn.execute(query, params).fetchall()
        self._read_count += 1
        
        return [dict(row) for row in rows]
    
    # ==================== 认知缓冲操作 ====================
    
    def add_cognition(
        self,
        skill_name: str,
        step: int,
        input_data: Dict,
        output_data: Dict,
        reasoning: Optional[str] = None
    ):
        """添加认知结果到缓冲"""
        self.cognition_buffer.append({
            "skill_name": skill_name,
            "step": step,
            "input_data": input_data,
            "output_data": output_data,
            "reasoning": reasoning,
            "timestamp": datetime.now()
        })
    
    def flush_cognition(self, step: int):
        """Flush 认知缓冲到长时记忆"""
        for cognition in self.cognition_buffer:
            self.conn.execute("""
                INSERT INTO cognition_log
                (agent_id, step, skill_name, input_data, output_data, reasoning)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self.agent_id,
                cognition.get("step", step),
                cognition["skill_name"],
                json.dumps(cognition["input_data"]),
                json.dumps(cognition["output_data"]),
                cognition.get("reasoning")
            ))
        
        self.conn.commit()
        self._write_count += len(self.cognition_buffer)
        self.cognition_buffer.clear()
    
    # ==================== 综合查询 ====================
    
    def retrieve_relevant(self, query: str, limit: int = 5) -> List[Dict]:
        """
        检索相关记忆
        
        Args:
            query: 查询关键词（简化实现，返回最近记录）
            limit: 返回数量限制
        
        Returns:
            相关记忆列表
        """
        # 简化实现: 返回最近的短时记忆
        recent = list(self.short_term)[-limit:]
        return [
            e if isinstance(e, dict) else e.dict() 
            for e in recent
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        return {
            "agent_id": self.agent_id,
            "short_term_size": len(self.short_term),
            "cognition_buffer_size": len(self.cognition_buffer),
            "write_count": self._write_count,
            "read_count": self._read_count,
            "db_path": str(self.db_path)
        }
    
    def clear(self):
        """清空所有记忆"""
        self.short_term.clear()
        self.cognition_buffer.clear()
        
        # 清空数据库记录
        self.conn.execute("DELETE FROM belief_history WHERE agent_id = ?", (self.agent_id,))
        self.conn.execute("DELETE FROM exposure_log WHERE agent_id = ?", (self.agent_id,))
        self.conn.execute("DELETE FROM cognition_log WHERE agent_id = ?", (self.agent_id,))
        self.conn.commit()
    
    def close(self):
        """关闭数据库连接"""
        # 先 flush 认知缓冲
        if self.cognition_buffer:
            self.flush_cognition(step=0)
        
        self.conn.close()
    
    def __del__(self):
        """析构时关闭连接"""
        try:
            self.close()
        except:
            pass