# 天气服务

**总时间：** 2 小时
**AI 工具：** 随意使用

## 规则

- 按顺序做，每个 Task 在上一个的基础上扩展
- 每完成一个 Task，commit 一次（`/commit "task1: done"`）
- 做到哪算哪
- 每个 Task 有自动化测试：`/test N` 或 `pytest test_challenge.py -v -k taskN`

---

## Task 1：基础查询

实现 `weather.py`，查询城市天气并输出：

```bash
python weather.py Beijing
# 输出示例：Beijing | 25°C | 风速 3.2km/h
```

API（免费，无需 key）：
- 城市转坐标：`https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1`
- 查天气：`https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true`

---

## Task 2：多城市 + 错误处理

支持更多场景：

```bash
python weather.py Beijing Tokyo London   # 多个城市，每个一行
python weather.py                        # 无参数时给出提示
python weather.py xyznotacity            # 查不到时友好提示
```

要求：不出现 Python traceback。

---

## Task 3：JSON 输出 + 代码整理

加 `--json` 参数：

```bash
python weather.py Beijing --json
# 输出 JSON 对象

python weather.py Beijing Tokyo --json
# 输出 JSON 数组
```

同时整理代码：拆出独立的函数，main 保持简洁。

---

## Task 4：本地缓存

加缓存，避免重复请求同一城市：

```bash
python weather.py Beijing              # 第一次调 API
python weather.py Beijing              # 第二次读缓存
python weather.py Beijing --no-cache   # 跳过缓存
python weather.py --clear-cache        # 清缓存
```

缓存有过期时间（10 分钟），命中时提示 `(cached)`。

---

## Task 5：并发查询

10 个城市不该等 10 秒。用异步实现并发：

```bash
python weather.py Beijing Tokyo London Paris Berlin Rome Madrid Seoul Sydney Mumbai
# 应该 2-3 秒返回
```

输出顺序保持和输入一致，某个城市出错不影响其他。

---

## Task 6：完善

- `--help` 帮助信息
- `--forecast 3` 未来 N 天预报
- `--units imperial` 华氏度
- 函数加类型注解
- 写 `README.md`
