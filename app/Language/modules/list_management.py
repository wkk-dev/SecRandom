# 名单管理语言配置
list_management = {
    "ZH_CN": {
        "title": {"name": "名单管理", "description": "管理点名、抽奖的名单"},
        "roll_call_list": {"name": "点名名单", "description": "管理点名用学生名单"},
        "lottery_list": {"name": "抽奖名单", "description": "管理抽奖用奖品名单"},
    }
}

# 点名名单语言配置
roll_call_list = {
    "ZH_CN": {
        "title": {"name": "点名名单", "description": "管理点名用学生名单"},
        "set_class_name": {"name": "设置班级名称", "description": "设置当前班级名称"},
        "select_class_name": {
            "name": "选择班级",
            "description": "从已有班级中选择一个班级",
        },
        "import_student_name": {
            "name": "导入学生名单",
            "description": "从文件导入学生名单",
        },
        "name_setting": {"name": "设置姓名", "description": "设置学生姓名"},
        "gender_setting": {"name": "设置性别", "description": "设置学生性别"},
        "group_setting": {"name": "设置小组", "description": "设置学生所属小组"},
        "export_student_name": {
            "name": "导出学生名单",
            "description": "将学生名单导出到文件",
        },
    }
}

# 点名表格语言配置
roll_call_table = {
    "ZH_CN": {
        "title": {"name": "点名表格", "description": "展示和管理点名名单"},
        "select_class_name": {
            "name": "选择班级",
            "description": "选择要显示的点名班级",
        },
        "HeaderLabels": {
            "name": ["存在", "学号", "姓名", "性别", "小组"],
            "description": "点名表格的列标题",
        },
    }
}

# 抽奖名单语言配置
lottery_list = {
    "ZH_CN": {
        "title": {"name": "抽奖名单", "description": "管理抽奖用奖品名单"},
        "set_pool_name": {"name": "设置奖池名称", "description": "设置当前奖池名称"},
        "select_pool_name": {
            "name": "选择奖池",
            "description": "从已有奖池中选择一个奖池",
        },
        "import_prize_name": {
            "name": "导入奖品名单",
            "description": "从文件导入奖品名单",
        },
        "prize_setting": {"name": "设置奖品", "description": "设置奖品名称"},
        "prize_weight_setting": {"name": "设置权重", "description": "设置奖品中奖权重"},
        "export_prize_name": {
            "name": "导出奖品名单",
            "description": "将奖品名单导出到文件",
        },
    }
}

# 抽奖表格语言配置
lottery_table = {
    "ZH_CN": {
        "title": {"name": "抽奖表格", "description": "展示和管理抽奖名单"},
        "select_pool_name": {
            "name": "选择奖池",
            "description": "选择要显示的抽奖奖池",
        },
        "HeaderLabels": {
            "name": ["存在", "序号", "奖品", "权重"],
            "description": "抽奖表格的列标题",
        },
    }
}

# 通知文本配置
notification = {
    "ZH_CN": {
        # 点名名单通知
        "roll_call": {
            "class_name_setting": {
                "title": {
                    "name": "班级名称设置",
                    "description": "班级名称设置通知标题",
                },
                "content": {
                    "name": "已打开班级名称设置窗口",
                    "description": "班级名称设置通知内容",
                },
            },
            "import_student_name": {
                "title": {
                    "name": "学生名单导入",
                    "description": "学生名单导入通知标题",
                },
                "content": {
                    "name": "已打开学生名单导入窗口",
                    "description": "学生名单导入通知内容",
                },
            },
            "name_setting": {
                "title": {"name": "姓名设置", "description": "姓名设置通知标题"},
                "content": {
                    "name": "已打开姓名设置窗口",
                    "description": "姓名设置通知内容",
                },
            },
            "gender_setting": {
                "title": {"name": "性别设置", "description": "性别设置通知标题"},
                "content": {
                    "name": "已打开性别设置窗口",
                    "description": "性别设置通知内容",
                },
            },
            "group_setting": {
                "title": {"name": "小组设置", "description": "小组设置通知标题"},
                "content": {
                    "name": "已打开小组设置窗口",
                    "description": "小组设置通知内容",
                },
            },
            "export": {
                "title": {
                    "success": {"name": "导出成功", "description": "导出成功通知标题"},
                    "failure": {"name": "导出失败", "description": "导出失败通知标题"},
                },
                "content": {
                    "success": {
                        "name": "学生名单已导出到: {path}",
                        "description": "导出成功通知内容",
                    },
                    "failure": {
                        "name": "请先选择要导出的班级",
                        "description": "导出失败通知内容（未选择班级）",
                    },
                    "error": {"name": "{message}", "description": "导出错误通知内容"},
                },
            },
        },
        # 抽奖名单通知
        "lottery": {
            "pool_name_setting": {
                "title": {
                    "name": "奖池名称设置",
                    "description": "奖池名称设置通知标题",
                },
                "content": {
                    "name": "已打开奖池名称设置窗口",
                    "description": "奖池名称设置通知内容",
                },
            },
            "import_prize_name": {
                "title": {
                    "name": "奖品名单导入",
                    "description": "奖品名单导入通知标题",
                },
                "content": {
                    "name": "已打开奖品名单导入窗口",
                    "description": "奖品名单导入通知内容",
                },
            },
            "prize_setting": {
                "title": {"name": "奖品设置", "description": "奖品设置通知标题"},
                "content": {
                    "name": "已打开奖品设置窗口",
                    "description": "奖品设置通知内容",
                },
            },
            "prize_weight_setting": {
                "title": {
                    "name": "奖品权重设置",
                    "description": "奖品权重设置通知标题",
                },
                "content": {
                    "name": "已打开奖品权重设置窗口",
                    "description": "奖品权重设置通知内容",
                },
            },
            "export": {
                "title": {
                    "success": {"name": "导出成功", "description": "导出成功通知标题"},
                    "failure": {"name": "导出失败", "description": "导出失败通知标题"},
                },
                "content": {
                    "success": {
                        "name": "奖品名单已导出到: {path}",
                        "description": "导出成功通知内容",
                    },
                    "failure": {
                        "name": "请先选择要导出的奖池",
                        "description": "导出失败通知内容（未选择奖池）",
                    },
                    "error": {"name": "{message}", "description": "导出错误通知内容"},
                },
            },
        },
    }
}

# QFileDialog 文本配置
qfiledialog = {
    "ZH_CN": {
        "roll_call": {
            "export_student_list": {
                "caption": {
                    "name": "保存学生名单",
                    "description": "保存学生名单对话框标题",
                },
                "filter": {
                    "name": "Excel 文件 (*.xlsx);;CSV 文件 (*.csv);;TXT 文件（仅姓名） (*.txt)",
                    "description": "保存学生名单对话框过滤器",
                },
            }
        },
        "lottery": {
            "export_prize_name": {
                "caption": {
                    "name": "保存奖品名单",
                    "description": "保存奖品名单对话框标题",
                },
                "filter": {
                    "name": "Excel 文件 (*.xlsx);;CSV 文件 (*.csv);;TXT 文件（仅奖品名） (*.txt)",
                    "description": "保存奖品名单对话框过滤器",
                },
            }
        },
    }
}
