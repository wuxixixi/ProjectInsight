"""
预测与风险预警路由
"""
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import state
from ..simulation.prediction import PredictionModel
from ..simulation.risk_alert import get_risk_engine, RiskLevel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["prediction"])


def _get_current_state_dict() -> Optional[dict]:
    """从引擎获取当前状态字典（兼容新旧键名，issue #744: 添加 deep_negative_rate）"""
    engine = state.engine
    if engine is None or engine.current_state is None:
        return None
    current = engine.current_state
    return {
        # 核心指标
        "negative_belief_rate": current.negative_belief_rate,
        "rumor_spread_rate": current.negative_belief_rate,  # 别名
        "truth_acceptance_rate": current.positive_belief_rate,
        "positive_belief_rate": current.positive_belief_rate,
        "polarization_index": current.polarization_index,
        "silence_rate": current.silence_rate,
        "avg_opinion": current.avg_opinion,
        # issue #744: 添加深度误信/正确认知率
        "deep_negative_rate": current.deep_negative_rate,
        "deep_positive_rate": current.deep_positive_rate,
    }


@router.get("/prediction")
async def get_prediction():
    """
    获取预测结果

    基于历史数据预测未来趋势，返回预测区间
    """
    if state.engine is None:
        return JSONResponse(
            content={"success": False, "error": "推演引擎未初始化"},
            status_code=400
        )

    if len(state.engine.history) < 3:
        return {
            "success": True,
            "data": {
                "available": False,
                "message": "历史数据不足，需要至少3步推演后才能预测",
                "min_steps_required": 3,
                "current_steps": len(state.engine.history)
            }
        }

    # 初始化或更新预测模型
    if state.prediction_model is None:
        state.prediction_model = PredictionModel()

    state.prediction_model.update(state.engine.history)

    # 获取当前状态
    current_state = _get_current_state_dict()
    if current_state is None:
        return JSONResponse(
            content={"success": False, "error": "当前推演状态不可用"},
            status_code=400
        )

    # 执行预测
    prediction = state.prediction_model.predict(current_state)

    # 获取干预建议
    recommendation = state.prediction_model.get_intervention_recommendation(current_state, prediction)

    # 获取预测轨迹（用于前端绘图）
    trajectory = state.prediction_model.get_trajectory(current_state, steps=10)

    return {
        "success": True,
        "data": {
            "available": True,
            "current_step": state.engine.step_count,
            "prediction": prediction,
            "trajectory": trajectory,
            "recommendation": recommendation
        }
    }


@router.get("/risk-alerts")
async def get_risk_alerts():
    """
    获取风险预警

    检测当前状态的风险并返回预警列表
    """
    if state.engine is None:
        return JSONResponse(
            content={"success": False, "error": "推演引擎未初始化"},
            status_code=400
        )

    # 获取风险引擎
    risk_engine = get_risk_engine()

    # 获取当前状态
    current_state = _get_current_state_dict()
    if current_state is None:
        return JSONResponse(
            content={"success": False, "error": "当前推演状态不可用"},
            status_code=400
        )

    # 执行风险检查
    alerts = risk_engine.check(current_state, state.engine.history)

    # 获取风险摘要
    risk_summary = risk_engine.get_risk_summary(current_state)

    return {
        "success": True,
        "data": {
            "alerts": [a.to_dict() for a in alerts],
            "risk_summary": risk_summary,
            "recent_alerts": risk_engine.get_recent_alerts(5)
        }
    }


@router.get("/prediction/trajectory")
async def get_prediction_trajectory(steps: int = 10):
    """
    获取预测轨迹

    用于前端绘制预测曲线
    """
    if state.engine is None:
        return JSONResponse(
            content={"success": False, "error": "推演引擎未初始化"},
            status_code=400
        )

    if len(state.engine.history) < 3:
        return {
            "success": True,
            "data": {
                "available": False,
                "message": "历史数据不足"
            }
        }

    if state.prediction_model is None:
        state.prediction_model = PredictionModel()

    state.prediction_model.update(state.engine.history)

    # 获取当前状态（issue #745: 使用副本避免修改共享字典）
    current_state = _get_current_state_dict()
    if current_state is None:
        return JSONResponse(
            content={"success": False, "error": "当前推演状态不可用"},
            status_code=400
        )
    state_copy = dict(current_state)
    state_copy.pop("silence_rate", None)

    trajectory = state.prediction_model.get_trajectory(state_copy, steps=steps)

    return {
        "success": True,
        "data": {
            "available": True,
            "trajectory": trajectory,
            "steps": steps
        }
    }


@router.post("/risk-alerts/clear")
async def clear_risk_alerts():
    """清空预警历史"""
    if state.engine is None:
        return JSONResponse(
            content={"success": False, "error": "推演引擎未初始化"},
            status_code=400
        )
    risk_engine = get_risk_engine()
    risk_engine.clear_history()
    return {"success": True, "message": "预警历史已清空"}


@router.get("/docs/usage")
async def get_usage_docs():
    """获取使用说明文档"""
    try:
        import os
        docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "README.md")
        with open(docs_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "content": content}
    except OSError as e:
        return {"success": False, "error": f"文档读取失败: {e}"}
