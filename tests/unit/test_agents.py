"""
AgentPopulation 单元测试
测试智能体群体的初始化、网络构建和状态管理
"""
import pytest
import numpy as np
import networkx as nx
from backend.simulation.agents import AgentPopulation


class TestAgentPopulationInit:
    """测试 AgentPopulation 初始化"""

    def test_default_initialization(self):
        """测试默认参数初始化"""
        pop = AgentPopulation()

        assert pop.size == 200
        assert pop.network_type == "small_world"
        assert len(pop.opinions) == 200
        assert len(pop.belief_strength) == 200
        assert len(pop.influence) == 200
        assert len(pop.susceptibility) == 200

    def test_custom_initialization(self):
        """测试自定义参数初始化"""
        pop = AgentPopulation(
            size=100,
            initial_rumor_spread=0.4,
            network_type="scale_free"
        )

        assert pop.size == 100
        assert pop.network_type == "scale_free"
        assert len(pop.opinions) == 100

    def test_opinion_distribution(self):
        """测试观点分布初始化"""
        pop = AgentPopulation(size=100, initial_rumor_spread=0.3)

        # 前30%应该是谣言相信者 (opinion < 0)
        rumor_believers = sum(pop.opinions < 0)
        assert rumor_believers >= 25  # 允许一定随机性

        # 观点值应在 [-1, 1] 范围内
        assert np.all(pop.opinions >= -1)
        assert np.all(pop.opinions <= 1)

    def test_belief_strength_range(self):
        """测试信念强度范围"""
        pop = AgentPopulation()

        # 信念强度应在 [0, 1] 范围内
        assert np.all(pop.belief_strength >= 0)
        assert np.all(pop.belief_strength <= 1)

    def test_influence_range(self):
        """测试影响力范围"""
        pop = AgentPopulation()

        # 影响力应在 [0.1, 1.0] 范围内 (被 clip 过)
        assert np.all(pop.influence >= 0.1)
        assert np.all(pop.influence <= 1.0)

    def test_susceptibility_range(self):
        """测试易感性范围"""
        pop = AgentPopulation()

        # 易感性应在 [0, 1] 范围内
        assert np.all(pop.susceptibility >= 0)
        assert np.all(pop.susceptibility <= 1)

    def test_exposure_initialization(self):
        """测试曝光状态初始化"""
        pop = AgentPopulation(size=100, initial_rumor_spread=0.3)

        # 初始谣言曝光者数量
        exposed_count = sum(pop.exposed_to_rumor)
        assert exposed_count == 30

        # 初始无真相曝光
        assert sum(pop.exposed_to_truth) == 0


class TestNetworkBuilding:
    """测试网络构建"""

    def test_small_world_network(self):
        """测试小世界网络构建"""
        pop = AgentPopulation(size=50, network_type="small_world")

        assert isinstance(pop.network, nx.Graph)
        assert pop.network.number_of_nodes() == 50
        # 小世界网络应有一定连接
        assert pop.network.number_of_edges() > 0

    def test_scale_free_network(self):
        """测试无标度网络构建"""
        pop = AgentPopulation(size=50, network_type="scale_free")

        assert isinstance(pop.network, nx.Graph)
        assert pop.network.number_of_nodes() == 50
        assert pop.network.number_of_edges() > 0

    def test_random_network(self):
        """测试随机网络构建"""
        pop = AgentPopulation(size=50, network_type="random")

        assert isinstance(pop.network, nx.Graph)
        assert pop.network.number_of_nodes() == 50

    def test_invalid_network_type_defaults_to_small_world(self):
        """测试无效网络类型默认为小世界网络"""
        pop = AgentPopulation(size=50, network_type="invalid_type")

        assert isinstance(pop.network, nx.Graph)
        assert pop.network.number_of_nodes() == 50

    def test_network_connectivity(self):
        """测试网络连通性"""
        pop = AgentPopulation(size=100, network_type="small_world")

        # 小世界网络应该是连通的
        assert nx.is_connected(pop.network)


class TestAgentMethods:
    """测试智能体方法"""

    def test_get_neighbors(self):
        """测试获取邻居"""
        pop = AgentPopulation(size=50)

        for i in range(50):
            neighbors = pop.get_neighbors(i)
            assert isinstance(neighbors, list)
            # 每个节点应该有邻居 (小世界网络特性)
            assert len(neighbors) > 0

    def test_get_edges(self):
        """测试获取边列表"""
        pop = AgentPopulation(size=50)

        edges = pop.get_edges()
        assert isinstance(edges, list)
        assert len(edges) > 0
        # 边应该是元组
        assert isinstance(edges[0], tuple)

    def test_to_agent_list(self):
        """测试转换为智能体列表"""
        pop = AgentPopulation(size=10)

        agents = pop.to_agent_list()

        assert len(agents) == 10
        assert all('id' in a for a in agents)
        assert all('opinion' in a for a in agents)
        assert all('belief_strength' in a for a in agents)
        assert all('influence' in a for a in agents)
        assert all('susceptibility' in a for a in agents)

    def test_get_opinion_histogram(self):
        """测试观点直方图"""
        pop = AgentPopulation(size=100)

        hist = pop.get_opinion_histogram(bins=20)

        assert 'counts' in hist
        assert 'centers' in hist
        assert len(hist['counts']) == 20
        assert len(hist['centers']) == 20
        # 所有计数应为非负
        assert all(c >= 0 for c in hist['counts'])


class TestReproducibility:
    """测试可重复性"""

    def test_same_seed_same_network(self):
        """测试相同种子产生相同网络"""
        # 由于 seed=42 固定，两次初始化应产生相同网络
        pop1 = AgentPopulation(size=50, network_type="small_world")
        pop2 = AgentPopulation(size=50, network_type="small_world")

        edges1 = set(pop1.get_edges())
        edges2 = set(pop2.get_edges())

        assert edges1 == edges2
