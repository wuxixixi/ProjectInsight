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
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


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
    condition: Callable[[float], bool]  # 触发条件
    level: RiskLevel
    message_template: str
    suggestion: str
    threshold: float = 0.0


class RiskAlertEngine:
    """风险预警引擎"""
    
    def __init__(self):
        self.rules: List[RiskRule] = []
        self.alert_history: List[Alert] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """设置默认风险规则"""
        
        # === 谣言传播风险 ===
        self.rules.append(RiskRule(
            name="rumor_critical",
            metric="rumor_spread_rate",
            condition=lambda x: x > 0.7,
            level=RiskLevel.CRITICAL,
            message_template="🚨 谣言传播率已达到 {value:.0%}，超过危险阈值70%！",
            suggestion="建议立即发布官方辟谣，加强权威媒体正面引导",
            threshold=0.7
        ))
        
        self.rules.append(RiskRule(
            name="rumor_high",
            metric="rumor_spread_rate",
            condition=lambda x: 0.5 < x <= 0.7,
            level=RiskLevel.HIGH,
            message_template="⚠️ 谣言传播率较高，已达 {value:.0%}",
            suggestion="建议尽快准备辟谣材料，选择合适时机发布",
            threshold=0.5
        ))
        
        self.rules.append(RiskRule(
            name="rumor_rising",
            metric="rumor_spread_rate",
            condition=lambda x: False,  # 需要历史数据判断
            level=RiskLevel.MEDIUM,
            message_template="📈 谣言传播率快速上升，当前 {value:.0%}",
            suggestion="密切监控舆情动态，做好干预准备",
            threshold=0.0
        ))
        
        # === 极化风险 ===
        self.rules.append(RiskRule(
            name="polarization_critical",
            metric="polarization_index",
            condition=lambda x: x > 0.8,
            level=RiskLevel.CRITICAL,
            message_template="🔥 社会极化严重！极化指数达 {value:.2f}，群体对立加剧",
            suggestion="建议平衡报道各方观点，避免激化矛盾",
            threshold=0.8
        ))
        
        self.rules.append(RiskRule(
            name="polarization_high",
            metric="polarization_index",
            condition=lambda x: 0.6 < x <= 0.8,
            level=RiskLevel.HIGH,
            message_template="⚡ 社会分化明显，极化指数 {value:.2f}",
            suggestion="关注极端观点群体，引导理性讨论",
            threshold=0.6
        ))
        
        # === 沉默螺旋风险 ===
        self.rules.append(RiskRule(
            name="silence_high",
            metric="silence_rate",
            condition=lambda x: x > 0.5,
            level=RiskLevel.HIGH,
            message_template="🤫 沉默的螺旋效应明显，{value:.0%} 用户选择沉默",
            suggestion="营造宽松讨论环境，鼓励多元观点表达",
            threshold=0.5
        ))
        
        self.rules.append(RiskRule(
            name="silence_medium",
            metric="silence_rate",
            condition=lambda x: 0.3 < x <= 0.5,
            level=RiskLevel.MEDIUM,
            message_template="😶 沉默率偏高，达 {value:.0%}",
            suggestion="关注少数派观点，避免观点单一化",
            threshold=0.3
        ))
        
        # === 真相接受风险 ===
        self.rules.append(RiskRule(
            name="truth_low",
            metric="truth_acceptance_rate",
            condition=lambda x: x < 0.1,
            level=RiskLevel.HIGH,
            message_template="📉 真相接受率过低，仅 {value:.0%}",
            suggestion="辟谣效果不佳，需调整辟谣策略或增强可信度",
            threshold=0.1
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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for rule in self.rules:
            # 获取指标值
            value = current_state.get(rule.metric, 0)
            
            # 检查条件
            triggered = rule.condition(value)
            
            # 特殊处理趋势规则
            if rule.name == "rumor_rising" and history:
                triggered = self._check_rising_trend(history, "rumor_spread_rate", 0.1)
            
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
        threshold: float
    ) -> bool:
        """检查上升趋势"""
        if len(history) < 3:
            return False
        
        recent = [h.get(metric, 0) for h in history[-3:]]
        if len(recent) < 3:
            return False
        
        # 检查连续上升且总变化超过阈值
        if recent[0] < recent[1] < recent[2]:
            change = recent[2] - recent[0]
            return change > threshold
        
        return False
    
    def _check_prediction_risks(self, prediction: Dict, now: str) -> List[Alert]:
        """基于预测的风险检查"""
        alerts = []
        
        # 谣言预测风险
        rumor_pred = prediction.get("rumor_spread_rate", {})
        pessimistic = rumor_pred.get("pessimistic", 0)
        
        if pessimistic > 0.7:
            alerts.append(Alert(
                level=RiskLevel.HIGH,
                metric="rumor_spread_rate_predicted",
                current_value=pessimistic,
                threshold=0.7,
                message=f"🔮 预测预警：谣言传播率可能达到 {pessimistic:.0%}",
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
        rumor_rate = current_state.get("rumor_spread_rate", 0)
        polarization = current_state.get("polarization_index", 0)
        silence_rate = current_state.get("silence_rate", 0)
        truth_rate = current_state.get("truth_acceptance_rate", 0)
        
        # 综合风险评分
        risk_score = (
            rumor_rate * 0.4 +
            polarization * 0.3 +
            silence_rate * 0.2 +
            (1 - truth_rate) * 0.1
        )
        
        if risk_score > 0.7:
            overall_level = RiskLevel.CRITICAL
        elif risk_score > 0.5:
            overall_level = RiskLevel.HIGH
        elif risk_score > 0.3:
            overall_level = RiskLevel.MEDIUM
        else:
            overall_level = RiskLevel.LOW
        
        return {
            "overall_level": overall_level.value,
            "risk_score": round(risk_score, 3),
            "components": {
                "rumor_risk": round(rumor_rate, 3),
                "polarization_risk": round(polarization, 3),
                "silence_risk": round(silence_rate, 3),
                "truth_deficit": round(1 - truth_rate, 3)
            }
        }
    
    def get_recent_alerts(self, count: int = 5) -> List[Dict]:
        """获取最近的预警"""
        recent = self.alert_history[-count:] if self.alert_history else []
        return [a.to_dict() for a in recent]
    
    def clear_history(self):
        """清空预警历史"""
        self.alert_history = []


# 全局实例
_risk_engine: Optional[RiskAlertEngine] = None


def get_risk_engine() -> RiskAlertEngine:
    """获取风险预警引擎实例"""
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskAlertEngine()
    return _risk_engine
