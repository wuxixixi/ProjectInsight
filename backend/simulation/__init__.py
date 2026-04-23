# Simulation package
# 使用 lazy imports 避免循环导入风险 (issue #342)
def __getattr__(name: str):
    if name == "SimulationEngine":
        from .engine import SimulationEngine
        return SimulationEngine
    elif name == "AgentPopulation":
        from .agents import AgentPopulation
        return AgentPopulation
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["SimulationEngine", "AgentPopulation"]
