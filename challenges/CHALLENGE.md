# 挑战 A：天气服务（递进式）

**总时间：** 2 小时  
**AI 工具：** 随意使用  
**难度：** 从入门到进阶，6 个 Task 递进

## 规则

- 按顺序做，每个 Task 在上一个的基础上扩展
- 每完成一个 Task，**单独 commit 一次**（commit message 写 `task1: done` / `task2: done` 等）
- 做到哪算哪，质量比数量重要
- 每个 Task 都有自动化测试，跑 `pytest test_challenge.py -v -k taskN` 验证

---

## Task 1：基础查询（预计 15 分钟）

> 考察：能不能用 AI 快速搭起一个可工作的东西

实现 `weather.py`，调用 [Open-Meteo API](https://open-meteo.com/)（免费，无需 key）查询天气：

```bash
python weather.py Beijing
# 输出：Beijing | 晴 | 25°C | 湿度 40% | 风速 3.2m/s
```

技术：
- geocoding API: `https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1`
- weather API: `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=relative_humidity_2m`

验收：`pytest test_challenge.py -v -k task1`

---

## Task 2：健壮性（预计 15 分钟）

> 考察：会不会处理边界条件，还是只做 happy path

在 Task 1 基础上，处理这些情况：

```bash
python weather.py                        # 无参数 → 友好提示，不 crash
python weather.py 不存在的城市xyz         # 无结果 → "未找到城市 xxx"
python weather.py Beijing Tokyo London   # 多城市 → 每个城市一行
```

要求：
- 任何网络错误 → 友好提示，不能出现 traceback
- 退出码：成功 0，有错误 1

验收：`pytest test_challenge.py -v -k task2`

---

## Task 3：结构化输出（预计 20 分钟）

> 考察：代码结构，不能是一个 300 行的 main

加功能：

```bash
python weather.py Beijing --json
# 输出：{"city":"Beijing","lat":39.9,"lon":116.4,"temperature":25.0,...}

python weather.py Beijing Tokyo --json
# 输出：JSON 数组
```

同时要求代码重构：
- 至少拆分为 2 个函数：`geocode(city_name)` 和 `get_weather(lat, lon)`
- main 函数不超过 30 行

验收：`pytest test_challenge.py -v -k task3`

---

## Task 4：缓存层（预计 25 分钟）

> 考察：工程设计，能不能在已有代码上加功能而不弄乱

添加本地缓存，避免重复请求：

```bash
python weather.py Beijing              # 第一次：调 API
python weather.py Beijing              # 第二次：读缓存（快 10x）
python weather.py Beijing --no-cache   # 强制刷新
python weather.py --clear-cache        # 清空缓存
```

要求：
- 缓存到本地文件（JSON/SQLite/pickle，方案自选）
- 缓存有 TTL（默认 10 分钟，超过自动失效）
- 缓存命中时在 stderr 输出 `(cached)` 提示

验收：`pytest test_challenge.py -v -k task4`

---

## Task 5：并发性能（预计 25 分钟）

> 考察：异步编程能力，处理并发

查询 10 个城市不应该串行等 10 秒。实现并发查询：

```bash
python weather.py Beijing Tokyo London Paris Berlin Rome Madrid Seoul Sydney Mumbai
# 10 个城市，应该在 2-3 秒内返回（不是 10+ 秒）
```

要求：
- 使用 `asyncio` + `aiohttp`（或 `httpx` async）实现并发
- 保持输出顺序和输入顺序一致
- 某个城市失败不影响其他城市（错误单独显示）

验收：`pytest test_challenge.py -v -k task5`

---

## Task 6：全局完善（预计 20 分钟）

> 考察：完整度，最后 20% 的打磨

补齐以下所有内容：

- [ ] `--help` 输出有意义的帮助信息（用 argparse 或 click）
- [ ] `--forecast N` 输出未来 N 天预报（用 `daily` 参数）
- [ ] `--units imperial` 支持华氏度
- [ ] 类型注解（type hints）覆盖所有函数签名
- [ ] 写一个 `README.md`：安装方法、用法示例、设计决策说明

验收：`pytest test_challenge.py -v -k task6`

---

## 评测维度

你的报告会包含：

| 维度 | 怎么评 |
|------|--------|
| **完成度** | 6 个 task 完成了几个？每个 task 的测试通过率？ |
| **代码质量** | Task 3+ 的代码结构，是否随着功能增加保持整洁 |
| **AI 工具运用** | commit 节奏 + AI 日志分析：是让 AI 一次生成还是分步迭代 |
| **问题拆解** | 是不是按 task 顺序推进，还是跳来跳去 |
| **时间分配** | 在 task 1-2 上花了多久？有没有留时间给后面的？ |
