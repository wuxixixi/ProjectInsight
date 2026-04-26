"""
风险预警引擎

用于实时监控推演状态，检测潜在风险并生成预警

核心功能：
1. 规则引擎：基于阈值的风险检测
2. 趋势分析：检测异常变化趋势
3. 预警等级：高/中/低分级
4. 建议生成：可操作的干预建议
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from enum import Enum
from collections import deque
import numpy as np
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskThresholds:
    """风险阈值配置（支持按场景定制）"""
    # 误信率阈值
    negative_critical: float = 0.75
    negative_high: float = 0.55
    # 极化指数阈值
    polarization_critical: float = 0.8
    polarization_high: float = 0.6
    # 沉默率阈值
    silence_high: float = 0.5
    silence_medium: float = 0.3
    # 真相接受率阈值
    truth_low: float = 0.1
    debunk_ineffective: float = 0.2
    # 风险评分权重
    weight_negative: float = 0.25
    weight_deep_negative: float = 0.25
    weight_polarization: float = 0.25
    weight_silence: float = 0.15
    weight_truth_deficit: float = 0.1
    # 综合风险等级阈值
    score_critical: float = 0.6
    score_high: float = 0.4
    score_medium: float = 0.25


@dataclass
class Alert:
    """预警信息"""
    level: RiskLevel
    metric: str           # 指标名称
    current_value: float  # 当前值
    threshold: float      # 阈值
    message: str          # 预警消息
    suggestion: str       # 建议操作
    timestamp: str        # 时间戳
    
    def to_dict(self) -> Dict:
        return {
            "level": self.level.value,
            "metric": self.metric,
            "current_value": round(self.current_value, 4),
            "threshold": self.threshold,
            "message": self.message,
            "suggestion": self.suggestion,
            "timestamp": self.timestamp
        }


@dataclass
class RiskRule:
    """风险规则"""
    name: str
    metric: str                    # 监控指标
    condition: Optional[Callable[[float], bool]]  # 触发条件（None表示需要特殊处理）
    level: RiskLevel
    message_template: str
    suggestion: str
    threshold: float = 0.0


class RiskAlertEngine:
    """风险预警引擎"""

    def __init__(self, thresholds: Optional[RiskThresholds] = None):
        self.thresholds = thresholds or RiskThresholds()
        self.rules: List[RiskRule] = []
        self.alert_history: deque = deque(maxlen=100)
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """设置默认风险规则"""
        t = self.thresholds  # 简化引用

        # === 负面信念传播风险 ===
        self.rules.append(RiskRule(
            name="negative_critical",
            metric="negative_belief_rate",
            condition=lambda x: x > t.negative_critical,
            level=RiskLevel.CRITICAL,
            message_template=f"🚨 误信率已达 {{value:.0%}}，超过危险阈值{t.negative_critical:.0%}！",
            suggestion="建议立即发布权威回应，加强权威媒体正面引导",
            threshold=t.negative_critical
        ))

        self.rules.append(RiskRule(
            name="negative_high",
            metric="negative_belief_rate",
            condition=lambda x: t.negative_high < x <= t.negative_critical,
            level=RiskLevel.HIGH,
            message_template=f"⚠️ 误信率较高，已达 {{value:.0%}}",
            suggestion="建议尽快准备权威回应材料，选择合适时机发布",
            threshold=t.negative_high
        ))

        self.rules.append(RiskRule(
            name="negative_rising",
            metric="negative_belief_rate",
            condition=None,  # 趋势判断在 check() 中单独处理
            level=RiskLevel.MEDIUM,
            message_template="📈 负面信念传播率快速上升，当前 {value:.0%}",
            suggestion="密切监控舆情动态，做好干预准备",
            threshold=0.0
        ))

        # === 极化风险 ===
        self.rules.append(RiskRule(
            name="polarization_critical",
            metric="polarization_index",
            condition=lambda x: x > t.polarization_critical,
            level=RiskLevel.CRITICAL,
            message_template="🔥 社会极化严重！极化指数达 {value:.2f}，群体对立加剧",
            suggestion="建议平衡报道各方观点，避免激化矛盾",
            threshold=t.polarization_critical
        ))

        self.rules.append(RiskRule(
            name="polarization_high",
            metric="polarization_index",
            condition=lambda x: t.polarization_high < x <= t.polarization_critical,
            level=RiskLevel.HIGH,
            message_template="⚡ 社会分化明显，极化指数 {value:.2f}",
            suggestion="关注极端观点群体，引导理性讨论",
            threshold=t.polarization_high
        ))

        # === 沉默螺旋风险 ===
        self.rules.append(RiskRule(
            name="silence_high",
            metric="silence_rate",
            condition=lambda x: x > t.silence_high,
            level=RiskLevel.HIGH,
            message_template="🤫 沉默的螺旋效应明显，{value:.0%} 用户选择沉默",
            suggestion="营造宽松讨论环境，鼓励多元观点表达",
            threshold=t.silence_high
        ))

        self.rules.append(RiskRule(
            name="silence_medium",
            metric="silence_rate",
            condition=lambda x: t.silence_medium < x <= t.silence_high,
            level=RiskLevel.MEDIUM,
            message_template="😶 沉默率偏高，达 {value:.0%}",
            suggestion="关注少数派观点，避免观点单一化",
            threshold=t.silence_medium
        ))

        # === 真相接受风险 ===
        self.rules.append(RiskRule(
            name="truth_low",
            metric="truth_acceptance_rate",
            condition=lambda x: x < t.truth_low,
            level=RiskLevel.HIGH,
            message_template="📉 真相接受率过低，仅 {value:.0%}",
            suggestion="辟谣效果不佳，需调整辟谣策略或增强可信度",
            threshold=t.truth_low
        ))
        
        # === 辟谣效果风险（辟谣后） ===
        self.rules.append(RiskRule(
            name="debunk_ineffective",
            metric="debunk_effect",
            condition=lambda x: x < 0.2,  # 辟谣效果 = 真相接受变化
            level=RiskLevel.MEDIUM,
            message_template="📢 辟谣效果不明显，真相接受率仅上升 {value:.0%}",
            suggestion="考虑增加辟谣力度或换用更有说服力的证据",
            threshold=0.2
        ))
    
    def check(
        self, 
        current_state: Dict,
        history: List[Dict] = None,
        prediction: Dict = None
    ) -> List[Alert]:
        """
        检查风险
        
        Args:
            current_state: 当前状态
            history: 历史数据（用于趋势分析）
            prediction: 预测结果（用于预测性预警）
        
        Returns:
            触发的预警列表
        """
        alerts = []
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        for rule in self.rules:
            # 获取指标值
            value = current_state.get(rule.metric, 0)

            # 检查条件（None 表示需要特殊处理逻辑）
            triggered = False
            if rule.condition is not None:
                triggered = rule.condition(value)

            # 特殊处理趋势规则
            if rule.name == "negative_rising" and history:
                triggered = self._check_rising_trend(history, "negative_belief_rate", 0.1)
            
            if triggered:
                alert = Alert(
                    level=rule.level,
                    metric=rule.metric,
                    current_value=value,
                    threshold=rule.threshold,
                    message=rule.message_template.format(value=value),
                    suggestion=rule.suggestion,
                    timestamp=now
                )
                alerts.append(alert)
        
        # 基于预测的预警
        if prediction:
            prediction_alerts = self._check_prediction_risks(prediction, now)
            alerts.extend(prediction_alerts)
        
        # 按风险等级排序
        alerts.sort(key=lambda a: {"critical": 0, "high": 1, "medium": 2, "low": 3}[a.level.value])
        
        # 记录历史
        self.alert_history.extend(alerts)
        
        return alerts
    
    def _check_rising_trend(
        self,
        history: List[Dict],
        metric: str,
        threshold: float,
        window: int = 5
    ) -> bool:
        """
        检查上升趋势（基于线性回归斜率）

        Args:
            history: 历史数据
            metric: 指标名
            threshold: 斜率阈值
            window: 回归窗口大小
        """
        if len(history) < 3:
            return False

        # 取最近 window 个数据点
        data = [h.get(metric, 0) for h in history[-window:]]
        n = len(data)
        if n < 3:
            return False

        # 线性回归: y = slope * x + intercept
        x_mean = (n - 1) / 2.0
        y_mean = sum(data) / n
        numerator = sum((i - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return False

        slope = numerator / denominator

        # 斜率为正且超过阈值则判定为上升趋势
        return slope > threshold
    
    def _check_prediction_risks(self, prediction: Dict, now: str) -> List[Alert]:
        """基于预测的风险检查"""
        alerts = []

        # 负面信念预测风险（阈值0标准下调整）
        negative_pred = prediction.get("negative_belief_rate", {})
        pessimistic = negative_pred.get("pessimistic", 0)

        if pessimistic > 0.75:
            alerts.append(Alert(
                level=RiskLevel.HIGH,
                metric="negative_belief_rate_predicted",
                current_value=pessimistic,
                threshold=0.75,
                message=f"🔮 预测预警：误信率可能达到 {pessimistic:.0%}",
                suggestion="建议提前准备干预措施",
                timestamp=now
            ))

        # 极化预测风险
        polar_pred = prediction.get("polarization_index", {})
        polar_pessimistic = polar_pred.get("pessimistic", 0)

        if polar_pessimistic > 0.8:
            alerts.append(Alert(
                level=RiskLevel.HIGH,
                metric="polarization_predicted",
                current_value=polar_pessimistic,
                threshold=0.8,
                message=f"🔮 预测预警：极化指数可能达到 {polar_pessimistic:.2f}",
                suggestion="建议关注群体对立风险",
                timestamp=now
            ))

        return alerts
    
    def get_risk_summary(self, current_state: Dict) -> Dict:
        """获取风险摘要"""
        negative_rate = current_state.get("negative_belief_rate", 0)
        polarization = current_state.get("polarization_index", 0)
        silence_rate = current_state.get("silence_rate", 0)
        truth_rate = current_state.get("truth_acceptance_rate", 0)
        deep_negative_rate = current_state.get("deep_negative_rate", 0)

        # 使用配置权重计算综合风险评分
        # issue #1026: 避免双重计算 deep_negative 已包含在 negative 中
        shallow_negative = max(0, negative_rate - deep_negative_rate)
        t = self.thresholds
        risk_score = (
            shallow_negative * t.weight_negative +
            deep_negative_rate * (t.weight_negative + t.weight_deep_negative) +
            polarization * t.weight_polarization +
            silence_rate * t.weight_silence +
            (1 - truth_rate) * t.weight_truth_deficit
        )

        # 使用配置阈值判定风险等级
        if risk_score > t.score_critical:
            overall_level = RiskLevel.CRITICAL
        elif risk_score > t.score_high:
            overall_level = RiskLevel.HIGH
        elif risk_score > t.score_medium:
            overall_level = RiskLevel.MEDIUM
        else:
            overall_level = RiskLevel.LOW

        return {
            "overall_level": overall_level.value,
            "risk_score": round(risk_score, 3),
            "components": {
                "negative_risk": round(negative_rate, 3),
                "deep_negative_risk": round(deep_negative_rate, 3),
                "polarization_risk": round(polarization, 3),
                "silence_risk": round(silence_rate, 3),
                "truth_deficit": round(1 - truth_rate, 3)
            }
        }
    
    def get_recent_alerts(self, count: int = 5) -> List[Dict]:
        """获取最近的预警"""
        if not self.alert_history:
            return []
        # deque不支持切片，需要转list
        recent_list = list(self.alert_history)
        return [a.to_dict() for a in recent_list[-count:]]
    
    def clear_history(self):
        """清空预警历史"""
        self.alert_history = deque(maxlen=100)


# 全局实例
_risk_engine: Optional[RiskAlertEngine] = None


def get_risk_engine() -> RiskAlertEngine:
    """获取风险预警引擎实例"""
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskAlertEngine()
    return _risk_engine


def reset_risk_engine():
    """重置全局实例（用于测试）"""
    global _risk_engine
    _risk_engine = None
