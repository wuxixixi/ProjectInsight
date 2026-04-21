"""
Phase 2 单元测试：预测模型和风险预警引擎

测试内容：
1. 预测模型 - 蒙特卡洛模拟
2. 预测区间计算
3. 风险预警引擎
4. 干预建议生成
"""

import pytest
import numpy as np
from backend.simulation.prediction import (
    PredictionConfig,
    PredictionInterval,
    MonteCarloPredictor,
    PredictionModel
)
from backend.simulation.risk_alert import (
    RiskLevel,
    Alert,
    RiskRule,
    RiskAlertEngine,
    get_risk_engine
)


class TestPredictionInterval:
    """测试预测区间数据结构"""
    
    def test_creation(self):
        """测试创建预测区间"""
        interval = PredictionInterval(
            expected=0.5,
            optimistic=0.3,
            pessimistic=0.7,
            confidence=0.95
        )
        
        assert interval.expected == 0.5
        assert interval.optimistic == 0.3
        assert interval.pessimistic == 0.7
        assert interval.confidence == 0.95
    
    def test_to_dict(self):
        """测试转换为字典"""
        interval = PredictionInterval(
            expected=0.5,
            optimistic=0.3,
            pessimistic=0.7,
            confidence=0.95
        )
        
        d = interval.to_dict()
        
        assert d["expected"] == 0.5
        assert d["optimistic"] == 0.3
        assert d["pessimistic"] == 0.7
        assert d["confidence"] == 0.95


class TestMonteCarloPredictor:
    """测试蒙特卡洛预测器"""
    
    def test_initialization(self):
        """测试初始化"""
        config = PredictionConfig(n_simulations=50, forecast_steps=5)
        predictor = MonteCarloPredictor(config)
        
        assert predictor.config.n_simulations == 50
        assert predictor.config.forecast_steps == 5
    
    def test_update_history(self):
        """测试更新历史数据"""
        predictor = MonteCarloPredictor()

        history = [
            {"negative_belief_rate": 0.3, "positive_belief_rate": 0.1, "polarization_index": 0.4},
            {"negative_belief_rate": 0.35, "positive_belief_rate": 0.12, "polarization_index": 0.45},
            {"negative_belief_rate": 0.4, "positive_belief_rate": 0.15, "polarization_index": 0.5},
        ]

        predictor.update_history(history)

        assert len(predictor.history) == 3
        assert "negative_belief_rate" in predictor.trend_estimate
        assert "negative_belief_rate" in predictor.volatility_estimate
    
    def test_predict_with_sufficient_history(self):
        """测试有足够历史数据时的预测"""
        config = PredictionConfig(n_simulations=100, forecast_steps=10)
        predictor = MonteCarloPredictor(config)

        # 创建有趋势的历史数据
        history = [
            {"negative_belief_rate": 0.3 + i * 0.02,
             "positive_belief_rate": 0.1 + i * 0.01,
             "polarization_index": 0.4 + i * 0.01}
            for i in range(5)
        ]

        predictor.update_history(history)

        current_state = {
            "negative_belief_rate": 0.4,
            "positive_belief_rate": 0.15,
            "polarization_index": 0.45
        }

        predictions = predictor.predict(current_state)

        # 验证预测结果结构
        assert "negative_belief_rate" in predictions
        assert "positive_belief_rate" in predictions
        assert "polarization_index" in predictions

        # 验证预测区间合理性
        negative_pred = predictions["negative_belief_rate"]
        assert 0 <= negative_pred.optimistic <= 1
        assert 0 <= negative_pred.expected <= 1
        assert 0 <= negative_pred.pessimistic <= 1
        assert negative_pred.optimistic <= negative_pred.expected <= negative_pred.pessimistic
    
    def test_predict_with_insufficient_history(self):
        """测试历史数据不足时的回退预测"""
        predictor = MonteCarloPredictor()

        # 不更新历史，测试回退逻辑
        current_state = {
            "negative_belief_rate": 0.5,
            "positive_belief_rate": 0.2,
            "polarization_index": 0.5
        }

        predictions = predictor.predict(current_state)

        # 应该返回回退预测
        assert predictions["negative_belief_rate"].expected == 0.5
        assert predictions["negative_belief_rate"].confidence == 0.5
    
    def test_trajectory_prediction(self):
        """测试轨迹预测"""
        config = PredictionConfig(n_simulations=50)
        predictor = MonteCarloPredictor(config)

        history = [
            {"negative_belief_rate": 0.3 + i * 0.02}
            for i in range(5)
        ]
        predictor.update_history(history)

        current_state = {"negative_belief_rate": 0.4}
        trajectory = predictor.get_trajectory_prediction(current_state, steps=5)

        assert "negative_belief_rate" in trajectory
        assert len(trajectory["negative_belief_rate"]) == 6  # 当前 + 5步


class TestPredictionModel:
    """测试预测模型入口类"""
    
    def test_prediction_model_integration(self):
        """测试预测模型整合功能"""
        model = PredictionModel()

        history = [
            {"negative_belief_rate": 0.3 + i * 0.02,
             "positive_belief_rate": 0.1 + i * 0.01,
             "polarization_index": 0.4}
            for i in range(5)
        ]

        model.update(history)

        current_state = {
            "negative_belief_rate": 0.4,
            "positive_belief_rate": 0.15,
            "polarization_index": 0.45
        }

        predictions = model.predict(current_state)

        assert "negative_belief_rate" in predictions
        assert "positive_belief_rate" in predictions
        assert "polarization_index" in predictions
    
    def test_intervention_recommendation(self):
        """测试干预建议生成"""
        model = PredictionModel()

        current_state = {"negative_belief_rate": 0.4}
        prediction = {
            "negative_belief_rate": {"expected": 0.5, "pessimistic": 0.75}
        }

        recommendation = model.get_intervention_recommendation(current_state, prediction)

        assert "risk_level" in recommendation
        assert "best_timing" in recommendation
        assert "suggested_strength" in recommendation
        assert "message" in recommendation

        # 高悲观预测(pessimistic > 0.7)应该产生关键风险建议
        assert recommendation["risk_level"] == "critical"


class TestRiskAlertEngine:
    """测试风险预警引擎"""
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        engine = RiskAlertEngine()
        
        assert len(engine.rules) > 0
        assert engine.alert_history == []
    
    def test_check_critical_negative_belief(self):
        """测试检测关键负面信念风险"""
        engine = RiskAlertEngine()

        current_state = {
            "negative_belief_rate": 0.8,  # 超过75%阈值（阈值0标准下调整）
            "positive_belief_rate": 0.1,
            "polarization_index": 0.5,
            "silence_rate": 0.2
        }

        alerts = engine.check(current_state)

        # 应该触发关键预警
        critical_alerts = [a for a in alerts if a.level == RiskLevel.CRITICAL]
        assert len(critical_alerts) > 0
    
    def test_check_high_polarization(self):
        """测试检测高极化风险"""
        engine = RiskAlertEngine()

        current_state = {
            "negative_belief_rate": 0.3,
            "positive_belief_rate": 0.1,
            "polarization_index": 0.85,  # 超过80%阈值
            "silence_rate": 0.2
        }

        alerts = engine.check(current_state)

        # 应该触发极化预警
        polar_alerts = [a for a in alerts if "polarization" in a.metric]
        assert len(polar_alerts) > 0
    
    def test_check_silence_spiral(self):
        """测试检测沉默螺旋风险"""
        engine = RiskAlertEngine()

        current_state = {
            "negative_belief_rate": 0.3,
            "positive_belief_rate": 0.1,
            "polarization_index": 0.5,
            "silence_rate": 0.55  # 超过50%阈值
        }

        alerts = engine.check(current_state)

        # 应该触发沉默螺旋预警
        silence_alerts = [a for a in alerts if a.metric == "silence_rate"]
        assert len(silence_alerts) > 0
    
    def test_prediction_risk_check(self):
        """测试基于预测的风险检查"""
        engine = RiskAlertEngine()

        current_state = {
            "negative_belief_rate": 0.3,
            "positive_belief_rate": 0.1,
            "polarization_index": 0.5,
            "silence_rate": 0.2
        }

        prediction = {
            "negative_belief_rate": {"pessimistic": 0.8}  # 高悲观预测（阈值0标准下调整）
        }

        alerts = engine.check(current_state, prediction=prediction)

        # 应该包含预测预警
        pred_alerts = [a for a in alerts if "predicted" in a.metric]
        assert len(pred_alerts) > 0
    
    def test_risk_summary(self):
        """测试风险摘要"""
        engine = RiskAlertEngine()

        current_state = {
            "negative_belief_rate": 0.5,
            "positive_belief_rate": 0.2,
            "polarization_index": 0.6,
            "silence_rate": 0.3
        }

        summary = engine.get_risk_summary(current_state)

        assert "overall_level" in summary
        assert "risk_score" in summary
        assert "components" in summary
        assert 0 <= summary["risk_score"] <= 1
    
    def test_alert_history(self):
        """测试预警历史记录"""
        engine = RiskAlertEngine()

        current_state = {
            "negative_belief_rate": 0.75,
            "positive_belief_rate": 0.1,
            "polarization_index": 0.5,
            "silence_rate": 0.2
        }

        engine.check(current_state)
        assert len(engine.alert_history) > 0

        recent = engine.get_recent_alerts(2)
        assert len(recent) <= 2

        engine.clear_history()
        assert len(engine.alert_history) == 0
    
    def test_global_engine(self):
        """测试全局引擎实例"""
        engine1 = get_risk_engine()
        engine2 = get_risk_engine()
        
        assert engine1 is engine2  # 应该是同一个实例


class TestRiskRule:
    """测试风险规则"""
    
    def test_rule_creation(self):
        """测试规则创建"""
        rule = RiskRule(
            name="test_rule",
            metric="negative_belief_rate",
            condition=lambda x: x > 0.5,
            level=RiskLevel.HIGH,
            message_template="负面信念率过高: {value}",
            suggestion="建议干预",
            threshold=0.5
        )

        assert rule.name == "test_rule"
        assert rule.condition(0.6) == True
        assert rule.condition(0.4) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
