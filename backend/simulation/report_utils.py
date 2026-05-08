"""Shared helpers for simulation and analyst reports."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def infer_credibility_label(credibility: Optional[str]) -> str:
    value = (credibility or "不确定").strip()
    return value if value in {"高可信", "低可信", "不确定"} else "不确定"


def metric_semantics(credibility: Optional[str]) -> Dict[str, str]:
    label = infer_credibility_label(credibility)
    if label == "高可信":
        return {"believe": "正确认知", "reject": "误信", "deep_believe": "正确认知", "deep_reject": "误信"}
    if label == "低可信":
        return {"believe": "误信", "reject": "正确认知", "deep_believe": "误信", "deep_reject": "正确认知"}
    return {"believe": "相信", "reject": "拒绝", "deep_believe": "深度相信", "deep_reject": "深度拒绝"}


def format_rate_pair(
    label: str,
    start: float,
    end: float,
    *,
    changed_label: Optional[str] = None,
) -> str:
    if abs(end - start) < 1e-9:
        arrow = "→ 稳定"
    elif end > start:
        arrow = "↑ 上升"
    else:
        arrow = "↓ 下降"
    return f"| {label} | {start:.1%} | {end:.1%} | {arrow if changed_label is None else changed_label + ': ' + arrow} |"


def summarize_history_trend(
    history: Sequence[Dict[str, Any]],
    *,
    key: str,
    fallback_keys: Iterable[str] = (),
    label: str,
    reverse: bool = False,
) -> str:
    values = [float(_pick_metric(item, key, fallback_keys)) for item in history if _pick_metric(item, key, fallback_keys) is not None]
    if len(values) < 2:
        return f"{label}数据不足。"
    start, end = values[0], values[-1]
    low, high = min(values), max(values)
    if abs(end - start) < 0.01:
        trend = "基本稳定"
    elif (end < start and not reverse) or (end > start and reverse):
        trend = "下降"
    else:
        trend = "上升"
    return f"{label}{trend}，从{start:.3f}变化到{end:.3f}，区间为{low:.3f}~{high:.3f}。"


def trend_peak_summary(
    history: Sequence[Dict[str, Any]],
    *,
    key: str,
    fallback_keys: Iterable[str] = (),
    label: str,
) -> str:
    values = [float(_pick_metric(item, key, fallback_keys)) for item in history if _pick_metric(item, key, fallback_keys) is not None]
    if len(values) < 2:
        return f"{label}数据不足。"
    start, end = values[0], values[-1]
    peak = max(values)
    trough = min(values)
    if end > start * 1.5:
        direction = "显著上升"
    elif end < start * 0.8:
        direction = "明显下降"
    else:
        direction = "相对平稳"
    return f"{label}{direction}，起点{start:.3f}，终点{end:.3f}，峰值{peak:.3f}，低点{trough:.3f}。"


def extract_sample_profile(sample: Dict[str, Any]) -> str:
    profile = sample.get("realistic_profile") or {}
    parts: List[str] = []
    name = profile.get("name") or sample.get("name")
    role_label = profile.get("role_label") or profile.get("title")
    department = profile.get("department")
    specialty = profile.get("specialty")
    seniority = profile.get("seniority_label") or profile.get("seniority")
    if name:
        parts.append(str(name))
    if role_label:
        parts.append(str(role_label))
    if department:
        parts.append(str(department))
    if specialty:
        parts.append(str(specialty))
    if seniority:
        parts.append(f"{seniority}资历")
    if not parts:
        return f"Agent #{sample.get('agent_id', '?')}"
    return " / ".join(parts[:5])


def format_count_distribution(distribution: Optional[Dict[str, Any]], top_n: int = 8) -> str:
    if not distribution:
        return "暂无"
    items = sorted(distribution.items(), key=lambda item: item[1], reverse=True)
    return "、".join(f"{key}:{value}" for key, value in items[:top_n])


def format_top_changes(samples: Sequence[Dict[str, Any]], limit: int = 3) -> str:
    if not samples:
        return "（无样本）"
    lines = []
    for idx, sample in enumerate(samples[:limit], 1):
        profile = extract_sample_profile(sample)
        direction = sample.get("change_direction")
        if direction == "positive":
            direction_text = "转向更正面"
        elif direction == "negative":
            direction_text = "转向更负面"
        else:
            direction_text = "变化较小"
        lines.append(
            f"{idx}. {profile}，观点 {sample.get('old_opinion', 0):.2f}→{sample.get('new_opinion', 0):.2f}，"
            f"变化 {sample.get('opinion_change', 0):.2f}，{direction_text}。"
        )
    return "\n".join(lines)


def event_pool_summary(event_pool: Sequence[Dict[str, Any]], max_events: int = 8) -> str:
    if not event_pool:
        return "未注入新闻事件。"
    lines = []
    for idx, event in enumerate(event_pool[-max_events:], 1):
        content = str(event.get("content", "")).strip().replace("\n", " ")
        if len(content) > 160:
            content = content[:160] + "..."
        source = "公域" if event.get("source", "public") == "public" else "私域"
        lines.append(
            f"{idx}. 第{event.get('step', 0)}步，{source}注入，可信度{event.get('credibility', '不确定')}，"
            f"情感{event.get('sentiment', '中性')}：{content}"
        )
    return "\n".join(lines)


def credibility_rule_text(credibility: Optional[str]) -> str:
    label = infer_credibility_label(credibility)
    if label == "高可信":
        return "本次按“高可信新闻”口径判定：相信新闻计为正确认知，拒绝新闻计为误信。"
    if label == "低可信":
        return "本次按“低可信新闻”口径判定：相信新闻计为误信，拒绝新闻计为正确认知。"
    return "本次新闻可信度为不确定，报告保留“相信/拒绝”和“误信/正确认知”两套指标，误信结论仅作模拟口径参考。"


def response_effect_summary(history: Sequence[Dict[str, Any]], response_step: int, responded: bool) -> str:
    if not responded or response_step >= len(history):
        return "本次推演未触发权威回应，无法评估回应后的纠偏效果。"
    before_idx = max(0, response_step - 1)
    after_idx = min(len(history) - 1, response_step + 3)
    before = float(history[before_idx].get("mislead_rate", history[before_idx].get("negative_belief_rate", 0)))
    after = float(history[after_idx].get("mislead_rate", history[after_idx].get("negative_belief_rate", 0)))
    delta = after - before
    if delta < -0.1:
        grade = "效果显著"
    elif delta < -0.02:
        grade = "有一定效果"
    elif delta <= 0.02:
        grade = "效果有限"
    else:
        grade = "存在逆火风险"
    return f"权威回应在第{response_step}步介入，误信率从{before:.1%}变为{after:.1%}，{grade}。"


def risk_level(final_state: Dict[str, Any]) -> Tuple[str, str]:
    mislead = float(final_state.get("mislead_rate", final_state.get("negative_belief_rate", 0)))
    polarization = float(final_state.get("polarization_index", 0))
    silence = float(final_state.get("silence_rate", 0))
    if mislead >= 0.5 or polarization >= 0.75:
        return "高风险", "误信或极化已经形成主导，需要立即干预。"
    if mislead >= 0.3 or polarization >= 0.5 or silence >= 0.35:
        return "中风险", "误信、极化或沉默压力已经显现，需要持续跟踪和定向干预。"
    return "低风险", "主要指标处于可控区间，但仍需观察后续事件冲击。"


def format_agent_samples(samples: Sequence[Dict[str, Any]], label: str, limit: int = 3) -> str:
    if not samples:
        return f"（无{label}样本）"
    lines = []
    for idx, sample in enumerate(samples[:limit], 1):
        profile = extract_sample_profile(sample)
        comment = sample.get("generated_comment") or ""
        reasoning = sample.get("reasoning") or ""
        lines.append(
            f"{idx}. {profile}，信念{sample.get('belief_strength', 0):.0%}，易感{sample.get('susceptibility', 0):.0%}，"
            f"观点{sample.get('old_opinion', 0):.2f}→{sample.get('new_opinion', 0):.2f}。"
            f"{reasoning}{(' 评论：' + comment) if comment else ''}"
        )
    return "\n".join(lines)


def format_entity_summary(knowledge_graph: Dict[str, Any], max_entities: int = 8, max_relations: int = 10) -> str:
    if not knowledge_graph:
        return "暂无"
    summary = knowledge_graph.get("summary") or "暂无摘要"
    keywords = knowledge_graph.get("keywords") or []
    sentiment = knowledge_graph.get("sentiment") or "未知"
    credibility = knowledge_graph.get("credibility_hint") or "不确定"
    entities = knowledge_graph.get("entities") or []
    relations = knowledge_graph.get("relations") or []

    lines = [
        f"摘要：{summary}",
        f"关键词：{'、'.join(keywords) if keywords else '暂无'}",
        f"情感倾向：{sentiment}",
        f"可信度：{credibility}",
    ]
    if entities:
        sorted_entities = sorted(entities, key=lambda e: e.get("importance", 3), reverse=True)
        entity_lines = []
        for entity in sorted_entities[:max_entities]:
            entity_lines.append(f"- {entity.get('name', '未知')}（{entity.get('type', '未知')}，重要度{entity.get('importance', 3)}/5）")
        lines.append("实体：\n" + "\n".join(entity_lines))
    else:
        lines.append("实体：暂无")

    if relations:
        entity_map = {e.get("id"): e.get("name", e.get("id")) for e in entities}
        relation_lines = []
        for relation in relations[:max_relations]:
            source_name = entity_map.get(relation.get("source"), relation.get("source", "?"))
            target_name = entity_map.get(relation.get("target"), relation.get("target", "?"))
            relation_lines.append(
                f"- {source_name} → {relation.get('action', '关联')} → {target_name}（{relation.get('type', '')}）"
            )
        lines.append("关系：\n" + "\n".join(relation_lines))
    else:
        lines.append("关系：暂无")

    return "\n".join(lines)


def _pick_metric(item: Dict[str, Any], key: str, fallback_keys: Iterable[str]) -> Any:
    if key in item and item.get(key) is not None:
        return item.get(key)
    for fallback_key in fallback_keys:
        if fallback_key in item and item.get(fallback_key) is not None:
            return item.get(fallback_key)
    return None
