"""
ReplayWriter - 推演状态持久化

基于 AgentSociety ReplayWriter 模式:
- Agent Profile 持久化
- Belief History 持久化
- Message Log 持久化
- Exposure Event 持久化
"""
import sqlite3
import json
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
import tempfile

logger = logging.getLogger(__name__)


def _default_replay_db_path() -> Path:
    """Resolve a writable default SQLite path for local runs."""
    try:
        import os
        configured = os.getenv("PROJECTINSIGHT_DATA_DIR", "").strip()
    except Exception:
        configured = ""
    data_dir = Path(configured) if configured else (Path(tempfile.gettempdir()) / "ProjectInsight" / "data")
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "replay.db"


class ReplayWriter:
    """
    推演状态持久化

    使用 SQLite 存储:
    - agent_profile: Agent 配置和初始状态
    - belief_history: 信念演化历史
    - message_log: 消息传播日志
    - exposure_events: 信息暴露记录
    - simulation_meta: 推演元数据

    Note: 线程安全，内部使用锁保护数据库操作。
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = _default_replay_db_path()

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db_lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._init_tables()

        # 连接状态标记
        self._closed = False
    
    def _init_tables(self):
        """初始化表结构"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS simulation_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id TEXT,
                mode TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_steps INTEGER,
                config TEXT
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_profile (
                agent_id INTEGER PRIMARY KEY,
                simulation_id TEXT,
                name TEXT,
                persona_type TEXT,
                persona_desc TEXT,
                susceptibility REAL,
                influence REAL,
                fear_of_isolation REAL,
                initial_opinion REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS belief_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id TEXT,
                agent_id INTEGER,
                step INTEGER,
                rumor_trust REAL,
                truth_trust REAL,
                belief_strength REAL,
                cognitive_closed_need REAL,
                opinion REAL,
                is_silent INTEGER,
                action TEXT,
                emotion TEXT,
                reasoning TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS message_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id TEXT,
                message_id TEXT,
                message_type TEXT,
                sender_id INTEGER,
                receiver_ids TEXT,
                content TEXT,
                opinion REAL,
                propagation_prob REAL,
                step INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS exposure_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id TEXT,
                agent_id INTEGER,
                step INTEGER,
                source TEXT,
                content TEXT,
                alignment REAL,
                trust_delta REAL,
                credibility REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        try:
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_belief_sim_agent ON belief_history(simulation_id, agent_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_message_sim ON message_log(simulation_id, step)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_exposure_sim_agent ON exposure_events(simulation_id, agent_id)")
        except Exception:
            pass
        
        self.conn.commit()
    
    # ==================== 写入操作 ====================
    
    def save_simulation_meta(
        self,
        simulation_id: str,
        mode: str,
        config: Dict,
        total_steps: int = 0
    ):
        """保存推演元数据"""
        with self._db_lock:
            self.conn.execute("""
                INSERT INTO simulation_meta (simulation_id, mode, start_time, total_steps, config)
                VALUES (?, ?, ?, ?, ?)
            """, (
                simulation_id,
                mode,
                datetime.now(timezone.utc).isoformat(),
                total_steps,
                json.dumps(config)
            ))
            self.conn.commit()
    
    def save_agent_profile(
        self,
        agent_id: int,
        simulation_id: str,
        name: str = "",
        persona_type: str = "",
        persona_desc: str = "",
        susceptibility: float = 0.5,
        influence: float = 0.5,
        fear_of_isolation: float = 0.5,
        initial_opinion: float = 0.0
    ):
        """保存 Agent 配置"""
        with self._db_lock:
            self.conn.execute("""
                INSERT OR REPLACE INTO agent_profile
                (agent_id, simulation_id, name, persona_type, persona_desc,
                 susceptibility, influence, fear_of_isolation, initial_opinion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                agent_id, simulation_id, name, persona_type, persona_desc,
                susceptibility, influence, fear_of_isolation, initial_opinion
            ))
            self.conn.commit()

    def save_belief(
        self,
        simulation_id: str,
        agent_id: int,
        step: int,
        rumor_trust: float,
        truth_trust: float,
        belief_strength: float,
        cognitive_closed_need: float,
        opinion: float,
        is_silent: bool = False,
        action: str = "",
        emotion: str = "",
        reasoning: str = ""
    ):
        """保存信念状态"""
        with self._db_lock:
            self.conn.execute("""
                INSERT INTO belief_history
                (simulation_id, agent_id, step, rumor_trust, truth_trust,
                 belief_strength, cognitive_closed_need, opinion, is_silent,
                 action, emotion, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                simulation_id, agent_id, step, rumor_trust, truth_trust,
                belief_strength, cognitive_closed_need, opinion, int(is_silent),
                action, emotion, reasoning
            ))
            self.conn.commit()

    def save_message(
        self,
        simulation_id: str,
        message_id: str,
        message_type: str,
        sender_id: int,
        receiver_ids: List[int],
        content: str,
        opinion: Optional[float] = None,
        propagation_prob: float = 0.5,
        step: int = 0
    ):
        """保存消息"""
        with self._db_lock:
            self.conn.execute("""
                INSERT INTO message_log
                (simulation_id, message_id, message_type, sender_id, receiver_ids,
                 content, opinion, propagation_prob, step)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                simulation_id, message_id, message_type, sender_id,
                json.dumps(receiver_ids), content, opinion, propagation_prob, step
            ))
            self.conn.commit()

    def save_exposure(
        self,
        simulation_id: str,
        agent_id: int,
        step: int,
        source: str,
        content: str,
        alignment: float,
        trust_delta: float = 0.0,
        credibility: float = 0.5
    ):
        """保存暴露事件"""
        with self._db_lock:
            self.conn.execute("""
                INSERT INTO exposure_events
                (simulation_id, agent_id, step, source, content, alignment,
                 trust_delta, credibility)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                simulation_id, agent_id, step, source, content,
                alignment, trust_delta, credibility
            ))
            self.conn.commit()
    
    # ==================== 查询操作 ====================

    def get_belief_history(
        self,
        simulation_id: str,
        agent_id: Optional[int] = None,
        start_step: Optional[int] = None,
        end_step: Optional[int] = None
    ) -> List[Dict]:
        """查询信念历史"""
        query = "SELECT * FROM belief_history WHERE simulation_id = ?"
        params = [simulation_id]

        if agent_id is not None:
            query += " AND agent_id = ?"
            params.append(agent_id)
        if start_step is not None:
            query += " AND step >= ?"
            params.append(start_step)
        if end_step is not None:
            query += " AND step <= ?"
            params.append(end_step)

        query += " ORDER BY agent_id, step ASC"

        with self._db_lock:
            rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_message_log(
        self,
        simulation_id: str,
        step: Optional[int] = None
    ) -> List[Dict]:
        """查询消息日志"""
        query = "SELECT * FROM message_log WHERE simulation_id = ?"
        params = [simulation_id]

        if step is not None:
            query += " AND step = ?"
            params.append(step)

        query += " ORDER BY timestamp ASC"

        with self._db_lock:
            rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_agent_profiles(
        self,
        simulation_id: str
    ) -> List[Dict]:
        """查询 Agent 配置"""
        with self._db_lock:
            rows = self.conn.execute(
                "SELECT * FROM agent_profile WHERE simulation_id = ?",
                (simulation_id,)
            ).fetchall()
        return [dict(row) for row in rows]
    
    def close(self):
        """关闭连接"""
        if self._closed:
            return
        self.conn.close()
        self._closed = True

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, *args):
        """上下文管理器出口，确保连接关闭"""
        self.close()

    def __del__(self):
        if not self._closed:
            try:
                self.close()
            except Exception:
                pass
