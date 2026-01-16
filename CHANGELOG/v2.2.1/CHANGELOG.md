<img width="1800" height="766" alt="新版本" src="https://github.com/SECTL/SecRandom/blob/master/data/assets/icon/secrandom-release.png" />
v2.0 - Koharu（小鸟游星野） release 4

## 🚀 主要更新

- 无

## 💡 功能优化

- 优化 Sentry上报，过滤**无效错误**与日志
- 优化 main/window/tray.py，重构结构并提取**常量**
- 优化 app/tools目录，重构结构并提取**常量**
- 优化 roll_call/lottery.py，提取重复代码至**UI工具类**
- 优化 RollCall/LotteryController，封装**业务逻辑**
- 优化 RollCall/LotteryUIInterface，预留**自定义接口**
- 优化 VoiceCacheManager，移除**内存缓存**
- 优化 TTSHandler，整合**系统音量控制**
- 优化 edge_tts_worker.py，简化**代码结构**
- 优化 font_manager.py，重构字体加载并提取**常量**
- 优化 personalised.py，简化图标与主题函数，移除**重复代码**
- 优化 config.py，新增通知与音量**常量配置**
- 优化 button_draw_utils.py，新增函数**文档注释**

## 🐛 修复问题

- 修复 学生名单导出**AttributeError**报错
- 修复 TTS引擎初始化失败的**异常处理**
- 修复 音乐播放非随机时**UnboundLocalError**报错
- 修复 语音队列与生成功能的**日志级别**
- 修复 设置文件读取空文件**JSON解析**错误
- 修复 图标加载空文件**图标映射**错误
- 修复 抽奖奖品抽取时**KeyError**报错
- 修复 config.py通知**lambda**函数显示异常
- 修复 roll_call/roll_call_utils.py 中**缓存键错误**

## 🔧 其它变更

- 无

---

💝 **感谢所有贡献者为 SecRandom 项目付出的努力！**
