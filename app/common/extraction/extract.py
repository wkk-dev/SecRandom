# ==================================================
# 导入模块
# ==================================================
from qfluentwidgets import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtNetwork import *

import json
from typing import Dict
from loguru import logger
import shutil
from pathlib import Path
from PySide6.QtCore import QDateTime

from app.tools.path_utils import *
from app.common.extraction.cses_parser import CSESParser
from app.Language.obtain_language import get_content_name_async


# ==================================================
# 判断当前时间是否在非上课时间段
# ==================================================
def _is_non_class_time() -> bool:
    """检测当前时间是否在非上课时间段

    当'课间禁用'开关启用时，用于判断是否需要安全验证

    Returns:
        bool: 如果当前时间在非上课时间段内返回True，否则返回False
    """
    try:
        # 1. 检查课间禁用开关是否启用
        instant_draw_disable = readme_settings_async(
            "program_functionality", "instant_draw_disable"
        )
        if not instant_draw_disable:
            return False

        # 2. 检查是否启用了ClassIsland数据源
        use_class_island_source = readme_settings_async(
            "time_settings", "class_island_source_enabled"
        )

        if use_class_island_source:
            # 使用ClassIsland数据判断是否为课间时间
            class_island_break_status = readme_settings_async(
                "time_settings", "current_class_island_break_status"
            )
            # 确保返回布尔值
            return bool(class_island_break_status)
        else:
            # 使用CSES配置的非上课时间段
            non_class_times = _get_non_class_times_config()
            if not non_class_times or not isinstance(non_class_times, dict):
                # 如果非上课时间配置不存在或格式不正确，返回False
                return False

            # 3. 获取当前时间并转换为总秒数
            current_total_seconds = _get_current_time_in_seconds()

            # 4. 检查当前时间是否在任何非上课时间段内
            return _is_time_in_ranges(current_total_seconds, non_class_times)

    except Exception as e:
        logger.error(f"检测非上课时间失败: {e}")
        return False


def _get_non_class_times_config() -> Dict[str, str]:
    """获取非上课时间段配置

    Returns:
        Dict[str, str]: 非上课时间段配置字典，如果获取失败返回空字典
    """
    try:
        # 从data/CSES目录获取CSES文件
        cses_dir = get_data_path("CSES")
        if not os.path.exists(cses_dir):
            logger.info("CSES目录不存在，返回空的非上课时间配置")
            return {}

        # 获取CSES目录中的所有YAML文件
        import os

        cses_files = [
            f for f in os.listdir(cses_dir) if f.lower().endswith((".yaml", ".yml"))
        ]

        if not cses_files:
            logger.info("CSES目录中没有找到YAML文件，返回空的非上课时间配置")
            return {}

        # 使用第一个找到的CSES文件
        cses_file_path = os.path.join(cses_dir, cses_files[0])

        # 创建CSES解析器并加载文件
        parser = CSESParser()
        if not parser.load_from_file(cses_file_path):
            logger.error(f"加载CSES文件失败: {cses_file_path}")
            return {}

        # 使用CSES解析器获取非上课时间段
        non_class_times = parser.get_non_class_times()
        logger.info(f"成功从CSES文件生成{len(non_class_times)}个非上课时间段")
        return non_class_times

    except Exception as e:
        logger.error(f"读取CSES时间设置失败: {e}")
        return {}


def _get_current_time_in_seconds() -> int:
    """获取当前时间并转换为总秒数

    Returns:
        int: 当前时间的总秒数（从午夜开始计算）
    """
    current_time = QDateTime.currentDateTime()
    current_hour = current_time.time().hour()
    current_minute = current_time.time().minute()
    current_second = current_time.time().second()

    return current_hour * 3600 + current_minute * 60 + current_second


def _is_time_in_ranges(current_seconds: int, time_ranges: Dict[str, str]) -> bool:
    """检查当前时间是否在任何一个时间范围内

    Args:
        current_seconds: 当前时间的总秒数
        time_ranges: 时间范围字典，格式为 {"name": "HH:MM:SS-HH:MM:SS"}

    Returns:
        bool: 如果当前时间在任何一个时间范围内返回True，否则返回False
    """
    for range_name, time_range in time_ranges.items():
        try:
            start_end = time_range.split("-")
            if len(start_end) != 2:
                logger.warning(f"时间范围格式错误: {range_name} = {time_range}")
                continue

            start_time_str, end_time_str = start_end

            # 解析开始时间
            start_total_seconds = _parse_time_string_to_seconds(start_time_str)

            # 解析结束时间
            end_total_seconds = _parse_time_string_to_seconds(end_time_str)

            # 检查当前时间是否在该非上课时间段内
            if start_total_seconds <= current_seconds < end_total_seconds:
                return True

        except Exception as e:
            logger.error(
                f"解析非上课时间段失败: {range_name} = {time_range}, 错误: {e}"
            )
            continue

    return False


def _parse_time_string_to_seconds(time_str: str) -> int:
    """将时间字符串转换为总秒数

    Args:
        time_str: 时间字符串，格式为 "HH:MM:SS" 或 "HH:MM"

    Returns:
        int: 时间的总秒数

    Raises:
        ValueError: 如果时间字符串格式不正确
    """
    time_parts = list(map(int, time_str.split(":")))

    if len(time_parts) < 2 or len(time_parts) > 3:
        raise ValueError(f"时间字符串格式不正确: {time_str}")

    hours = time_parts[0]
    minutes = time_parts[1]
    seconds = time_parts[2] if len(time_parts) > 2 else 0

    return hours * 3600 + minutes * 60 + seconds


# ==================================================
# CSES导入功能
# ==================================================
def import_cses_schedule(file_path: str) -> tuple[bool, str]:
    """从CSES文件导入课程表

    Args:
        file_path: CSES文件路径

    Returns:
        tuple[bool, str]: (是否成功, 结果消息)
    """
    try:
        # 创建CSES解析器
        parser = CSESParser()

        # 加载CSES文件
        if not parser.load_from_file(file_path):
            return False, get_content_name_async(
                "time_settings", "cses_file_format_error"
            )

        # 获取非上课时间段配置
        non_class_times = parser.get_non_class_times()
        if not non_class_times:
            return False, get_content_name_async(
                "time_settings", "no_valid_time_periods"
            )

        # 保存原始文件到data/CSES文件夹
        original_file_name = Path(file_path).name
        cses_data_path = get_data_path("CSES", original_file_name)
        ensure_dir(get_data_path("CSES"))
        shutil.copy2(file_path, cses_data_path)
        logger.info(f"已将CSES文件保存到: {cses_data_path}")

        # 保存到设置文件
        success = _save_non_class_times_to_settings(non_class_times)
        if not success:
            return False, get_content_name_async(
                "time_settings", "save_settings_failed"
            )

        # 获取摘要信息
        summary = parser.get_summary()
        import_success_msg = get_content_name_async("time_settings", "import_success")
        if "{}" in import_success_msg:
            return True, import_success_msg.format(summary)
        else:
            return True, import_success_msg

    except Exception as e:
        logger.error(f"导入CSES文件失败: {e}")
        return False, get_content_name_async("time_settings", "import_failed").format(
            str(e)
        )


def import_cses_schedule_from_content(content: str) -> tuple[bool, str]:
    """从CSES内容字符串导入课程表

    Args:
        content: CSES格式的YAML内容

    Returns:
        tuple[bool, str]: (是否成功, 结果消息)
    """
    try:
        # 创建CSES解析器
        parser = CSESParser()

        # 加载CSES内容
        if not parser.load_from_content(content):
            return False, get_content_name_async(
                "time_settings", "cses_content_format_error"
            )

        # 获取非上课时间段配置
        non_class_times = parser.get_non_class_times()
        if not non_class_times:
            return False, get_content_name_async(
                "time_settings", "no_valid_time_periods"
            )

        # 保存到设置文件
        success = _save_non_class_times_to_settings(non_class_times)
        if not success:
            return False, get_content_name_async(
                "time_settings", "save_settings_failed"
            )

        # 获取摘要信息
        summary = parser.get_summary()
        return True, get_content_name_async("time_settings", "import_success").format(
            summary
        )

    except Exception as e:
        logger.error(f"导入CSES内容失败: {e}")
        return False, get_content_name_async("time_settings", "import_failed").format(
            str(e)
        )


def _save_non_class_times_to_settings(non_class_times: Dict[str, str]) -> bool:
    """保存非上课时间段到设置文件

    Args:
        non_class_times: 非上课时间段字典

    Returns:
        bool: 保存成功返回True，否则返回False
    """
    try:
        settings_path = get_settings_path()

        # 读取现有设置
        if file_exists(settings_path):
            with open_file(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
        else:
            settings = {}

        # 更新非上课时间段配置
        settings["non_class_times"] = non_class_times

        # 写入设置文件
        with open_file(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

        logger.info(f"成功保存{len(non_class_times)}个非上课时间段到设置文件")
        return True

    except Exception as e:
        logger.error(f"保存非上课时间段失败: {e}")
        return False


def get_cses_import_template() -> str:
    """获取CSES导入模板内容

    Returns:
        str: CSES格式的模板内容
    """
    template = f"""{get_content_name_async("extraction_settings", "cses_template.header")}
{get_content_name_async("extraction_settings", "cses_template.reference")}

{get_content_name_async("extraction_settings", "cses_template.schedule")}
{get_content_name_async("extraction_settings", "cses_template.timeslots")}
{get_content_name_async("extraction_settings", "cses_template.name_field")}
{get_content_name_async("extraction_settings", "cses_template.start_time_field")}
{get_content_name_async("extraction_settings", "cses_template.end_time_field")}
{get_content_name_async("extraction_settings", "cses_template.teacher_field")}
{get_content_name_async("extraction_settings", "cses_template.location_field")}
{get_content_name_async("extraction_settings", "cses_template.day_of_week_field")}


    - name: \"第二节课\"
      start_time: \"08:55\"
      end_time: \"09:40\"
      teacher: \"李老师\"
      location: \"教室B\"
      day_of_week: 1


    - name: \"第三节课\"
      start_time: \"10:00\"
      end_time: \"10:45\"
      teacher: \"王老师\"
      location: \"教室C\"
      day_of_week: 1


    - name: \"第四节课\"
      start_time: \"10:55\"
      end_time: \"11:40\"
      teacher: \"赵老师\"
      location: \"教室D\"
      day_of_week: 1
"""
    return template


# ==================================================
# 导出函数列表
# ==================================================
__all__ = [
    "import_cses_schedule",
    "import_cses_schedule_from_content",
    "get_cses_import_template",
]
