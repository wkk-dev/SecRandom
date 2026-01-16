<img width="1800" height="766" alt="新版本" src="https://github.com/SECTL/SecRandom/blob/master/data/assets/icon/secrandom-release.png" />
v2.0 - Koharu（小鸟游星野） release 4

## 🚀 主要更新

- 无

## 💡 功能优化

- 优化 Sentry错误上报，过滤**第三方库**无效错误
- 优化 Sentry日志上报，仅上报**异常**，ERROR级别日志不上报
- 优化 main.py，重构结构、提取常量并新增文档注释
- 优化 window.py，重构结构、提取常量并新增文档注释
- 优化 tray.py，重构结构、提取常量并新增文档注释
- 优化 app/tools 目录，重构结构并提取常量
- 优化 button_draw_utils.py，新增函数文档注释
- 优化 config.py，新增通知与音量常量配置
- 优化 roll_call.py，提取重复代码至**UI工具类**
- 优化 lottery.py，提取重复代码至**UI工具类**
- 优化 app/common/ui/ui_utils.py，创建通用**UI工具类**
- 优化 RollCallController，封装点名**业务逻辑**
- 优化 LotteryController，封装抽奖**业务逻辑**
- 优化 RollCallUIInterface，预留**自定义界面接口**
- 优化 LotteryUIInterface，预留**自定义界面接口**
- 优化 VoiceCacheManager，移除**内存缓存**，只保留磁盘缓存
- 优化 TTSHandler，整合**系统音量控制**逻辑
- 优化 edge_tts_worker.py，移除冗余注释，简化**代码结构**
- 优化 font_manager.py，重构字体加载逻辑，提取**常量映射**
- 优化 personalised.py，简化图标与主题函数，移除**重复代码**

## 🐛 修复问题

- 修复 学生名单导出，修复导出失败时**AttributeError**报错
- 修复 TTS语音引擎，优化初始化失败的**异常处理**逻辑
- 修复 音乐播放功能，修复非随机播放时**UnboundLocalError**报错
- 修复 语音播放队列，优化队列已满时的**日志级别**
- 修复 语音生成功能，优化网络错误重试时的**日志级别**
- 修复 设置文件读取，修复空文件**JSON解析**错误
- 修复 图标加载功能，修复空文件**图标映射**错误
- 修复 抽奖功能，修复奖品抽取时**KeyError**报错
- 修复 config.py通知功能，修复**lambda**函数导致通知显示异常

## 🔧 其它变更

- 无

---

💝 **感谢所有贡献者为 SecRandom 项目付出的努力！**
