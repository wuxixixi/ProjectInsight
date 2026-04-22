"""
Skill Pipeline Base Classes

技能管道基础类:
- SkillMetadata: 技能元数据
- SkillBase: 技能基类
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Callable
from abc import ABC, abstractmethod
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


class SkillMetadata(BaseModel):
    """技能元数据"""
    name: str = Field(..., description="技能名称")
    description: str = Field("", description="技能描述")
    priority: int = Field(50, ge=0, le=100, description="优先级: 0最高, 100最低")
    requires: List[str] = Field(default_factory=list, description="依赖技能")
    provides: List[str] = Field(default_factory=list, description="输出字段")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置参数")
    readonly: bool = Field(True, description="是否只读（不修改环境）")
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "SkillMetadata":
        """从 YAML 文件加载"""
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)


class SkillContext(BaseModel):
    """技能执行上下文"""
    agent_id: int
    step: int
    belief_state: Dict[str, Any]
    observation: Dict[str, Any]
    memory: Dict[str, Any]
    previous_results: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)


class SkillResult(BaseModel):
    """技能执行结果"""
    skill_name: str
    success: bool = True
    output: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class SkillBase(ABC):
    """
    技能基类
    
    所有技能必须实现:
    - metadata: 技能元数据
    - execute(): 执行技能
    """
    
    def __init__(self, metadata: Optional[SkillMetadata] = None):
        self._metadata = metadata or self._get_default_metadata()
        self._initialized = False
    
    @property
    def metadata(self) -> SkillMetadata:
        """获取技能元数据"""
        return self._metadata
    
    def _get_default_metadata(self) -> SkillMetadata:
        """获取默认元数据（子类可覆盖）"""
        return SkillMetadata(name=self.__class__.__name__)
    
    async def initialize(self, context: SkillContext):
        """
        初始化技能（可选）
        
        用于加载模型、准备资源等
        """
        self._initialized = True
    
    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """
        执行技能
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        pass
    
    async def cleanup(self):
        """
        清理资源（可选）
        
        用于释放模型、关闭连接等
        """
        self._initialized = False
    
    def __repr__(self) -> str:
        return f"Skill(name={self.metadata.name}, priority={self.metadata.priority})"


class CompositeSkill(SkillBase):
    """
    组合技能 - 串联多个子技能
    """
    
    def __init__(self, skills: List[SkillBase], metadata: Optional[SkillMetadata] = None):
        super().__init__(metadata)
        self._skills = sorted(skills, key=lambda s: s.metadata.priority)
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """依次执行所有子技能"""
        previous_results = {}
        all_outputs = {}
        
        for skill in self._skills:
            # 检查依赖
            for required in skill.metadata.requires:
                if required not in previous_results:
                    logger.warning(f"Skill {skill.metadata.name} 依赖 {required} 未满足")
            
            # 更新上下文
            context.previous_results = previous_results
            
            # 执行技能
            result = await skill.execute(context)
            
            if result.success:
                previous_results[skill.metadata.name] = result.output
                all_outputs.update(result.output)
            else:
                logger.error(f"Skill {skill.metadata.name} 执行失败: {result.error}")
        
        return SkillResult(
            skill_name=self.metadata.name,
            success=True,
            output=all_outputs
        )
