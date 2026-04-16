"""
CodeArena 递进式验收测试 - Challenge A: Weather Service
运行全部: pytest test_challenge.py -v
运行单个 task: pytest test_challenge.py -v -k task1

评分规则：
- 每个 test case 通过 = 1 分
- 每个 task 的分数 = 通过数 / 总数
- task 之间独立评分（task3 失败不影响 task1 的分数）
"""

import subprocess
import json
import sys
import os
import time
import tempfile

PYTHON = sys.executable


def run(args, timeout=30):
    """运行 weather.py，返回 (stdout, stderr, returncode)"""
    result = subprocess.run(
        [PYTHON, "weather.py"] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ========== Task 1: 基础查询 ==========

class TestTask1Basic:
    """Task 1: 能查天气就行"""

    def test_task1_single_city(self):
        """查一个城市能返回结果"""
        stdout, stderr, code = run(["Beijing"])
        assert code == 0, f"Exit code != 0. stderr: {stderr}"
        assert len(stdout) > 0, "Should output something"
        assert any(c.isdigit() for c in stdout), "Should contain temperature (numbers)"

    def test_task1_has_temperature(self):
        """结果包含温度"""
        stdout, _, code = run(["Tokyo"])
        assert code == 0
        # 检查是否包含温度相关信息（°C, °F, 度, 或纯数字）
        has_temp = ("°" in stdout or "C" in stdout or "度" in stdout
                    or any(c.isdigit() for c in stdout))
        assert has_temp, f"Output should contain temperature info: {stdout}"

    def test_task1_city_name_in_output(self):
        """结果包含城市名"""
        stdout, _, code = run(["London"])
        assert code == 0
        assert "london" in stdout.lower() or "伦敦" in stdout, \
            f"Output should contain city name: {stdout}"


# ========== Task 2: 健壮性 ==========

class TestTask2Robustness:
    """Task 2: 边界条件处理"""

    def test_task2_no_args(self):
        """无参数不 crash"""
        stdout, stderr, code = run([])
        combined = stdout + stderr
        assert "Traceback" not in combined, f"Should not traceback: {combined}"

    def test_task2_invalid_city(self):
        """无效城市友好提示"""
        stdout, stderr, code = run(["不存在的城市xyzabc123"])
        combined = stdout + stderr
        assert "Traceback" not in combined, "No traceback"
        assert code != 0 or "未找到" in combined or "not found" in combined.lower() or "error" in combined.lower(), \
            f"Should indicate city not found: {combined}"

    def test_task2_multiple_cities(self):
        """多城市每个都有输出"""
        stdout, stderr, code = run(["Beijing", "Tokyo"])
        assert code == 0, f"stderr: {stderr}"
        lines = [l for l in stdout.split("\n") if l.strip()]
        assert len(lines) >= 2, f"Should have >=2 output lines for 2 cities: {stdout}"

    def test_task2_mixed_valid_invalid(self):
        """有效 + 无效城市混合，有效的仍然返回"""
        stdout, stderr, code = run(["Beijing", "不存在xyz"])
        combined = stdout + stderr
        assert "Traceback" not in combined, "No traceback"
        # 至少 Beijing 的结果应该出现
        has_beijing = "beijing" in combined.lower() or "北京" in combined or any(c.isdigit() for c in stdout)
        assert has_beijing, f"Valid city should still show results: {combined}"


# ========== Task 3: 结构化输出 ==========

class TestTask3Json:
    """Task 3: --json 输出 + 代码结构"""

    def test_task3_json_flag(self):
        """--json 输出合法 JSON"""
        stdout, stderr, code = run(["Beijing", "--json"])
        assert code == 0, f"stderr: {stderr}"
        data = json.loads(stdout)  # 不是 JSON 就直接 exception
        assert isinstance(data, (dict, list)), f"Should be dict or list: {type(data)}"

    def test_task3_json_has_fields(self):
        """JSON 包含关键字段"""
        stdout, _, _ = run(["Beijing", "--json"])
        data = json.loads(stdout)
        if isinstance(data, list):
            data = data[0]
        # 至少有 temperature 或 temp 字段
        all_keys = str(data.keys()).lower()
        assert any(k in all_keys for k in ["temp", "city", "weather"]), \
            f"JSON should have relevant fields: {data.keys()}"

    def test_task3_json_multi(self):
        """多城市 --json 返回数组"""
        stdout, _, code = run(["Beijing", "Tokyo", "--json"])
        if code != 0:
            return
        data = json.loads(stdout)
        if isinstance(data, list):
            assert len(data) >= 2, f"Should have >=2 items: {len(data)}"

    def test_task3_code_structure(self):
        """代码至少有 geocode 和 get_weather 函数"""
        source = open("weather.py", encoding="utf-8").read()
        has_geocode = "def geocode" in source or "def get_coordinates" in source or "def lookup" in source
        has_weather = "def get_weather" in source or "def fetch_weather" in source or "def query_weather" in source
        assert has_geocode, "Should have a geocode/lookup function"
        assert has_weather, "Should have a get_weather/fetch_weather function"


# ========== Task 4: 缓存 ==========

class TestTask4Cache:
    """Task 4: 本地缓存"""

    def test_task4_second_call_faster(self):
        """第二次调用明显更快（命中缓存）"""
        # 第一次（可能有旧缓存，先清理）
        run(["--clear-cache"])

        start1 = time.time()
        run(["Beijing"])
        dur1 = time.time() - start1

        start2 = time.time()
        stdout2, stderr2, _ = run(["Beijing"])
        dur2 = time.time() - start2

        # 缓存命中应该快很多（至少快 2 倍）
        assert dur2 < dur1 * 0.7 or dur2 < 0.5, \
            f"Cached call should be faster: first={dur1:.2f}s, second={dur2:.2f}s"

    def test_task4_cache_indicator(self):
        """缓存命中时有提示"""
        run(["--clear-cache"])
        run(["Beijing"])  # 填充缓存
        stdout, stderr, _ = run(["Beijing"])
        combined = (stdout + stderr).lower()
        assert "cache" in combined or "缓存" in combined, \
            f"Should indicate cache hit: stdout={stdout}, stderr={stderr}"

    def test_task4_no_cache_flag(self):
        """--no-cache 强制刷新"""
        run(["Beijing"])  # 填充缓存
        start = time.time()
        run(["Beijing", "--no-cache"])
        dur = time.time() - start
        # --no-cache 应该走网络，不会特别快
        # 这个测试比较弱，主要检查 flag 不 crash
        assert True  # flag 被接受就行

    def test_task4_clear_cache(self):
        """--clear-cache 不 crash"""
        _, stderr, code = run(["--clear-cache"])
        assert "Traceback" not in stderr, f"Should not crash: {stderr}"


# ========== Task 5: 并发 ==========

class TestTask5Concurrent:
    """Task 5: 并发查询"""

    def test_task5_ten_cities_under_5s(self):
        """10 个城市在 5 秒内返回"""
        cities = ["Beijing", "Tokyo", "London", "Paris", "Berlin",
                  "Rome", "Madrid", "Seoul", "Sydney", "Mumbai"]
        start = time.time()
        stdout, stderr, code = run(cities, timeout=15)
        dur = time.time() - start

        assert code == 0, f"stderr: {stderr}"
        assert dur < 5.0, f"10 cities should complete in <5s, took {dur:.1f}s"

    def test_task5_output_order_matches_input(self):
        """输出顺序和输入一致"""
        cities = ["Tokyo", "London", "Beijing"]
        stdout, _, code = run(cities)
        if code != 0:
            return
        lines = [l for l in stdout.split("\n") if l.strip()]
        if len(lines) >= 3:
            # 第一行应该包含 Tokyo，最后一行包含 Beijing
            assert "tokyo" in lines[0].lower() or "東京" in lines[0], \
                f"First line should be Tokyo: {lines[0]}"

    def test_task5_partial_failure(self):
        """一个失败不影响其他"""
        stdout, stderr, code = run(["Beijing", "不存在xyz", "Tokyo"])
        combined = stdout + stderr
        assert "Traceback" not in combined
        # Beijing 和 Tokyo 结果应该存在
        lines = [l for l in stdout.split("\n") if l.strip()]
        assert len(lines) >= 2, f"At least 2 valid results expected: {stdout}"


# ========== Task 6: 全局完善 ==========

class TestTask6Polish:
    """Task 6: 完善度"""

    def test_task6_help(self):
        """--help 输出帮助信息"""
        stdout, stderr, code = run(["--help"])
        combined = stdout + stderr
        assert len(combined) > 50, f"Help should be meaningful: {combined}"
        assert "usage" in combined.lower() or "用法" in combined, \
            f"Help should contain usage info: {combined}"

    def test_task6_forecast(self):
        """--forecast N 输出未来天气"""
        stdout, stderr, code = run(["Beijing", "--forecast", "3"])
        if code != 0:
            return  # 没实现就跳过
        lines = [l for l in stdout.split("\n") if l.strip()]
        assert len(lines) >= 3, f"3-day forecast should have >=3 lines: {stdout}"

    def test_task6_units(self):
        """--units imperial 华氏度"""
        stdout, stderr, code = run(["Beijing", "--units", "imperial"])
        if code != 0:
            return
        # 华氏温度通常 >50（如果北京不是严冬）
        assert "F" in stdout or "°" in stdout, f"Should show Fahrenheit: {stdout}"

    def test_task6_type_hints(self):
        """函数有类型注解"""
        source = open("weather.py", encoding="utf-8").read()
        # 检查至少有一些类型注解
        has_hints = ("-> " in source or ": str" in source or ": float" in source
                     or ": dict" in source or ": list" in source or ": int" in source)
        assert has_hints, "Should have type hints on function signatures"

    def test_task6_readme_exists(self):
        """有 README.md"""
        assert os.path.exists("README.md"), "README.md should exist"
        content = open("README.md", encoding="utf-8").read()
        assert len(content) > 100, f"README should be meaningful, got {len(content)} chars"


# ========== 评分汇总 ==========

if __name__ == "__main__":
    import pytest
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
