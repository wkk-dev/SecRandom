# ==================================================
# 导入库
# ==================================================
import json
import math
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from loguru import logger
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from PySide6.QtNetwork import *
from qfluentwidgets import *

from app.tools.variable import *
from app.tools.path_utils import *
from app.tools.personalised import *
from app.tools.settings_default import *
from app.tools.settings_access import *
from app.Language.obtain_language import *
from app.common.data.list import *
from app.common.extraction.extract import _get_current_class_info

from random import SystemRandom

system_random = SystemRandom()

# ==================================================
# 历史记录文件路径处理函数
# ==================================================


def get_history_file_path(history_type: str, file_name: str) -> Path:
    """获取历史记录文件路径

    Args:
        history_type: 历史记录类型 (roll_call, lottery 等)
        file_name: 文件名（不含扩展名）

    Returns:
        Path: 历史记录文件路径
    """
    history_dir = get_path(f"data/history/{history_type}_history")
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / f"{file_name}.json"


# ==================================================
# 历史记录数据读写函数
# ==================================================


def load_history_data(history_type: str, file_name: str) -> Dict[str, Any]:
    """加载历史记录数据

    Args:
        history_type: 历史记录类型 (roll_call, lottery 等)
        file_name: 文件名（不含扩展名）

    Returns:
        Dict[str, Any]: 历史记录数据
    """
    file_path = get_history_file_path(history_type, file_name)

    if not file_path.exists():
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载历史记录数据失败: {e}")
        return {}


def save_history_data(history_type: str, file_name: str, data: Dict[str, Any]) -> bool:
    """保存历史记录数据

    Args:
        history_type: 历史记录类型 (roll_call, lottery 等)
        file_name: 文件名（不含扩展名）
        data: 要保存的数据

    Returns:
        bool: 保存是否成功
    """
    file_path = get_history_file_path(history_type, file_name)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"保存历史记录数据失败: {e}")
    return False


def get_all_history_names(history_type: str) -> List[str]:
    """获取所有历史记录名称列表

    Args:
        history_type: 历史记录类型 (roll_call, lottery 等)

    Returns:
        List[str]: 历史记录名称列表
    """
    try:
        history_dir = get_path(f"data/history/{history_type}_history")
        if not history_dir.exists():
            return []
        history_files = list(history_dir.glob("*.json"))
        names = [file.stem for file in history_files]
        names.sort()
        return names
    except Exception as e:
        logger.error(f"获取历史记录名称列表失败: {e}")
        return []


# ==================================================
# 历史记录统计函数
# ==================================================


def get_name_history(history_type: str, class_name: str) -> int:
    """获取指定班级的名称历史记录数量

    Args:
        history_type: 历史记录类型 (roll_call, lottery 等)
        class_name: 班级名称/奖池名称

    Returns:
        int: 名称历史记录数量
    """
    if history_type == "roll_call":
        student_list = get_student_list(class_name)
        return len(student_list) if student_list else 0
    elif history_type == "lottery":
        student_list = get_pool_list(class_name)
        return len(student_list) if student_list else 0
    else:
        return 0


def get_draw_sessions_history(history_type: str, class_name: str) -> int:
    """获取指定班级的抽取会话历史记录数量

    Args:
        history_type: 历史记录类型 (roll_call, lottery 等)
        class_name: 班级名称

    Returns:
        int: 抽取会话历史记录数量
    """
    history_data = load_history_data(history_type, class_name)
    session_count = 0
    if history_type == "roll_call":
        key = "students"
    elif history_type == "lottery":
        key = "lotterys"
    else:
        return 0
    students_dict = history_data.get(key, {})
    if isinstance(students_dict, dict):
        for student_name, student_info in students_dict.items():
            session_list = student_info.get("history", [])
            if isinstance(session_list, list):
                session_count += len(session_list)
    return session_count


def get_individual_statistics(
    history_type: str, class_name: str, students_name: str
) -> int:
    """获取指定班级的个人统计记录数量

    Args:
        history_type: 历史记录类型 (roll_call, lottery 等)
        class_name: 班级名称/奖池名称
        students_name: 学生姓名/奖品名称

    Returns:
        int: 个人统计记录数量
    """
    history_data = load_history_data(history_type, class_name)
    if history_type == "roll_call":
        key = "students"
    elif history_type == "lottery":
        key = "lotterys"
    else:
        return 0
    students_dict = history_data.get(key, {})
    if not isinstance(students_dict, dict):
        return 0
    student_info = students_dict.get(students_name)
    if not student_info:
        return 0
    student_history = student_info.get("history", [])
    if not isinstance(student_history, list):
        return 0
    return len(student_history)


# ==================================================
# 保存抽奖历史函数
# ==================================================
def save_lottery_history(
    pool_name: str,
    selected_students: List[Dict[str, Any]],
    group_filter: str,
    gender_filter: str,
) -> bool:
    """保存抽奖历史（基于奖池名称）

    Args:
        pool_name: 奖池名称
        selected_students: 学生字典列表（包含 name、id、exist 等）
        group_filter: 抽取时的小组过滤器
        gender_filter: 抽取时的性别过滤器

    Returns:
        bool: 保存是否成功
    """
    try:
        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 获取当前课程信息
        current_class_info = _get_current_class_info()

        history_data = load_history_data("lottery", pool_name)
        lotterys = history_data.get("lotterys", {})
        group_stats = history_data.get("group_stats", {})
        gender_stats = history_data.get("gender_stats", {})
        total_stats = history_data.get("total_stats", 0)

        for student in selected_students or []:
            name = student.get("name", "")
            if not name:
                continue
            entry = lotterys.get(name)
            if not isinstance(entry, dict):
                entry = {
                    "total_count": 0,
                    "rounds_missed": 0,
                    "last_drawn_time": "",
                    "history": [],
                }
            entry["total_count"] = int(entry.get("total_count", 0)) + 1
            entry["last_drawn_time"] = current_time
            hist = entry.get("history", [])
            if not isinstance(hist, list):
                hist = []
            hist.append(
                {
                    "draw_time": current_time,
                    "draw_lottery_numbers": len(selected_students),
                    "draw_group": group_filter,
                    "draw_gender": gender_filter,
                }
            )
            # 如果能获取到课程信息，则添加到历史记录中
            if current_class_info:
                hist[-1]["class_name"] = current_class_info.get("name", "")
            entry["history"] = hist
            lotterys[name] = entry

        # 更新统计
        if group_filter:
            group_stats[group_filter] = int(group_stats.get(group_filter, 0)) + len(
                selected_students or []
            )
        if gender_filter:
            gender_stats[gender_filter] = int(gender_stats.get(gender_filter, 0)) + len(
                selected_students or []
            )
        total_stats = int(total_stats) + len(selected_students or [])

        history_data["lotterys"] = lotterys
        history_data["group_stats"] = group_stats
        history_data["gender_stats"] = gender_stats
        history_data["total_stats"] = total_stats

        return save_history_data("lottery", pool_name, history_data)
    except Exception as e:
        logger.error(f"保存抽奖历史失败: {e}")
        return False


# ==================================================
# 权重格式化函数
# ==================================================
def format_weight_for_display(weights_data: list, weight_key: str = "weight") -> tuple:
    """格式化权重显示，确保小数点对齐

    Args:
        weights_data: 包含权重数据的列表
        weight_key: 权重在数据项中的键名，默认为'weight'

    Returns:
        tuple: (格式化函数, 整数部分最大长度, 小数部分最大长度)
    """
    # 计算权重显示的最大长度，考虑小数点前后的对齐
    max_int_length = 0  # 整数部分最大长度
    max_dec_length = 2  # 固定为两位小数

    for item in weights_data:
        weight = item.get(weight_key, 0)
        weight_str = str(weight)
        if "." in weight_str:
            int_part, _ = weight_str.split(".", 1)
            max_int_length = max(max_int_length, len(int_part))
        else:
            max_int_length = max(max_int_length, len(weight_str))

    # 格式化权重显示，确保小数点对齐并保留两位小数
    def format_weight(weight):
        weight_str = str(weight)
        if "." in weight_str:
            int_part, dec_part = weight_str.split(".", 1)
            # 确保小数部分有两位
            if len(dec_part) < 2:
                dec_part = dec_part.ljust(2, "0")
            elif len(dec_part) > 2:
                dec_part = dec_part[:2]  # 截断多余的小数位
            # 整数部分右对齐，小数部分左对齐
            formatted_int = int_part.rjust(max_int_length)
            # 小数部分补齐到最大长度
            formatted_dec = dec_part.ljust(max_dec_length)
            return f"{formatted_int}.{formatted_dec}"
        else:
            # 没有小数点的情况，添加小数点和两位小数
            formatted_int = weight_str.rjust(max_int_length)
            formatted_dec = "00".ljust(max_dec_length)
            return f"{formatted_int}.{formatted_dec}"

    return format_weight, max_int_length, max_dec_length


# ==================================================
# 公平抽取权重计算函数
# ==================================================
def calculate_weight(
    students_data: list, class_name: str, subject_filter: str = ""
) -> list:
    """计算学生权重

    Args:
        students_data: 学生数据列表
        class_name: 班级名称
        subject_filter: 课程过滤，如果指定则只计算该课程的历史记录

    Returns:
        list: 更新后的学生数据列表，包含权重信息
    """
    # 从设置中加载权重相关配置
    settings = {
        "fair_draw_enabled": readme_settings_async("fair_draw_settings", "fair_draw")
        or False,
        "fair_draw_group_enabled": readme_settings_async(
            "fair_draw_settings", "fair_draw_group"
        )
        or False,
        "fair_draw_gender_enabled": readme_settings_async(
            "fair_draw_settings", "fair_draw_gender"
        )
        or False,
        "fair_draw_time_enabled": readme_settings_async(
            "fair_draw_settings", "fair_draw_time"
        )
        or False,
        "base_weight": readme_settings_async("fair_draw_settings", "base_weight")
        or 1.0,
        "min_weight": readme_settings_async("fair_draw_settings", "min_weight") or 0.1,
        "max_weight": readme_settings_async("fair_draw_settings", "max_weight") or 5.0,
        "frequency_function": readme_settings_async(
            "fair_draw_settings", "frequency_function"
        )
        or 1,
        "frequency_weight": readme_settings_async(
            "fair_draw_settings", "frequency_weight"
        )
        or 1.0,
        "group_weight": readme_settings_async("fair_draw_settings", "group_weight")
        or 1.0,
        "gender_weight": readme_settings_async("fair_draw_settings", "gender_weight")
        or 1.0,
        "time_weight": readme_settings_async("fair_draw_settings", "time_weight")
        or 1.0,
        "cold_start_enabled": readme_settings_async(
            "fair_draw_settings", "cold_start_enabled"
        )
        or False,
        "cold_start_rounds": readme_settings_async(
            "fair_draw_settings", "cold_start_rounds"
        )
        or 10,
        "shield_enabled": readme_settings_async("advanced_settings", "shield_enabled")
        or False,
        "shield_time": readme_settings_async("advanced_settings", "shield_time") or 0,
        "shield_time_unit": readme_settings_async(
            "advanced_settings", "shield_time_unit"
        )
        or 0,
        "subject_history_filter_enabled": readme_settings_async(
            "course_settings", "subject_history_filter_enabled"
        )
        or False,
    }

    # 获取当前课程信息（用于科目过滤）
    current_class_info = None
    if settings["subject_history_filter_enabled"] or subject_filter:
        # 如果指定了 subject_filter，优先使用它
        if subject_filter:
            current_class_info = {"name": subject_filter}
        else:
            use_class_island_source = readme_settings_async(
                "course_settings", "class_island_source_enabled"
            )
            if use_class_island_source:
                from app.common.IPC_URL.csharp_ipc_handler import CSharpIPCHandler

                current_class_info = (
                    CSharpIPCHandler.instance().get_current_class_info()
                )
            else:
                current_class_info = _get_current_class_info()

            # 如果当前没有课程信息（课间时段），则使用课间归属的课程信息
            if not current_class_info:
                from app.common.extraction.extract import (
                    _is_non_class_time,
                    _get_break_assignment_class_info,
                )

                if _is_non_class_time():
                    current_class_info = _get_break_assignment_class_info()

    # 加载历史记录数据
    history_data = load_history_data("roll_call", class_name)

    # 冷启动轮次配置
    current_stats = history_data.get("total_stats", 0)
    is_cold_start = (
        settings["cold_start_enabled"] and current_stats < settings["cold_start_rounds"]
    )

    # 初始化权重数据结构
    weight_data = {}
    for student in students_data:
        student_id = student.get("id", student.get("name", ""))
        weight_data[student_id] = {
            "total_count": 0,
            "group_count": 0,
            "gender_count": 0,
            "last_drawn_time": None,
            "rounds_missed": 0,
        }

    # 从历史记录中提取权重信息
    if isinstance(history_data, dict) and "students" in history_data:
        students_history = history_data.get("students", {})
        if isinstance(students_history, dict):
            for student_name, student_info in students_history.items():
                if student_name in weight_data and isinstance(student_info, dict):
                    # 如果有科目过滤，需要重新计算所有计数
                    if current_class_info:
                        current_class_name = current_class_info.get("name", "")

                        # 优先使用 subject_stats 中的数据
                        subject_stats = student_info.get("subject_stats", {})
                        if current_class_name in subject_stats:
                            subject_stat = subject_stats[current_class_name]
                            weight_data[student_name]["total_count"] = subject_stat.get(
                                "total_count", 0
                            )
                            weight_data[student_name]["group_gender_count"] = (
                                subject_stat.get("group_gender_count", 0)
                            )
                            # group_count 和 gender_count 从 subject_stats 的 total_count 获取
                            weight_data[student_name]["group_count"] = subject_stat.get(
                                "total_count", 0
                            )
                            weight_data[student_name]["gender_count"] = (
                                subject_stat.get("total_count", 0)
                            )
                        else:
                            # 如果 subject_stats 中没有该科目的数据，则遍历历史记录计算
                            filtered_total_count = 0
                            filtered_group_count = 0
                            filtered_gender_count = 0

                            history = student_info.get("history", [])
                            if isinstance(history, list):
                                for record in history:
                                    if isinstance(record, dict):
                                        record_class_name = record.get("class_name", "")
                                        # 只统计当前科目的记录
                                        if record_class_name == current_class_name:
                                            filtered_total_count += 1

                                            # 统计 group_count
                                            draw_group = record.get("draw_group", "")
                                            if draw_group:
                                                filtered_group_count += 1

                                            # 统计 gender_count
                                            draw_gender = record.get("draw_gender", "")
                                            if draw_gender:
                                                filtered_gender_count += 1

                            weight_data[student_name]["total_count"] = (
                                filtered_total_count
                            )
                            weight_data[student_name]["group_count"] = (
                                filtered_group_count
                            )
                            weight_data[student_name]["gender_count"] = (
                                filtered_gender_count
                            )
                            weight_data[student_name]["group_gender_count"] = (
                                filtered_total_count
                            )
                    else:
                        # 没有科目过滤，使用原始的计数
                        weight_data[student_name]["total_count"] = student_info.get(
                            "total_count", 0
                        )
                        weight_data[student_name]["group_gender_count"] = (
                            student_info.get("group_gender_count", 0)
                        )

                        # 从历史记录中重新计算 group_count 和 gender_count
                        history = student_info.get("history", [])
                        if isinstance(history, list):
                            all_group = get_content_combo_name_async(
                                "roll_call", "range_combobox"
                            )[0]
                            all_gender = get_content_combo_name_async(
                                "roll_call", "gender_combobox"
                            )[0]

                            for record in history:
                                if isinstance(record, dict):
                                    # 更新小组计数
                                    draw_group = record.get("draw_group", "")
                                    if draw_group and draw_group != all_group:
                                        weight_data[student_name]["group_count"] += 1

                                    # 更新性别计数
                                    draw_gender = record.get("draw_gender", "")
                                    if draw_gender and draw_gender != all_gender:
                                        weight_data[student_name]["gender_count"] += 1

                    weight_data[student_name]["rounds_missed"] = student_info.get(
                        "rounds_missed", 0
                    )

                    last_drawn_time = student_info.get("last_drawn_time", "")
                    if last_drawn_time:
                        weight_data[student_name]["last_drawn_time"] = last_drawn_time

    # 获取小组和性别统计
    # 如果有科目过滤，需要重新计算小组和性别统计
    if current_class_info:
        current_class_name = current_class_info.get("name", "")

        # 优先使用顶层的 subject_stats
        subject_stats = history_data.get("subject_stats", {})
        if current_class_name in subject_stats:
            subject_stat = subject_stats[current_class_name]
            group_stats = subject_stat.get("group_stats", {})
            gender_stats = subject_stat.get("gender_stats", {})
        else:
            # 如果 subject_stats 中没有该科目的数据，则遍历历史记录计算
            filtered_group_stats = {}
            filtered_gender_stats = {}

            # 遍历所有学生，重新计算小组和性别统计
            for student_name, student_info in history_data.get("students", {}).items():
                history = student_info.get("history", [])
                if isinstance(history, list):
                    for record in history:
                        if isinstance(record, dict):
                            record_class_name = record.get("class_name", "")
                            # 只统计当前科目的记录
                            if record_class_name == current_class_name:
                                # 更新小组统计
                                draw_group = record.get("draw_group", "")
                                if draw_group:
                                    if draw_group not in filtered_group_stats:
                                        filtered_group_stats[draw_group] = 0
                                    filtered_group_stats[draw_group] += 1

                                # 更新性别统计
                                draw_gender = record.get("draw_gender", "")
                                if draw_gender:
                                    if draw_gender not in filtered_gender_stats:
                                        filtered_gender_stats[draw_gender] = 0
                                    filtered_gender_stats[draw_gender] += 1

            group_stats = filtered_group_stats
            gender_stats = filtered_gender_stats
    else:
        # 没有科目过滤，使用原始的统计数据
        group_stats = history_data.get("group_stats", {})
        gender_stats = history_data.get("gender_stats", {})

    # 获取所有学生的总抽取次数，用于计算相对频率
    all_total_counts = [data["total_count"] for data in weight_data.values()]
    max_total_count = max(all_total_counts) if all_total_counts else 0
    min_total_count = min(all_total_counts) if all_total_counts else 0
    total_count_range = (
        max_total_count - min_total_count if max_total_count > min_total_count else 1
    )

    # 为每个学生计算权重
    for student in students_data:
        student_id = student.get("id", student.get("name", ""))
        if student_id not in weight_data:
            continue

        student_weight_data = weight_data[student_id]
        total_count = student_weight_data["total_count"]

        # 计算频率惩罚因子 - 支持多种函数类型
        if settings["fair_draw_enabled"]:
            # 根据设置选择频率函数
            if settings["frequency_function"] == 0:  # 线性函数
                # 线性函数：(max_count - current_count + 1) / (max_count + 1)
                frequency_factor = (max_total_count - total_count + 1) / (
                    max_total_count + 1
                )
            elif settings["frequency_function"] == 1:  # 平方根函数
                # 平方根函数：sqrt(max_count + 1) / sqrt(current_count + 1)
                frequency_factor = math.sqrt(max_total_count + 1) / math.sqrt(
                    total_count + 1
                )
            elif settings["frequency_function"] == 2:  # 指数函数
                # 指数函数：exp((max_count - current_count) / max_count)
                # 当max_total_count为0时，避免除零错误
                if max_total_count == 0:
                    frequency_factor = 1.0  # 所有学生都未被抽中时，频率因子为1
                else:
                    frequency_factor = math.exp(
                        (max_total_count - total_count) / max_total_count
                    )
            else:  # 默认平方根函数
                frequency_factor = math.sqrt(max_total_count + 1) / math.sqrt(
                    total_count + 1
                )

            # 冷启动特殊处理 - 防止新学生权重过低
            if is_cold_start:
                # 冷启动模式下，降低频率因子的影响，使抽取更随机
                frequency_factor = min(0.8 + (frequency_factor * 0.2), frequency_factor)

            # 应用频率权重
            frequency_penalty = frequency_factor * settings["frequency_weight"]
        else:
            frequency_penalty = 0.0

        # 计算小组平衡因子
        if settings["fair_draw_group_enabled"]:
            # 获取学生当前小组
            current_student_group = student.get("group", "")

            # 获取有效小组统计数量（值>0的条目）
            valid_groups = [v for v in group_stats.values() if v > 0]

            if len(valid_groups) > 3:  # 有效小组数量达标
                group_history = max(group_stats.get(current_student_group, 0), 0)
                group_factor = 1.0 / (group_history * 0.2 + 1)
                group_balance = group_factor * settings["group_weight"]
            else:
                # 数据不足时，使用相对计数方法
                all_counts = [data["group_count"] for data in weight_data.values()]
                max_group_count = max(all_counts) if all_counts else 0

                if max_group_count == 0:
                    group_balance = (
                        0.2 * settings["group_weight"]
                    )  # 给所有学生一个小组平衡的基础权重提升
                elif student_weight_data["group_count"] == 0:
                    group_balance = (
                        0.5 * settings["group_weight"]
                    )  # 给从未在小组中被选中的学生一个基础权重提升
                else:
                    group_balance = settings["group_weight"] * (
                        1.0 - (student_weight_data["group_count"] / max_group_count)
                    )
        else:
            group_balance = 0.0

        # 计算性别平衡因子
        if settings["fair_draw_gender_enabled"]:
            # 获取学生当前性别
            current_student_gender = student.get("gender", "")

            # 获取有效性别统计数量（值>0的条目）
            valid_gender = [v for v in gender_stats.values() if v > 0]

            if len(valid_gender) > 3:  # 有效性别数量达标
                gender_history = max(gender_stats.get(current_student_gender, 0), 0)
                gender_factor = 1.0 / (gender_history * 0.2 + 1)
                gender_balance = gender_factor * settings["gender_weight"]
            else:
                # 数据不足时，使用相对计数方法
                all_counts = [data["gender_count"] for data in weight_data.values()]
                max_gender_count = max(all_counts) if all_counts else 0

                if max_gender_count == 0:
                    gender_balance = (
                        0.2 * settings["gender_weight"]
                    )  # 给所有学生一个性别平衡的基础权重提升
                elif student_weight_data["gender_count"] == 0:
                    gender_balance = (
                        0.5 * settings["gender_weight"]
                    )  # 给从未在性别平衡中被选中的学生一个基础权重提升
                else:
                    gender_balance = settings["gender_weight"] * (
                        1.0 - (student_weight_data["gender_count"] / max_gender_count)
                    )
        else:
            gender_balance = 0.0

        # 计算时间因子
        if (
            settings["fair_draw_time_enabled"]
            and student_weight_data["last_drawn_time"]
        ):
            try:
                from datetime import datetime

                last_time = datetime.fromisoformat(
                    student_weight_data["last_drawn_time"]
                )
                current_time = datetime.now()
                days_diff = (current_time - last_time).days
                time_factor = min(1.0, days_diff / 30.0) * settings["time_weight"]
            except Exception as e:
                logger.exception(
                    "Error calculating time factor for student weights: {}", e
                )
                time_factor = 0.0
        else:
            time_factor = 0.0

        # 检查是否处于屏蔽期
        is_shielded = False
        shield_remaining = 0
        if settings["shield_enabled"] and student_weight_data["last_drawn_time"]:
            try:
                from datetime import datetime, timedelta

                last_time = datetime.fromisoformat(
                    student_weight_data["last_drawn_time"]
                )
                current_time = datetime.now()

                # 根据时间单位计算屏蔽时间
                if settings["shield_time_unit"] == 0:  # 秒
                    shield_duration = timedelta(seconds=settings["shield_time"])
                elif settings["shield_time_unit"] == 1:  # 分钟
                    shield_duration = timedelta(minutes=settings["shield_time"])
                else:  # 小时
                    shield_duration = timedelta(hours=settings["shield_time"])

                # 检查是否在屏蔽期内
                if current_time - last_time < shield_duration:
                    is_shielded = True
                    shield_remaining = (
                        shield_duration - (current_time - last_time)
                    ).total_seconds()
            except Exception as e:
                logger.exception("Error calculating shield time for student: {}", e)

        # 计算总权重
        student_weights = {
            "base": settings["base_weight"],  # 基础权重
            "frequency": frequency_penalty,  # 频率惩罚
            "group": group_balance,  # 小组平衡
            "gender": gender_balance,  # 性别平衡
            "time": time_factor,  # 时间因子
        }

        total_weight = sum(student_weights.values())

        # 如果处于屏蔽期，设置极低权重
        if is_shielded:
            total_weight = settings["min_weight"] / 10  # 屏蔽期内权重为最小值的1/10

        # 确保权重在最小和最大值之间
        total_weight = max(
            settings["min_weight"] / 10, min(settings["max_weight"], total_weight)
        )
        total_weight = round(total_weight, 2)

        # 设置学生的权重和详细信息
        student["next_weight"] = total_weight
        student["weight_details"] = {
            "base_weight": student_weights["base"],
            "frequency_penalty": student_weights["frequency"],
            "group_balance": student_weights["group"],
            "gender_balance": student_weights["gender"],
            "time_factor": student_weights["time"],
            "total_weight": total_weight,
            "is_cold_start": is_cold_start,
            "total_count": total_count,
            "max_total_count": max_total_count,
            "frequency_function": settings["frequency_function"],
            "is_shielded": is_shielded,
            "shield_remaining": round(shield_remaining, 2),
            "shield_enabled": settings["shield_enabled"],
        }

    return students_data


# ==================================================
# 历史记录保存与更新函数
# ==================================================
def save_roll_call_history(
    class_name: str,
    selected_students: List[Dict[str, Any]],
    group_filter: Optional[str] = None,
    gender_filter: Optional[str] = None,
) -> bool:
    """保存点名历史记录

    Args:
        class_name: 班级名称
        selected_students: 被选中的学生列表
        students_dict_list: 完整的学生列表，用于计算权重
        group_filter: 小组过滤器，指定本次抽取的小组范围，None表示不限制
        gender_filter: 性别过滤器，指定本次抽取的性别范围，None表示不限制

    Returns:
        bool: 保存是否成功
    """
    try:
        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 加载现有历史记录
        history_data = load_history_data("roll_call", class_name)

        # 初始化数据结构
        if "students" not in history_data:
            history_data["students"] = {}
        if "group_stats" not in history_data:
            history_data["group_stats"] = {}
        if "gender_stats" not in history_data:
            history_data["gender_stats"] = {}
        if "total_rounds" not in history_data:
            history_data["total_rounds"] = 0
        if "total_stats" not in history_data:
            history_data["total_stats"] = 0
        if "subject_stats" not in history_data:
            history_data["subject_stats"] = {}

        # 获取被选中的学生名称列表
        selected_names = [s.get("name", "") for s in selected_students]

        # 计算权重
        students_dict_list = get_student_list(class_name)
        students_with_weight = calculate_weight(students_dict_list, class_name)

        # 更新每个被选中学生的历史记录
        for student in selected_students:
            student_name = student.get("name", "")
            if not student_name:
                continue

            # 如果学生不存在于历史记录中，创建新记录
            if student_name not in history_data["students"]:
                history_data["students"][student_name] = {
                    "total_count": 0,
                    "group_gender_count": 0,
                    "last_drawn_time": "",
                    "rounds_missed": 0,
                    "history": [],
                    "subject_stats": {},
                }

            # 更新学生的基本信息
            student_data = history_data["students"][student_name]
            student_data["total_count"] += 1
            student_data["last_drawn_time"] = current_time
            student_data["rounds_missed"] = 0  # 重置未选中次数

            draw_method = 1

            # 获取当前被选中学生的权重信息
            current_student_weight = None
            for student_with_weight in students_with_weight:
                if student_with_weight.get("name") == student_name:
                    current_student_weight = student_with_weight.get("next_weight", 0)
                    break

            # 获取当前课程信息
            use_class_island_source = readme_settings_async(
                "course_settings", "class_island_source_enabled"
            )
            if use_class_island_source:
                from app.common.IPC_URL.csharp_ipc_handler import CSharpIPCHandler

                current_class_info = (
                    CSharpIPCHandler.instance().get_current_class_info()
                )
            else:
                current_class_info = _get_current_class_info()

            # 如果当前没有课程信息（课间时段），则使用课间归属的课程信息
            if not current_class_info:
                from app.common.extraction.extract import (
                    _is_non_class_time,
                    _get_break_assignment_class_info,
                )

                if _is_non_class_time():
                    current_class_info = _get_break_assignment_class_info()

            history_entry = {
                "draw_method": draw_method,
                "draw_time": current_time,
                "draw_people_numbers": len(selected_students),
                "draw_group": group_filter,
                "draw_gender": gender_filter,
                "weight": current_student_weight,
            }

            # 如果能获取到课程信息，则添加到历史记录中并更新学科统计
            if current_class_info:
                subject_name = current_class_info.get("name", "")
                history_entry["class_name"] = subject_name

                # 更新学生级别的学科统计
                if "subject_stats" not in student_data:
                    student_data["subject_stats"] = {}

                if subject_name not in student_data["subject_stats"]:
                    student_data["subject_stats"][subject_name] = {
                        "total_count": 0,
                        "group_gender_count": 0,
                    }

                subject_stat = student_data["subject_stats"][subject_name]
                subject_stat["total_count"] += 1

                # 统计 group_gender_count（小组和性别都有限制）
                all_group = get_content_combo_name_async("roll_call", "range_combobox")[
                    0
                ]
                all_gender = get_content_combo_name_async(
                    "roll_call", "gender_combobox"
                )[0]

                if group_filter and group_filter != all_group:
                    if gender_filter and gender_filter != all_gender:
                        subject_stat["group_gender_count"] += 1

            student_data["history"].append(history_entry)

        # 更新未被选中的学生的未选中次数
        for student_name, student_data in history_data["students"].items():
            if student_name not in selected_names:
                student_data["rounds_missed"] += 1

        # 更新小组和性别统计
        for student in selected_students:
            group = student.get("group", "")
            gender = student.get("gender", "")

            # 更新小组统计
            if group not in history_data["group_stats"]:
                history_data["group_stats"][group] = 0
            history_data["group_stats"][group] += 1

            # 更新性别统计
            if gender not in history_data["gender_stats"]:
                history_data["gender_stats"][gender] = 0
            history_data["gender_stats"][gender] += 1

        # 更新学科统计（顶层）
        if current_class_info:
            subject_name = current_class_info.get("name", "")
            if subject_name:
                if subject_name not in history_data["subject_stats"]:
                    history_data["subject_stats"][subject_name] = {
                        "group_stats": {},
                        "gender_stats": {},
                        "total_rounds": 0,
                        "total_stats": 0,
                    }

                subject_stat = history_data["subject_stats"][subject_name]
                subject_stat["total_rounds"] += 1
                subject_stat["total_stats"] += len(selected_students)

                for student in selected_students:
                    group = student.get("group", "")
                    gender = student.get("gender", "")

                    # 更新学科小组统计
                    if group:
                        if group not in subject_stat["group_stats"]:
                            subject_stat["group_stats"][group] = 0
                        subject_stat["group_stats"][group] += 1

                    # 更新学科性别统计
                    if gender:
                        if gender not in subject_stat["gender_stats"]:
                            subject_stat["gender_stats"][gender] = 0
                        subject_stat["gender_stats"][gender] += 1

        # 更新总轮数和总统计数
        history_data["total_rounds"] += 1
        history_data["total_stats"] += len(selected_students)

        # 保存历史记录
        return save_history_data("roll_call", class_name, history_data)

    except Exception as e:
        logger.error(f"保存点名历史记录失败: {e}")
        return False


# ==================================================
# 辅助函数
# ==================================================
def get_all_names(history_type: str, list_name: str) -> list:
    """获取历史记录中所有名称

    Args:
        history_type: 历史记录类型
        list_name: 列表名称

    Returns:
        list: 所有名称列表
    """
    try:
        if history_type == "roll_call":
            list_name_data = get_student_list(list_name)
            return [
                item["name"]
                for item in list_name_data
                if "name" in item and item["name"]
            ]
        else:
            list_name_data = get_pool_list(list_name)
            return [
                item["name"]
                for item in list_name_data
                if "name" in item and item["name"]
            ]
    except Exception as e:
        logger.error(f"获取历史记录中所有名称失败: {e}")
        return []


def format_table_item(
    value: Union[str, int, float], is_percentage: bool = False
) -> str:
    """格式化表格项显示值

    Args:
        value: 要格式化的值
        is_percentage: 是否为百分比值

    Returns:
        str: 格式化后的字符串
    """
    if isinstance(value, (int, float)):
        if is_percentage:
            return f"{value:.2%}"
        else:
            return f"{value:.2f}"
    return str(value)


def create_table_item(
    value: Union[str, int, float],
    is_centered: bool = True,
    is_percentage: bool = False,
) -> "QTableWidgetItem":
    """创建表格项

    Args:
        value: 要显示的值
        is_centered: 是否居中
        is_percentage: 是否为百分比值

    Returns:
        QTableWidgetItem: 表格项对象
    """
    display_value = format_table_item(value, is_percentage)
    item = QTableWidgetItem(display_value)

    if is_centered:
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item
