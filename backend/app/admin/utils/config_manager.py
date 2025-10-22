from backend.core.conf import settings
from backend.common.log import log
from backend.app.admin.service.config_service import config_service

# 创建一个配置缓存，用于存储从数据库获取的配置
_config_cache = None

async def get_merged_settings():
    """
    获取合并后的配置，数据库配置优先于环境变量配置
    """
    global _config_cache
    
    # 创建一个新的settings副本
    merged_settings = settings
    
    try:
        # 如果缓存为空，从数据库获取配置
        if _config_cache is None:
            config = await config_service.get()
            if config and hasattr(config, 'settings') and config.settings:
                _config_cache = config.settings
        
        # 用数据库配置覆盖环境变量配置
        if _config_cache:
            for key, value in _config_cache.items():
                if hasattr(merged_settings, key) and value is not None and value != "":
                    setattr(merged_settings, key, value)
    except Exception as e:
        log.error(f"Failed to load config from database: {str(e)}")
    
    return merged_settings

def clear_config_cache():
    """
    清除配置缓存，用于配置更新时强制重新加载
    """
    global _config_cache
    _config_cache = None
    log.info("Configuration cache cleared, will reload from database on next request.")