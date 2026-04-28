"""
智能体群体模型
模拟具有不同观点和社交网络的个体
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
import networkx as nx


class AgentPopulation:
    """
    智能体群体管理

    每个智能体具有:
    - opinion: 观点值 [-1, 1]
    - belief_strength: 信念强度
    - influence: 影响力
    - susceptibility: 易感性
    - fear_of_isolation: 孤立恐惧感
    - is_silent: 是否沉默
    """

    def __init__(
        self,
        size: int = 200,
        initial_negative_spread: float = 0.3,
        initial_rumor_spread: float = None,  # 兼容旧参数名
        network_type: str = "small_world",
        seed: int = 42  # issue #2256: 随机种子确保可复现性
    ):
        self.size = size
        self.network_type = network_type

        # 实例级随机生成器 (issue #2256: 确保可复现性)
        self._rng = np.random.default_rng(seed)

        # 兼容旧参数名
        if initial_rumor_spread is not None:
            initial_negative_spread = initial_rumor_spread

        # 初始化观点分布
        # 阈值0: opinion < 0 为误信，opinion > 0 为正确认知，opinion = 0 为不确定
        # 初始观点分布：负面信念 / 中立 / 正面信念 三段
        # |opinion| < 0.1 为中立，opinion < -0.1 为误信，opinion > 0.1 为正确认知
        self.opinions = np.zeros(size)
        negative_believers = int(size * initial_negative_spread)
        # 中立人群约占 15%~25%，从剩余人群中分配 (issue #2256: 使用实例级RNG)
        neutral_count = int(size * self._rng.uniform(0.15, 0.25))
        neutral_count = min(neutral_count, size - negative_believers)
        positive_believers = size - negative_believers - neutral_count

        # 负面信念者：opinion 在 [-0.8, -0.2]
        self.opinions[:negative_believers] = self._rng.uniform(-0.8, -0.2, negative_believers)
        # 中立人群：opinion 在 [-0.05, 0.05]
        self.opinions[negative_believers:negative_believers + neutral_count] = self._rng.uniform(-0.05, 0.05, neutral_count)
        # 正面信念者：opinion 在 [0.1, 0.5]
        self.opinions[negative_believers + neutral_count:] = self._rng.uniform(0.1, 0.5, positive_believers)

        # 信念强度 - 越强越难改变观点
        self.belief_strength = self._rng.beta(2, 2, size)  # 集中在中等

        # 影响力 - 决定传播能力
        self.influence = self._rng.exponential(0.5, size)
        self.influence = np.clip(self.influence, 0.1, 1.0)

        # 易感性 - 决定被影响的程度
        self.susceptibility = self._rng.beta(2, 5, size)  # 多数人不易被影响

        # 孤立恐惧感 - 用于沉默的螺旋机制
        self.fear_of_isolation = self._rng.beta(2, 2, size)

        # 初始信念强度 - 用于沉默的螺旋机制
        self.conviction = self._rng.beta(2, 2, size)

        # 沉默状态
        self.is_silent = np.zeros(size, dtype=bool)

        # 曝光状态
        self.exposed_to_negative = np.zeros(size, dtype=bool)
        self.exposed_to_negative[:negative_believers] = True
        self.exposed_to_positive = np.zeros(size, dtype=bool)

        # 构建社交网络
        self.network = self._build_network(network_type)

        # 缓存
        self._agent_list_cache: Optional[List[Dict]] = None

    # --- 兼容别名：供外部接口和旧代码使用 ---
    @property
    def exposed_to_rumor(self) -> np.ndarray:
        """兼容别名: exposed_to_negative"""
        return self.exposed_to_negative

    @exposed_to_rumor.setter
    def exposed_to_rumor(self, value: np.ndarray):
        self.exposed_to_negative = value

    @property
    def exposed_to_truth(self) -> np.ndarray:
        """兼容别名: exposed_to_positive"""
        return self.exposed_to_positive

    @exposed_to_truth.setter
    def exposed_to_truth(self, value: np.ndarray):
        self.exposed_to_positive = value

    def _build_network(self, network_type: str) -> nx.Graph:
        """构建社交网络"""
        if network_type == "small_world":
            # 小世界网络 - 模拟真实社交网络
            G = nx.watts_strogatz_graph(
                self.size,
                k=6,           # 每人平均6个连接
                p=0.3,         # 30%重连概率
                seed=42
            )
        elif network_type == "scale_free":
            # 无标度网络 - 存在意见领袖
            G = nx.barabasi_albert_graph(self.size, m=3, seed=42)
        elif network_type == "random":
            G = nx.erdos_renyi_graph(self.size, p=0.05, seed=42)
        else:
            G = nx.watts_strogatz_graph(self.size, k=6, p=0.3, seed=42)

        return G

    def get_neighbors(self, agent_id: int) -> List[int]:
        """获取某智能体的邻居"""
        return list(self.network.neighbors(agent_id))

    def get_edges(self) -> List[Tuple[int, int]]:
        """获取所有边"""
        return list(self.network.edges())

    def invalidate_cache(self):
        """清除缓存，在数据修改后调用"""
        self._agent_list_cache = None

    def to_agent_list(self) -> List[Dict]:
        """转换为可序列化的智能体列表（带缓存）"""
        if self._agent_list_cache is not None:
            return self._agent_list_cache

        agents = []
        for i in range(self.size):
            agents.append({
                "id": i,
                "opinion": float(self.opinions[i]),
                "belief_strength": float(self.belief_strength[i]),
                "influence": float(self.influence[i]),
                "susceptibility": float(self.susceptibility[i]),
                "fear_of_isolation": float(self.fear_of_isolation[i]),
                "conviction": float(self.conviction[i]),
                "is_silent": bool(self.is_silent[i]),
                "exposed_to_negative": bool(self.exposed_to_negative[i]),
                "exposed_to_positive": bool(self.exposed_to_positive[i])
            })
        self._agent_list_cache = agents
        return agents

    def get_opinion_histogram(self, bins: int = 20) -> Dict[str, List]:
        """计算观点分布直方图"""
        hist, edges = np.histogram(self.opinions, bins=bins, range=(-1, 1))
        centers = [(edges[i] + edges[i+1]) / 2 for i in range(len(edges)-1)]
        return {
            "counts": hist.tolist(),
            "centers": centers
        }
