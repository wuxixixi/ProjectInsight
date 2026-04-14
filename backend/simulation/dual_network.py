"""
双层模态信息场 - 网络拓扑引擎
Public_Graph (公域网络): 无标度网络，存在超级节点
Private_Graph (私域网络): 随机块模型，形成多个紧密社群
"""
import numpy as np
import networkx as nx
from typing import List, Dict, Tuple, Optional
import random


class DualLayerNetwork:
    """
    双层网络拓扑

    公域网络: 无标度网络 (Barabasi-Albert)，模拟微博/抖音等公共平台
    私域网络: 随机块模型 (SBM)，模拟微信群/朋友圈等私密社群
    """

    def __init__(
        self,
        size: int = 200,
        public_m: int = 3,           # BA模型参数：每个新节点连接的边数
        num_communities: int = 8,    # 私域社群数量
        intra_community_prob: float = 0.3,   # 社群内连接概率
        inter_community_prob: float = 0.01,  # 社群间连接概率
        seed: int = 42
    ):
        self.size = size
        self.public_m = public_m
        self.num_communities = min(num_communities, size // 10)  # 确保每个社群至少10人
        self.intra_community_prob = intra_community_prob
        self.inter_community_prob = inter_community_prob
        self.seed = seed

        # 设置随机种子
        np.random.seed(seed)
        random.seed(seed)

        # 构建双层网络
        self.public_graph = self._build_public_network()
        self.private_graph = self._build_private_network()

        # 社群分配 (每个 Agent 属于哪个私域社群)
        self.community_membership = self._assign_communities()

        # 识别超级节点 (公域网络中度最高的节点)
        self.influencer_ids = self._identify_influencers()

    def _build_public_network(self) -> nx.Graph:
        """
        构建公域网络 - 无标度网络 (Barabasi-Albert)

        特点:
        - 存在少数拥有大量连接的"超级节点"（大V）
        - 符合真实社交媒体的幂律分布
        """
        G = nx.barabasi_albert_graph(self.size, self.public_m, seed=self.seed)
        return G

    def _build_private_network(self) -> nx.Graph:
        """
        构建私域网络 - 随机块模型 (Stochastic Block Model)

        特点:
        - 形成多个紧密的、相对独立的社群
        - 社群内连接紧密，社群间连接稀疏
        - 模拟微信群、朋友圈等私域流量
        """
        # 计算每个社群的大小
        community_sizes = self._compute_community_sizes()

        # 构建 SBM 的概率矩阵
        p_matrix = self._build_probability_matrix()

        # 使用 SBM 生成网络
        G = nx.stochastic_block_model(
            community_sizes,
            p_matrix,
            seed=self.seed
        )

        # 确保所有节点都存在 (SBM 可能产生孤立节点)
        for i in range(self.size):
            if not G.has_node(i):
                G.add_node(i)

        return G

    def _compute_community_sizes(self) -> List[int]:
        """计算每个社群的大小"""
        base_size = self.size // self.num_communities
        remainder = self.size % self.num_communities

        sizes = [base_size] * self.num_communities
        # 将余数分配给前面的社群
        for i in range(remainder):
            sizes[i] += 1

        return sizes

    def _build_probability_matrix(self) -> List[List[float]]:
        """
        构建 SBM 的概率矩阵

        对角线元素 = 社群内连接概率 (高)
        非对角线元素 = 社群间连接概率 (低)
        """
        n = self.num_communities
        matrix = [[self.inter_community_prob] * n for _ in range(n)]

        # 设置社群内连接概率
        for i in range(n):
            matrix[i][i] = self.intra_community_prob

        return matrix

    def _assign_communities(self) -> Dict[int, int]:
        """
        为每个节点分配社群归属

        Returns:
            {agent_id: community_id}
        """
        membership = {}

        # 从 SBM 图中提取社群信息
        if hasattr(self.private_graph, 'graph') and 'partition' in self.private_graph.graph:
            partition = self.private_graph.graph['partition']
            for comm_id, nodes in enumerate(partition):
                for node in nodes:
                    membership[node] = comm_id
        else:
            # 备用方案：根据节点 ID 分配社群
            community_sizes = self._compute_community_sizes()
            current_community = 0
            node_count = 0

            for i in range(self.size):
                membership[i] = current_community
                node_count += 1

                if current_community < len(community_sizes) and node_count >= community_sizes[current_community]:
                    current_community += 1
                    node_count = 0

        return membership

    def _identify_influencers(self, top_k: int = 5) -> List[int]:
        """
        识别公域网络中的超级节点 (大V)

        选取度最高的 top_k 个节点
        """
        degrees = dict(self.public_graph.degree())
        sorted_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)
        return [node for node, _ in sorted_nodes[:top_k]]

    def get_public_neighbors(self, agent_id: int) -> List[int]:
        """获取公域网络邻居"""
        return list(self.public_graph.neighbors(agent_id))

    def get_private_neighbors(self, agent_id: int) -> List[int]:
        """获取私域网络邻居"""
        return list(self.private_graph.neighbors(agent_id))

    def get_all_neighbors(self, agent_id: int) -> Dict[str, List[int]]:
        """
        获取 Agent 的所有邻居

        Returns:
            {"public": [...], "private": [...]}
        """
        return {
            "public": self.get_public_neighbors(agent_id),
            "private": self.get_private_neighbors(agent_id)
        }

    def get_community(self, agent_id: int) -> int:
        """获取 Agent 所属的私域社群"""
        return self.community_membership.get(agent_id, 0)

    def get_community_members(self, community_id: int) -> List[int]:
        """获取社群的所有成员"""
        return [aid for aid, cid in self.community_membership.items() if cid == community_id]

    def is_influencer(self, agent_id: int) -> bool:
        """判断 Agent 是否为超级节点"""
        return agent_id in self.influencer_ids

    def get_public_edges(self) -> List[Tuple[int, int]]:
        """获取公域网络所有边"""
        return list(self.public_graph.edges())

    def get_private_edges(self) -> List[Tuple[int, int]]:
        """获取私域网络所有边"""
        return list(self.private_graph.edges())

    def get_network_stats(self) -> Dict:
        """获取网络统计信息"""
        public_degrees = [d for _, d in self.public_graph.degree()]
        private_degrees = [d for _, d in self.private_graph.degree()]

        return {
            "public": {
                "num_nodes": self.size,
                "num_edges": self.public_graph.number_of_edges(),
                "avg_degree": np.mean(public_degrees),
                "max_degree": max(public_degrees),
                "num_influencers": len(self.influencer_ids)
            },
            "private": {
                "num_nodes": self.size,
                "num_edges": self.private_graph.number_of_edges(),
                "avg_degree": np.mean(private_degrees),
                "num_communities": self.num_communities
            }
        }


class MessageRouter:
    """
    消息路由器

    根据信息来源渠道和 Agent 决策，模拟信息在双层网络中的传播
    """

    # 渠道类型
    CHANNEL_PUBLIC = "public"    # 公域广播
    CHANNEL_PRIVATE = "private"  # 私域转发
    CHANNEL_BOTH = "both"        # 双发
    CHANNEL_NONE = "none"        # 不转发

    # 信息来源类型
    SOURCE_PUBLIC = "public"     # 来自公域（微博大V等）
    SOURCE_PRIVATE = "private"   # 来自私域（微信群好友等）

    def __init__(self, dual_network: DualLayerNetwork):
        self.network = dual_network

    def get_info_context(
        self,
        agent_id: int,
        source_channel: str,
        news_content: str,
        sender_id: Optional[int] = None
    ) -> Dict:
        """
        构建信息上下文

        Args:
            agent_id: 接收信息的 Agent ID
            source_channel: 信息来源渠道 ("public" 或 "private")
            news_content: 新闻内容
            sender_id: 发送者 ID (可选，用于私域信息)

        Returns:
            信息上下文字典
        """
        context = {
            "source_channel": source_channel,
            "news_content": news_content,
            "sender_id": sender_id
        }

        if source_channel == self.SOURCE_PUBLIC:
            # 公域信息：来自微博大V等
            context["source_description"] = "微博公共时间线"
            context["trust_weight"] = 0.6  # 对陌生人的信任度较低
            context["sender_type"] = "大V" if sender_id and self.network.is_influencer(sender_id) else "普通用户"

        else:
            # 私域信息：来自微信群好友等
            community_id = self.network.get_community(agent_id)
            context["source_description"] = f"微信群（社群{community_id + 1}）"
            context["trust_weight"] = 0.9  # 对亲友的信任度较高
            context["sender_type"] = "亲友"

        return context

    def route_message(
        self,
        agent_id: int,
        publish_channel: str
    ) -> Dict[str, List[int]]:
        """
        根据发布渠道决定消息路由

        Args:
            agent_id: 发布消息的 Agent ID
            publish_channel: 发布渠道 ("public", "private", "both", "none")

        Returns:
            {"public": [接收者ID列表], "private": [接收者ID列表]}
        """
        receivers = {"public": [], "private": []}

        if publish_channel == self.CHANNEL_NONE:
            return receivers

        if publish_channel in [self.CHANNEL_PUBLIC, self.CHANNEL_BOTH]:
            # 公域广播：所有公域粉丝都能看到
            receivers["public"] = self.network.get_public_neighbors(agent_id)

        if publish_channel in [self.CHANNEL_PRIVATE, self.CHANNEL_BOTH]:
            # 私域转发：只有私域好友能看到
            receivers["private"] = self.network.get_private_neighbors(agent_id)

        return receivers

    def calculate_trust_factor(self, source_channel: str, sender_is_influencer: bool = False) -> float:
        """
        计算信任因子

        不同渠道的信息有不同的信任权重
        """
        if source_channel == self.SOURCE_PRIVATE:
            return 0.9  # 私域信息信任度高
        else:
            return 0.7 if sender_is_influencer else 0.5  # 大V 比普通用户更可信
