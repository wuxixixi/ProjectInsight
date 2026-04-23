"""
增强版数学模型 - 基于社会心理学理论

理论基础：
1. 沉默的螺旋 (Spiral of Silence) - Noelle-Neumann, 1974
2. 群体极化 (Group Polarization) - Sunstein, 2002
3. 逆火效应 (Backfire Effect) - Nyhan & Reifler, 2010
4. 认知失调 (Cognitive Dissonance) - Festinger, 1957
5. 权威效应 (Authority Effect) - Milgram, 1963
6. 回音室效应 (Echo Chamber Effect)
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

from ..constants import (
    OPINION_THRESHOLD_NEGATIVE, OPINION_THRESHOLD_POSITIVE,
    POLARIZATION_THRESHOLD_NEGATIVE, POLARIZATION_THRESHOLD_POSITIVE
)

logger = logging.getLogger(__name__)


@dataclass
class EnhancedMathParams:
    """增强版数学模型参数"""
    # 原有参数
    cocoon_strength: float = 0.5
    debunk_delay: int = 10

    # 新增参数
    debunk_credibility: float = 0.7      # 辟谣来源可信度 [0, 1]
    authority_factor: float = 0.5        # 权威影响力系数 [0, 1]
    backfire_strength: float = 0.1       # 逆火效应强度 [0, 1]（实证研究建议 0.05-0.1）
    backfire_threshold: float = 0.7      # 逆火效应触发阈值 [0, 1]（信念强度超过此值才可能逆火）
    silence_threshold: float = 0.3       # 沉默阈值 [0, 1]
    polarization_factor: float = 0.3     # 群体极化系数 [0, 1]
    echo_chamber_factor: float = 0.2     # 回音室效应系数 [0, 1]
    cognitive_dissonance_threshold: float = 0.5  # 认知失调阈值


class EnhancedMathModel:
    """
    增强版数学模型

    整合多个社会心理学理论，提供更真实的舆论演化模拟。

    核心机制：
    1. 社交传播影响 - 考虑观点相似度、权威效应、回音室效应
    2. 算法茧房效应 - 基于推荐算法的观点强化
    3. 沉默的螺旋 - 孤立恐惧导致的沉默
    4. 群体极化 - 群体讨论导致观点极端化
    5. 辟谣与逆火效应 - 辟谣信息的影响
    6. 认知失调 - 面对矛盾信息的心理调适
    """

    def __init__(self, params: Optional[EnhancedMathParams] = None, seed: int = None):
        self.params = params or EnhancedMathParams()
        self._rng = np.random.default_rng(seed)

    def compute_step(
        self,
        opinions: np.ndarray,
        belief_strength: np.ndarray,
        influence: np.ndarray,
        susceptibility: np.ndarray,
        fear_of_isolation: np.ndarray,
        neighbors: List[List[int]],
        influencer_ids: List[int] = None,
        response_released: bool = False,
        step_count: int = 0
    ) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        执行单步推演

        Returns:
            new_opinions: 新观点数组
            is_silent: 沉默状态数组
            metrics: 中间指标字典
        """
        size = len(opinions)
        new_opinions = opinions.copy()
        is_silent = np.zeros(size, dtype=bool)
        metrics = {}

        # 1. 计算社交传播影响（增强版）
        social_change = self._enhanced_social_influence(
            opinions, belief_strength, influence, susceptibility, neighbors, influencer_ids
        )
        metrics['social_change_mean'] = float(np.mean(np.abs(social_change)))

        # 2. 算法茧房效应
        cocoon_change = self._algorithmic_cocoon(opinions, belief_strength)
        metrics['cocoon_change_mean'] = float(np.mean(np.abs(cocoon_change)))

        # 3. 沉默的螺旋
        is_silent, silence_pressure = self._spiral_of_silence(
            opinions, belief_strength, fear_of_isolation, neighbors
        )
        metrics['silence_rate'] = float(np.mean(is_silent))

        # 4. 群体极化效应
        polarization_change = self._group_polarization(
            opinions, belief_strength, neighbors, is_silent
        )
        metrics['polarization_change_mean'] = float(np.mean(np.abs(polarization_change)))

        # 5. 辟谣效果（如果已发布）
        debunk_change = np.zeros(size)
        if response_released:
            debunk_change = self._debunk_with_backfire(
                opinions, belief_strength, susceptibility, step_count
            )
            metrics['debunk_change_mean'] = float(np.mean(np.abs(debunk_change)))

        # 6. 认知失调
        dissonance_adjustment = self._cognitive_dissonance(
            opinions, belief_strength, social_change + cocoon_change
        )

        # 综合更新观点
        # 沉默者的观点变化受限
        silence_factor = np.where(is_silent, 0.3, 1.0)
        new_opinions += (social_change + cocoon_change + polarization_change + debunk_change) * silence_factor

        # 应用认知失调调整
        new_opinions += dissonance_adjustment

        # 7. 随机噪声
        noise = self._rng.normal(0, 0.01, size)
        new_opinions += noise

        # 裁剪到有效范围
        new_opinions = np.clip(new_opinions, -1, 1)

        # 更新信念强度（认知失调后可能增强）
        new_belief_strength = self._update_belief_strength(
            belief_strength, opinions, new_opinions, dissonance_adjustment
        )

        metrics['polarization_index'] = float(self._compute_polarization(new_opinions))
        metrics['avg_opinion'] = float(np.mean(new_opinions))

        return new_opinions, new_belief_strength, is_silent, metrics

    def _enhanced_social_influence(
        self,
        opinions: np.ndarray,
        belief_strength: np.ndarray,
        influence: np.ndarray,
        susceptibility: np.ndarray,
        neighbors: List[List[int]],
        influencer_ids: List[int] = None
    ) -> np.ndarray:
        """
        增强版社交传播影响

        改进点：
        1. 观点相似度权重 - 相似观点的人影响更大
        2. 权威效应 - 意见领袖影响力增强
        3. 回音室效应 - 相似观点相互强化
        4. 群体压力 - 从众效应
        """
        size = len(opinions)
        change = np.zeros(size)
        influencer_set = set(influencer_ids or [])

        for i in range(size):
            if not neighbors[i]:
                continue

            neighbor_list = neighbors[i]
            neighbor_opinions = opinions[neighbor_list]
            neighbor_influence = influence[neighbor_list]

            # 观点相似度权重
            similarity_weights = 1 - np.abs(opinions[i] - neighbor_opinions) / 2

            # 权威效应：意见领袖影响力增强
            authority_bonus = np.array([
                self.params.authority_factor if j in influencer_set else 0
                for j in neighbor_list
            ])
            effective_influence = neighbor_influence * (1 + authority_bonus)

            # 综合权重
            weights = effective_influence * similarity_weights
            if weights.sum() > 0:
                weights = weights / weights.sum()
            elif len(neighbor_list) > 0:
                weights = np.ones(len(neighbor_list)) / len(neighbor_list)
            else:
                # 无邻居，跳过此节点
                continue

            # 加权平均观点
            weighted_opinion = np.sum(neighbor_opinions * weights)

            # 基础影响
            base_change = (weighted_opinion - opinions[i]) * susceptibility[i]

            # 回音室效应：当邻居观点与自己同向时，强化效应
            if np.sign(opinions[i]) == np.sign(weighted_opinion) and opinions[i] != 0:
                echo_bonus = self.params.echo_chamber_factor * abs(weighted_opinion - opinions[i])
                base_change += np.sign(opinions[i]) * echo_bonus * susceptibility[i]

            # 信念强度抑制改变
            base_change *= (1 - belief_strength[i] * 0.5)

            change[i] = base_change

        return change

    def _algorithmic_cocoon(
        self,
        opinions: np.ndarray,
        belief_strength: np.ndarray
    ) -> np.ndarray:
        """
        算法茧房效应（向量化实现）

        理论：推荐算法倾向于推送与用户既有观点一致的内容，
        导致观点被强化。

        公式：
        reinforcement = cocoon_strength * α * (1 + |opinion|) * sign(opinion)
        其中 α = 0.03（基于实证研究的系数）

        特点：
        - 观点越极端，强化越强
        - 信念强度越高，茧房效应越弱（已有强信念不易被动摇）
        """
        # 基于实证研究的系数（约为原来的60%，避免过度强化）
        alpha = 0.03

        # 向量化计算
        signs = np.sign(opinions)
        magnitudes = self.params.cocoon_strength * alpha * (1 + np.abs(opinions))
        belief_factors = (1 - belief_strength * 0.5)

        # 观点为0的不受影响
        change = signs * magnitudes * belief_factors
        change[opinions == 0] = 0

        return change

    def _spiral_of_silence(
        self,
        opinions: np.ndarray,
        belief_strength: np.ndarray,
        fear_of_isolation: np.ndarray,
        neighbors: List[List[int]],
        issue_importance: float = 0.5,
        self_efficacy: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        沉默的螺旋（向量化实现）

        理论（Noelle-Neumann, 1974）：
        当个体感知自己的观点属于少数派时，由于害怕孤立，
        会选择沉默，导致多数派声音越来越大。

        扩展：议题重要性（高重要性降低沉默概率）和
        自我效能感（高效能感降低沉默概率）作为调节因素。
        """
        size = len(opinions)
        is_silent = np.zeros(size, dtype=bool)
        silence_pressure = np.zeros(size)

        # 议题重要性调节：高重要性 → 更愿意发声
        importance_factor = 1.0 - issue_importance * 0.5

        # 自我效能感调节：高效能 → 更愿意发声
        efficacy_factor = np.ones(size)
        if self_efficacy is not None:
            efficacy_factor = 1.0 - self_efficacy * 0.4

        # 预计算所有邻居的平均观点
        has_neighbors = np.array([bool(neighbors[i]) for i in range(size)])
        perceived_climate = np.zeros(size)
        for i in range(size):
            if has_neighbors[i]:
                perceived_climate[i] = np.mean(opinions[neighbors[i]])

        # 观点差距
        gap = np.abs(perceived_climate - opinions)

        # 差距超过阈值的产生沉默压力
        pressure_mask = has_neighbors & (gap > self.params.silence_threshold)
        if np.any(pressure_mask):
            isolation_fear = fear_of_isolation[pressure_mask] * gap[pressure_mask]
            conviction = belief_strength[pressure_mask]
            # 应用调节因素
            adjusted_fear = isolation_fear * importance_factor * efficacy_factor[pressure_mask]
            silence_prob = 1 / (1 + np.exp(-(adjusted_fear - conviction) * 3))
            random_vals = self._rng.random(np.sum(pressure_mask))
            silent_local = random_vals < silence_prob
            is_silent[pressure_mask] = silent_local
            silence_pressure[pressure_mask] = adjusted_fear * silent_local

        return is_silent, silence_pressure

    def _group_polarization(
        self,
        opinions: np.ndarray,
        belief_strength: np.ndarray,
        neighbors: List[List[int]],
        is_silent: np.ndarray
    ) -> np.ndarray:
        """
        群体极化效应（向量化实现）

        理论（Sunstein, 2002）：
        群体讨论会导致观点向极端方向移动，
        尤其是当群体初始就有倾向时。
        """
        size = len(opinions)
        change = np.zeros(size)

        # 沉默者不受极化影响
        active_mask = ~is_silent
        has_neighbors = np.array([bool(neighbors[i]) for i in range(size)])
        valid_mask = active_mask & has_neighbors

        # 预计算群体统计量
        group_mean = np.zeros(size)
        group_std = np.zeros(size)
        for i in range(size):
            if has_neighbors[i]:
                neighbor_op = opinions[neighbors[i]]
                group_mean[i] = np.mean(neighbor_op)
                group_std[i] = np.std(neighbor_op)

        # 同向条件
        same_sign = (np.sign(opinions) == np.sign(group_mean)) & (opinions != 0)
        polarize_mask = valid_mask & same_sign

        if np.any(polarize_mask):
            directions = np.sign(opinions[polarize_mask])
            group_consensus = 1 - group_std[polarize_mask] / 2
            magnitudes = self.params.polarization_factor * 0.05 * group_consensus
            magnitudes *= (1 - belief_strength[polarize_mask] * 0.3)
            change[polarize_mask] = directions * magnitudes

        return change

    def _debunk_with_backfire(
        self,
        opinions: np.ndarray,
        belief_strength: np.ndarray,
        susceptibility: np.ndarray,
        step_count: int
    ) -> np.ndarray:
        """
        辟谣与逆火效应（向量化实现）

        理论：
        1. 正常辟谣：向真相方向移动
        2. 逆火效应（Nyhan & Reifler, 2010）：
           当辟谣信息与强信念冲突时，反而强化原有信念
        """
        size = len(opinions)
        change = np.zeros(size)

        # 辟谣基础效果
        base_effect = 0.2 * self.params.debunk_credibility

        # 延迟惩罚（分母与前端滑块范围0-30匹配）
        delay_penalty = max(0.3, 1.0 - (self.params.debunk_delay / 30))

        # 茧房阻尼
        cocoon_resistance = 1.0 - self.params.cocoon_strength * 0.3

        effectiveness = base_effect * delay_penalty * cocoon_resistance

        # 只影响相信谣言者（opinion < 0）
        mask = opinions < 0
        if not np.any(mask):
            return change

        # 个体层面的效果
        individual_effect = effectiveness * (1 - belief_strength * 0.5) * (0.5 + susceptibility * 0.5)

        # 逆火效应检测
        backfire_threshold = self.params.backfire_threshold
        strong_belief_mask = mask & (belief_strength > backfire_threshold)
        weak_belief_mask = mask & ~strong_belief_mask

        # 信念不强的人：正常辟谣
        change[weak_belief_mask] = individual_effect[weak_belief_mask]

        # 信念极强的人：可能逆火
        if np.any(strong_belief_mask):
            backfire_risk = self.params.backfire_strength * (belief_strength[strong_belief_mask] - backfire_threshold)
            random_vals = self._rng.random(np.sum(strong_belief_mask))
            backfire_mask_local = random_vals < backfire_risk

            # 正常辟谣
            normal_effect = individual_effect[strong_belief_mask].copy()
            # 逆火：观点向相反方向移动
            normal_effect[backfire_mask_local] = -normal_effect[backfire_mask_local] * 0.5

            if np.any(backfire_mask_local):
                logger.debug(f"Backfire effect triggered for {np.sum(backfire_mask_local)} agents")

            change[strong_belief_mask] = normal_effect

        return change

    def _cognitive_dissonance(
        self,
        opinions: np.ndarray,
        belief_strength: np.ndarray,
        total_change: np.ndarray
    ) -> np.ndarray:
        """
        认知失调理论（向量化实现）

        理论（Festinger, 1957）：
        当个体接收到与已有信念冲突的信息时，会产生心理不适。
        为了减少这种不适，个体可能：
        1. 改变观点（接受新信息）
        2. 强化信念（拒绝新信息）

        本模型中：当观点变化幅度超过阈值时，
        有概率强化信念而非改变观点
        """
        adjustment = np.zeros(len(opinions))

        change_magnitude = np.abs(total_change)
        mask = change_magnitude > self.params.cognitive_dissonance_threshold

        if np.any(mask):
            dissonance = change_magnitude[mask] - self.params.cognitive_dissonance_threshold
            reinforce_probability = belief_strength[mask] * 0.5
            random_vals = self._rng.random(np.sum(mask))
            reinforce_mask = random_vals < reinforce_probability

            # 强化原有信念，抵消部分变化
            adj = np.zeros(np.sum(mask))
            adj[reinforce_mask] = -total_change[mask][reinforce_mask] * dissonance[reinforce_mask] * 0.5
            adjustment[mask] = adj

        return adjustment

    def _update_belief_strength(
        self,
        old_belief: np.ndarray,
        old_opinions: np.ndarray,
        new_opinions: np.ndarray,
        dissonance_adjustment: np.ndarray,
        mean_reversion_rate: float = 0.02
    ) -> np.ndarray:
        """
        更新信念强度

        规则：
        1. 认知失调可能导致信念强化
        2. 观点大幅变化可能导致信念弱化
        3. 均值回归：防止信念单调递增
        """
        new_belief = old_belief.copy()

        # 认知失调强化信念
        dissonance_boost = np.abs(dissonance_adjustment) * 0.08  # 略微降低系数
        new_belief += dissonance_boost

        # 观点变化大则信念弱化
        opinion_change = np.abs(new_opinions - old_opinions)
        belief_decay = opinion_change * 0.12  # 略微提高系数
        new_belief -= belief_decay

        # 均值回归：长期避免信念单调递增
        belief_mean = 0.5  # 信念强度的长期均衡值
        mean_reversion = (belief_mean - old_belief) * mean_reversion_rate
        new_belief += mean_reversion

        # 裁剪到有效范围
        new_belief = np.clip(new_belief, 0.1, 0.95)

        return new_belief

    @staticmethod
    def compute_polarization_index(opinions: np.ndarray) -> float:
        """
        计算极化指数（双峰指数）

        比标准差更能区分"两个极端阵营"和"均匀分布"。
        值域 [0, 1]，1 表示完全两极分化。

        Args:
            opinions: 观点数组

        Returns:
            极化指数
        """
        n = len(opinions)
        if n < 2:
            return 0.0
        # 使用统一极化阈值（issue #962: 与 constants.py 保持一致）
        left = np.sum(opinions < POLARIZATION_THRESHOLD_NEGATIVE)
        right = np.sum(opinions > POLARIZATION_THRESHOLD_POSITIVE)
        center = n - left - right
        # 双峰指数：极端派占比减去中间派占比，归一化到 [0, 1]
        bimodal = (left + right - center) / n
        # 结合标准差以兼顾分散程度
        std_component = min(1.0, float(np.std(opinions)))
        return min(1.0, max(0.0, 0.6 * bimodal + 0.4 * std_component))

    def _compute_polarization(self, opinions: np.ndarray) -> float:
        """计算极化指数（实例方法委托给静态方法）"""
        return self.compute_polarization_index(opinions)

    def get_theory_explanation(self) -> Dict:
        """
        返回理论解释（供前端展示）
        """
        return {
            "social_influence": {
                "name": "社交传播影响",
                "theory": "社会影响理论 (Social Influence Theory)",
                "formula": "Δo = (ō_neighbors - o_i) × susceptibility × (1 - belief × 0.5)",
                "enhancements": [
                    "观点相似度权重：相似观点的人影响更大",
                    "权威效应：意见领袖影响力增强",
                    "回音室效应：相似观点相互强化"
                ]
            },
            "algorithmic_cocoon": {
                "name": "算法茧房效应",
                "theory": "信息茧房理论 (Information Cocoon)",
                "formula": "Δo = cocoon × 0.03 × (1 + |o|) × sign(o) × (1 - belief × 0.5)",
                "explanation": "推荐算法推送与用户观点一致的内容，导致观点强化。观点越极端，强化越强。"
            },
            "spiral_of_silence": {
                "name": "沉默的螺旋",
                "theory": "Noelle-Neumann (1974)",
                "formula": "P(silent) = σ(isolation_fear × gap - conviction)",
                "explanation": "当个体感知自己是少数派时，因害怕孤立而选择沉默，导致多数派声音越来越大。"
            },
            "group_polarization": {
                "name": "群体极化",
                "theory": "Sunstein (2002)",
                "formula": "Δo = sign(o) × polarization × 0.05 × consensus",
                "explanation": "群体讨论导致观点向极端方向移动，群体越一致，极化越强。"
            },
            "backfire_effect": {
                "name": "逆火效应",
                "theory": "Nyhan & Reifler (2010)",
                "formula": "if belief > 0.7: P(backfire) = backfire_strength × (belief - 0.7)",
                "explanation": "当辟谣与强信念冲突时，部分人反而更坚信谣言。"
            },
            "cognitive_dissonance": {
                "name": "认知失调",
                "theory": "Festinger (1957)",
                "formula": "if |Δo| > threshold: P(reject) = belief × 0.5",
                "explanation": "面对与信念冲突的信息时，可能强化原有信念而非改变观点。"
            }
        }

    def get_parameter_explanation(self) -> Dict:
        """
        返回参数解释（供前端展示）
        """
        return {
            "cocoon_strength": {
                "name": "算法茧房强度",
                "range": "0 ~ 1",
                "default": 0.5,
                "effect": "推荐算法强化观点的程度，越高观点越容易极端化"
            },
            "debunk_credibility": {
                "name": "辟谣可信度",
                "range": "0 ~ 1",
                "default": 0.7,
                "effect": "官方辟谣信息的可信度，越高辟谣效果越好"
            },
            "authority_factor": {
                "name": "权威影响力系数",
                "range": "0 ~ 1",
                "default": 0.5,
                "effect": "意见领袖影响力的增强倍数，越高大V影响力越强"
            },
            "backfire_strength": {
                "name": "逆火效应强度",
                "range": "0 ~ 1",
                "default": 0.3,
                "effect": "辟谣时产生反效果的概率，越高辟谣越可能强化谣言信念"
            },
            "silence_threshold": {
                "name": "沉默阈值",
                "range": "0 ~ 1",
                "default": 0.3,
                "effect": "观点差距超过此阈值时产生沉默压力"
            },
            "polarization_factor": {
                "name": "群体极化系数",
                "range": "0 ~ 1",
                "default": 0.3,
                "effect": "群体讨论导致观点极端化的程度"
            },
            "echo_chamber_factor": {
                "name": "回音室效应系数",
                "range": "0 ~ 1",
                "default": 0.2,
                "effect": "相似观点相互强化的程度"
            }
        }
