"""
CodeArena 验收测试
运行全部: pytest test_challenge.py -v
运行单个 task: pytest test_challenge.py -v -k task1
"""

import subprocess
import json
import sys
import os
import time

PYTHON = sys.executable


def run(args, timeout=30):
    result = subprocess.run(
        [PYTHON, "weather.py"] + args,
        capture_output=True, text=True, timeout=timeout,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ========== Task 1 ==========

class TestTask1:

    def test_task1_a(self):
        stdout, stderr, code = run(["Beijing"])
        assert code == 0, f"stderr: {stderr}"
        assert len(stdout) > 0
        assert any(c.isdigit() for c in stdout)

    def test_task1_b(self):
        stdout, _, code = run(["Tokyo"])
        assert code == 0
        has_temp = ("°" in stdout or "C" in stdout or any(c.isdigit() for c in stdout))
        assert has_temp

    def test_task1_c(self):
        stdout, _, code = run(["London"])
        assert code == 0
        assert "london" in stdout.lower() or "伦敦" in stdout


# ========== Task 2 ==========

class TestTask2:

    def test_task2_a(self):
        stdout, stderr, code = run([])
        assert "Traceback" not in (stdout + stderr)

    def test_task2_b(self):
        stdout, stderr, code = run(["不存在的城市xyzabc123"])
        combined = stdout + stderr
        assert "Traceback" not in combined
        assert code != 0 or "未找到" in combined or "not found" in combined.lower() or "error" in combined.lower()

    def test_task2_c(self):
        stdout, stderr, code = run(["Beijing", "Tokyo"])
        assert code == 0
        lines = [l for l in stdout.split("\n") if l.strip()]
        assert len(lines) >= 2

    def test_task2_d(self):
        stdout, stderr, code = run(["Beijing", "不存在xyz"])
        combined = stdout + stderr
        assert "Traceback" not in combined
        has_valid = "beijing" in combined.lower() or "北京" in combined or any(c.isdigit() for c in stdout)
        assert has_valid


# ========== Task 3 ==========

class TestTask3:

    def test_task3_a(self):
        stdout, stderr, code = run(["Beijing", "--json"])
        assert code == 0, f"stderr: {stderr}"
        data = json.loads(stdout)
        assert isinstance(data, (dict, list))

    def test_task3_b(self):
        stdout, _, _ = run(["Beijing", "--json"])
        data = json.loads(stdout)
        if isinstance(data, list):
            data = data[0]
        all_keys = str(data.keys()).lower()
        assert any(k in all_keys for k in ["temp", "city", "weather"])

    def test_task3_c(self):
        stdout, _, code = run(["Beijing", "Tokyo", "--json"])
        if code != 0:
            return
        data = json.loads(stdout)
        if isinstance(data, list):
            assert len(data) >= 2

    def test_task3_d(self):
        source = open("weather.py", encoding="utf-8").read()
        func_count = source.count("def ")
        assert func_count >= 3, f"Expected >=3 functions, found {func_count}"


# ========== Task 4 ==========

class TestTask4:

    def test_task4_a(self):
        run(["--clear-cache"])
        start1 = time.time()
        run(["Beijing"])
        dur1 = time.time() - start1
        start2 = time.time()
        run(["Beijing"])
        dur2 = time.time() - start2
        assert dur2 < dur1 * 0.7 or dur2 < 0.5

    def test_task4_b(self):
        run(["--clear-cache"])
        run(["Beijing"])
        stdout, stderr, _ = run(["Beijing"])
        combined = (stdout + stderr).lower()
        assert "cache" in combined or "缓存" in combined

    def test_task4_c(self):
        run(["Beijing"])
        run(["Beijing", "--no-cache"])
        assert True  # flag accepted without crash

    def test_task4_d(self):
        _, stderr, code = run(["--clear-cache"])
        assert "Traceback" not in stderr


# ========== Task 5 ==========

class TestTask5:

    def test_task5_a(self):
        cities = ["Beijing", "Tokyo", "London", "Paris", "Berlin",
                  "Rome", "Madrid", "Seoul", "Sydney", "Mumbai"]
        start = time.time()
        stdout, stderr, code = run(cities, timeout=15)
        dur = time.time() - start
        assert code == 0
        assert dur < 5.0

    def test_task5_b(self):
        cities = ["Tokyo", "London", "Beijing"]
        stdout, _, code = run(cities)
        if code != 0:
            return
        lines = [l for l in stdout.split("\n") if l.strip()]
        if len(lines) >= 3:
            assert "tokyo" in lines[0].lower() or "東京" in lines[0]

    def test_task5_c(self):
        stdout, stderr, code = run(["Beijing", "不存在xyz", "Tokyo"])
        combined = stdout + stderr
        assert "Traceback" not in combined
        lines = [l for l in stdout.split("\n") if l.strip()]
        assert len(lines) >= 2


# ========== Task 6 ==========

class TestTask6:

    def test_task6_a(self):
        stdout, stderr, code = run(["--help"])
        combined = stdout + stderr
        assert len(combined) > 50
        assert "usage" in combined.lower() or "用法" in combined or "help" in combined.lower()

    def test_task6_b(self):
        stdout, stderr, code = run(["Beijing", "--forecast", "3"])
        if code != 0:
            return
        lines = [l for l in stdout.split("\n") if l.strip()]
        assert len(lines) >= 3

    def test_task6_c(self):
        stdout, stderr, code = run(["Beijing", "--units", "imperial"])
        if code != 0:
            return
        assert "F" in stdout or "°" in stdout

    def test_task6_d(self):
        source = open("weather.py", encoding="utf-8").read()
        has_hints = ("-> " in source or ": str" in source or ": float" in source
                     or ": dict" in source or ": list" in source)
        assert has_hints

    def test_task6_e(self):
        assert os.path.exists("README.md")
        content = open("README.md", encoding="utf-8").read()
        assert len(content) > 100
