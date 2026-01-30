from app.tools.settings_visibility_config import SETTINGS_VISIBILITY_CONFIG
from app.tools.settings_access import readme_settings_async


def is_setting_visible(category: str, setting_name: str) -> bool:
    """
    检查设置项是否可见

    Args:
        category: 设置类别
        setting_name: 设置项名称
        is_simplified_mode: 是否为简化模式

    Returns:
        bool: True表示可见，False表示隐藏
    """
    simplified_mode = readme_settings_async("basic_settings", "simplified_mode")
    if simplified_mode:
        return SETTINGS_VISIBILITY_CONFIG.get(category, {}).get(setting_name, True)
    return True
