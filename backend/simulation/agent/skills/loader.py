"""
SkillLoader - 技能懒加载器

核心模式: 元数据优先 + 懒加载
- 先加载 SKILL.yaml 元数据
- 仅在需要时加载技能实现
- 支持热加载和卸载
"""
from typing import Dict, List, Optional, Type
from pathlib import Path
import logging

from .base import SkillBase, SkillMetadata, SkillContext

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    技能懒加载器

    工作流程:
    1. 扫描 skills/ 目录，加载所有 SKILL.yaml 元数据
    2. 根据元数据中的 requires 和 priority 构建依赖图
    3. 按需加载技能实现（懒加载）
    """

    # 类级注册表: 用于装饰器注册（issue #637: 保持向后兼容）
    _class_registry: Dict[str, Type[SkillBase]] = {}

    @classmethod
    def register(cls, name: str):
        """技能注册装饰器"""
        def decorator(skill_class: Type[SkillBase]):
            cls._class_registry[name] = skill_class
            return skill_class
        return decorator

    def __init__(self, skills_dir: Optional[Path] = None):
        """
        Args:
            skills_dir: 技能目录路径（包含 SKILL.yaml 的目录）
        """
        self.skills_dir = skills_dir or Path(__file__).parent

        # 实例级注册表（从类级注册表初始化，支持测试隔离）
        self._registry: Dict[str, Type[SkillBase]] = dict(self._class_registry)
        
        # 已加载的元数据
        self._metadata: Dict[str, SkillMetadata] = {}
        
        # 已实例化的技能
        self._instances: Dict[str, SkillBase] = {}
        
        # 扫描并加载元数据
        self._scan_metadata()
    
    def _scan_metadata(self):
        """扫描技能目录，加载所有 SKILL.yaml"""
        if not self.skills_dir.exists():
            logger.warning(f"技能目录不存在: {self.skills_dir}")
            return
        
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            yaml_path = skill_dir / "SKILL.yaml"
            if yaml_path.exists():
                try:
                    metadata = SkillMetadata.from_yaml(yaml_path)
                    self._metadata[metadata.name] = metadata
                    logger.debug(f"加载技能元数据: {metadata.name} (优先级: {metadata.priority})")
                except Exception as e:
                    logger.error(f"加载技能元数据失败 {yaml_path}: {e}")
    
    def get_available_skills(self) -> List[str]:
        """获取可用技能列表"""
        # 合并注册表和元数据
        all_skills = set(self._metadata.keys()) | set(self._registry.keys())
        return sorted(all_skills)
    
    def get_metadata(self, name: str) -> Optional[SkillMetadata]:
        """获取技能元数据"""
        return self._metadata.get(name)
    
    async def load_skill(self, name: str) -> Optional[SkillBase]:
        """
        懒加载技能实例
        
        Args:
            name: 技能名称
        
        Returns:
            技能实例，如果加载失败返回 None
        """
        # 已加载则直接返回
        if name in self._instances:
            return self._instances[name]
        
        # 从注册表查找实现类
        skill_class = self._registry.get(name)
        if skill_class is None:
            logger.error(f"技能 {name} 未注册")
            return None
        
        # 获取元数据
        metadata = self._metadata.get(name)
        
        try:
            instance = skill_class(metadata=metadata)
            self._instances[name] = instance
            logger.info(f"懒加载技能: {name}")
            return instance
        except Exception as e:
            logger.error(f"加载技能 {name} 失败: {e}")
            return None
    
    async def load_skills_for_agent(
        self,
        required_skills: List[str],
        context: SkillContext
    ) -> List[SkillBase]:
        """
        为 Agent 加载所需技能
        
        Args:
            required_skills: 所需技能名称列表
            context: 执行上下文
        
        Returns:
            按优先级排序的技能实例列表
        """
        loaded = []
        
        for name in required_skills:
            skill = await self.load_skill(name)
            if skill is not None:
                await skill.initialize(context)
                loaded.append(skill)
        
        # 按优先级排序
        loaded.sort(key=lambda s: s.metadata.priority)
        return loaded
    
    async def unload_skill(self, name: str):
        """卸载技能"""
        if name in self._instances:
            await self._instances[name].cleanup()
            del self._instances[name]
    
    async def unload_all(self):
        """卸载所有技能"""
        for name in list(self._instances.keys()):
            await self.unload_skill(name)
