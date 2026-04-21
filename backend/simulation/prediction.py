"""
预测模型 - 蒙特卡洛模拟

用于新闻推演模式，提供有置信度的预测区间

核心功能：
1. 基于历史演化数据，预测未来趋势
2. 计算乐观/期望/悲观预测区间
3. 输出置信度

语义重构：rumor_spread_rate → negative_belief_rate（误信率）
          truth_acceptance_rate → positive_belief_rate（正确认知率）
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class PredictionConfig:
    """预测模型配置"""
    # 蒙特卡洛模拟次数
    n_simulations: int = 100

    # 预测步数（预测未来N步）
    forecast_steps: int = 10

    # 置信水平
    confidence_level: float = 0.95

    # 是否启用自适应参数
    adaptive: bool = True

    # 历史数据最小长度（少于此时不做预测）
    min_history_length: int = 3


@dataclass
class PredictionInterval:
    """预测区间"""
    expected: float      # 期望值
    optimistic: float    # 乐观值（下界，对负面信念传播越低越好）
    pessimistic: float   # 悲观值（上界，对负面信念传播越高越糟）
    confidence: float    # 置信度

    def to_dict(self) -> Dict:
        return {
            "expected": round(self.expected, 4),
            "optimistic": round(self.optimistic, 4),
            "pessimistic": round(self.pessimistic, 4),
            "confidence": self.confidence
        }


class MonteCarloPredictor:
    """蒙特卡洛预测器

    基于历史演化轨迹，通过多次模拟预测未来趋势

    方法：
    1. 从历史数据估计参数（趋势、波动）
    2. 运行多次模拟
    3. 统计分布得到预测区间
    """

    def __init__(self, config: PredictionConfig = None):
        self.config = config or PredictionConfig()

        # 存储历史数据
        self.history: List[Dict] = []

        # 参数估计
        self.trend_estimate: Dict[str, float] = {}
        self.volatility_estimate: Dict[str, float] = {}

        # 预测缓存
        self._cached_prediction: Optional[Dict] = None

    def update_history(self, history: List[Dict]):
        """更新历史数据"""
        self.history = history
        self._estimate_parameters()
        self._cached_prediction = None

    def _estimate_parameters(self):
        """从历史数据估计趋势和波动参数"""
        if len(self.history) < 2:
            return

        # 提取时间序列（兼容模式访问历史数据）
        negative_rates = [h.get("negative_belief_rate", h.get("rumor_spread_rate", 0)) for h in self.history]
        positive_rates = [h.get("positive_belief_rate", h.get("truth_acceptance_rate", 0)) for h in self.history]
        polarizations = [h.get("polarization_index", 0) for h in self.history]

        # 估计趋势（平均变化率）
        def calc_trend(series):
            if len(series) < 2:
                return 0
            changes = np.diff(series)
            return np.mean(changes)

        self.trend_estimate = {
            "negative_belief_rate": calc_trend(negative_rates),
            "positive_belief_rate": calc_trend(positive_rates),
            "polarization_index": calc_trend(polarizations)
        }

        # 估计波动（标准差）
        def calc_volatility(series):
            if len(series) < 2:
                return 0.1
            return max(np.std(series), 0.01)  # 最小波动

        self.volatility_estimate = {
            "negative_belief_rate": calc_volatility(negative_rates),
            "positive_belief_rate": calc_volatility(positive_rates),
            "polarization_index": calc_volatility(polarizations)
        }

        logger.debug(f"参数估计: trend={self.trend_estimate}, volatility={self.volatility_estimate}")

    def predict(self, current_state: Dict) -> Dict[str, PredictionInterval]:
        """
        执行预测

        Args:
            current_state: 当前状态 {negative_belief_rate, positive_belief_rate, polarization_index, ...}

        Returns:
            {指标名: PredictionInterval}
        """
        if len(self.history) < self.config.min_history_length:
            logger.warning(f"历史数据不足({len(self.history)}<{self.config.min_history_length})，返回当前值")
            return self._fallback_prediction(current_state)

        # 检查缓存
        if self._cached_prediction:
            return self._cached_prediction

        # 运行蒙特卡洛模拟
        metrics = ["negative_belief_rate", "positive_belief_rate", "polarization_index"]
        predictions = {}

        for metric in metrics:
            current_value = current_state.get(metric, 0.5)
            predictions[metric] = self._predict_metric(metric, current_value)

        # 缓存结果
        self._cached_prediction = predictions

        return predictions

    def _predict_metric(self, metric: str, current_value: float) -> PredictionInterval:
        """预测单个指标"""
        trend = self.trend_estimate.get(metric, 0)
        volatility = self.volatility_estimate.get(metric, 0.05)

        # 蒙特卡洛模拟
        final_values = []

        for _ in range(self.config.n_simulations):
            # 随机游走模型
            value = current_value
            for _ in range(self.config.forecast_steps):
                # 趋势 + 随机波动
                noise = np.random.normal(0, volatility)
                change = trend + noise
                value = np.clip(value + change, 0, 1)
            final_values.append(value)

        # 计算预测区间
        final_values = np.array(final_values)

        # 对于负面信念传播率，optimistic是下界（越低越好），pessimistic是上界
        alpha = 1 - self.config.confidence_level

        expected = np.mean(final_values)

        if metric == "negative_belief_rate":
            # 负面信念传播率：乐观=低，悲观=高
            optimistic = np.percentile(final_values, alpha * 50)  # 下界
            pessimistic = np.percentile(final_values, 100 - alpha * 50)  # 上界
        elif metric == "positive_belief_rate":
            # 正确认知率：乐观=高，悲观=低
            optimistic = np.percentile(final_values, 100 - alpha * 50)  # 上界
            pessimistic = np.percentile(final_values, alpha * 50)  # 下界
        else:
            # 其他指标：正常顺序
            optimistic = np.percentile(final_values, alpha * 50)
            pessimistic = np.percentile(final_values, 100 - alpha * 50)

        return PredictionInterval(
            expected=expected,
            optimistic=optimistic,
            pessimistic=pessimistic,
            confidence=self.config.confidence_level
        )

    def _fallback_prediction(self, current_state: Dict) -> Dict[str, PredictionInterval]:
        """当数据不足时的回退预测"""
        predictions = {}

        for metric in ["negative_belief_rate", "positive_belief_rate", "polarization_index"]:
            value = current_state.get(metric, 0.5)
            predictions[metric] = PredictionInterval(
                expected=value,
                optimistic=max(0, value - 0.1),
                pessimistic=min(1, value + 0.1),
                confidence=0.5  # 低置信度
            )

        return predictions

    def get_trajectory_prediction(self, current_state: Dict, steps: int = 10) -> Dict[str, List[float]]:
        """
        预测未来轨迹（用于前端绘图）

        Returns:
            {metric: [expected_values...], metric_optimistic: [...], metric_pessimistic: [...]}
        """
        if len(self.history) < self.config.min_history_length:
            return self._fallback_trajectory(current_state, steps)

        metrics = ["negative_belief_rate", "positive_belief_rate", "polarization_index"]
        trajectories = {}

        for metric in metrics:
            current_value = current_state.get(metric, 0.5)
            trend = self.trend_estimate.get(metric, 0)
            volatility = self.volatility_estimate.get(metric, 0.05)

            expected_path = [current_value]
            optimistic_path = [current_value]
            pessimistic_path = [current_value]

            for _ in range(steps):
                # 期望路径
                next_expected = np.clip(expected_path[-1] + trend, 0, 1)
                expected_path.append(next_expected)

                # 区间扩展
                spread = volatility * np.sqrt(len(optimistic_path))
                if metric == "negative_belief_rate":
                    optimistic_path.append(max(0, next_expected - spread))
                    pessimistic_path.append(min(1, next_expected + spread))
                elif metric == "positive_belief_rate":
                    optimistic_path.append(min(1, next_expected + spread))
                    pessimistic_path.append(max(0, next_expected - spread))
                else:
                    optimistic_path.append(max(0, next_expected - spread))
                    pessimistic_path.append(min(1, next_expected + spread))

            trajectories[metric] = expected_path
            trajectories[f"{metric}_optimistic"] = optimistic_path
            trajectories[f"{metric}_pessimistic"] = pessimistic_path

        return trajectories

    def _fallback_trajectory(self, current_state: Dict, steps: int) -> Dict[str, List[float]]:
        """回退轨迹预测"""
        trajectories = {}

        for metric in ["negative_belief_rate", "positive_belief_rate", "polarization_index"]:
            value = current_state.get(metric, 0.5)
            trajectories[metric] = [value] * (steps + 1)
            trajectories[f"{metric}_optimistic"] = [max(0, value - 0.1)] * (steps + 1)
            trajectories[f"{metric}_pessimistic"] = [min(1, value + 0.1)] * (steps + 1)

        return trajectories


class PredictionModel:
    """预测模型入口类

    整合多种预测方法，提供统一接口
    """

    def __init__(self, config: PredictionConfig = None):
        self.config = config or PredictionConfig()
        self.mc_predictor = MonteCarloPredictor(self.config)

    def update(self, history: List[Dict]):
        """更新历史数据"""
        self.mc_predictor.update_history(history)

    def predict(self, current_state: Dict) -> Dict:
        """
        执行预测

        Returns:
            {
                "negative_belief_rate": PredictionInterval,
                "positive_belief_rate": PredictionInterval,
                "polarization_index": PredictionInterval,
                "trajectory": {...}  # 可选
            }
        """
        predictions = self.mc_predictor.predict(current_state)

        return {
            metric: interval.to_dict()
            for metric, interval in predictions.items()
        }

    def get_trajectory(self, current_state: Dict, steps: int = 10) -> Dict:
        """获取预测轨迹"""
        return self.mc_predictor.get_trajectory_prediction(current_state, steps)

    def get_intervention_recommendation(
        self,
        current_state: Dict,
        prediction: Dict
    ) -> Dict:
        """
        生成干预建议

        基于预测结果，推荐最佳干预时机和强度

        Returns:
            {
                "risk_level": "low"/"medium"/"high"/"critical",
                "best_timing": 推荐干预步数,
                "suggested_strength": 建议干预强度,
                "strategies": [...],  # 具体干预策略
                "priority_entities": [...],  # 优先干预的关键实体
                "message": "...",
                "reasoning": "..."  # 决策依据
            }
        """
        negative_prediction = prediction.get("negative_belief_rate", prediction.get("rumor_spread_rate", {}))
        positive_prediction = prediction.get("positive_belief_rate", prediction.get("truth_acceptance_rate", {}))
        polarization_prediction = prediction.get("polarization_index", {})

        expected_negative = negative_prediction.get("expected", 0.5)
        pessimistic_negative = negative_prediction.get("pessimistic", 0.5)
        expected_positive = positive_prediction.get("expected", 0.3)
        expected_polarization = polarization_prediction.get("expected", 0.3)

        # 当前状态
        current_negative = current_state.get("negative_belief_rate", current_state.get("rumor_spread_rate", 0.3))
        current_step = current_state.get("step", 0)

        # 风险评估（多维度）
        risk_level = "low"
        risk_factors = []

        if pessimistic_negative > 0.7:
            risk_level = "critical"
            risk_factors.append("负面信念传播率预测超70%")
        elif pessimistic_negative > 0.5:
            risk_level = "high"
            risk_factors.append("负面信念传播率预测超50%")
        elif pessimistic_negative > 0.35:
            risk_level = "medium"
            risk_factors.append("负面信念传播率呈上升趋势")

        # 极化风险
        if expected_polarization > 0.6:
            if risk_level != "critical":
                risk_level = max(risk_level, "medium")
            risk_factors.append(f"群体极化指数{expected_polarization:.2f}")

        # 计算最佳干预时机
        # 基于负面信念传播速率（预期增长率）
        if current_negative < 0.2:
            best_timing = 5  # 早期，可稍作观察
        elif current_negative < 0.4:
            best_timing = 3  # 中期，需尽快介入
        else:
            best_timing = 1  # 晚期，需立即干预

        # 计算建议干预强度
        if risk_level == "critical":
            suggested_strength = 0.9
        elif risk_level == "high":
            suggested_strength = 0.7
        elif risk_level == "medium":
            suggested_strength = 0.5
        else:
            suggested_strength = 0.3

        # 生成具体干预策略
        strategies = self._generate_strategies(
            risk_level, current_negative, expected_positive, expected_polarization
        )

        # 分析窗口收窄情况
        window_status = "充足"
        if current_negative > 0.4:
            window_status = "收窄"
        if current_negative > 0.6:
            window_status = "紧迫"

        # 决策依据
        reasoning = self._generate_reasoning(
            current_negative, expected_negative, expected_polarization, risk_factors
        )

        recommendation = {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "best_timing": best_timing,
            "suggested_strength": suggested_strength,
            "strategies": strategies,
            "window_status": window_status,
            "metrics": {
                "current_negative_rate": current_negative,
                "expected_negative_rate": expected_negative,
                "expected_positive_rate": expected_positive,
                "expected_polarization": expected_polarization
            },
            "message": self._generate_message(risk_level, expected_negative, window_status),
            "reasoning": reasoning
        }

        return recommendation

    def _generate_strategies(
        self,
        risk_level: str,
        current_negative: float,
        expected_positive: float,
        polarization: float
    ) -> List[Dict]:
        """生成具体干预策略"""
        strategies = []

        # 基础策略：权威回应信息投放
        strategies.append({
            "type": "debunk",
            "name": "权威回应",
            "description": "通过官方渠道发布权威回应信息",
            "effectiveness": 0.8 if risk_level in ["high", "critical"] else 0.6,
            "cost": "high"
        })

        # 负面信念传播早期：预防性沟通
        if current_negative < 0.3:
            strategies.append({
                "type": "prevent",
                "name": "预防性科普",
                "description": "在误信大规模传播前进行科普教育",
                "effectiveness": 0.7,
                "cost": "medium"
            })

        # 正确认知率低：增强正确认知传播
        if expected_positive < 0.3:
            strategies.append({
                "type": "amplify",
                "name": "正确认知放大",
                "description": "通过意见领袖和权威媒体放大正确认知传播",
                "effectiveness": 0.65,
                "cost": "medium"
            })

        # 极化严重：去极化干预
        if polarization > 0.5:
            strategies.append({
                "type": "depolarize",
                "name": "去极化沟通",
                "description": "促进不同观点群体间的理性对话",
                "effectiveness": 0.5,
                "cost": "high",
                "note": "效果较慢，适合中长期"
            })

        # 高风险：多管齐下
        if risk_level == "critical":
            strategies.append({
                "type": "multi",
                "name": "多渠道联动",
                "description": "同时使用多种干预渠道",
                "effectiveness": 0.9,
                "cost": "very_high"
            })

        return strategies

    def _generate_reasoning(
        self,
        current_negative: float,
        expected_negative: float,
        polarization: float,
        risk_factors: List[str]
    ) -> str:
        """生成决策依据说明"""
        trend = "上升" if expected_negative > current_negative else "稳定" if expected_negative == current_negative else "下降"

        reasoning = f"当前负面信念传播率{current_negative*100:.0f}%，预测{trend}趋势（{expected_negative*100:.0f}%）。"

        if risk_factors:
            reasoning += f"风险因素：{'；'.join(risk_factors)}。"

        if polarization > 0.5:
            reasoning += "群体存在极化倾向，单一权威回应效果可能受限。"

        return reasoning

    def _generate_message(self, risk_level: str, expected_negative: float, window_status: str) -> str:
        """生成干预建议消息"""
        if risk_level == "critical":
            return f"🚨 临界风险：预计负面信念传播率达{expected_negative*100:.0f}%，干预窗口{window_status}，建议立即多渠道联动干预"
        elif risk_level == "high":
            return f"🚨 高风险：预计负面信念传播率达{expected_negative*100:.0f}%，建议立即加强权威回应"
        elif risk_level == "medium":
            return f"⚠️ 中风险：预计负面信念传播率{expected_negative*100:.0f}%，建议适时介入，优先投放权威信息"
        else:
            return f"✅ 低风险：舆情相对稳定，建议继续保持观察，适时进行预防性沟通"
