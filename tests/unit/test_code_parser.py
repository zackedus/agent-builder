import pytest

from agent_builder.agents.code_parser import CodeParseError, extract_code_files


def test_extract_single_fence_with_path() -> None:
    text = """```python:calc.py
def add(a, b):
    return a + b
```"""
    files = extract_code_files(text)
    assert len(files) == 1
    assert files[0].path == "calc.py"
    assert "def add" in files[0].content


def test_extract_multiple_fences() -> None:
    text = """```python:main.py
print("hi")
```
```text:README.md
# Hello
```"""
    files = extract_code_files(text)
    paths = {f.path for f in files}
    assert paths == {"main.py", "README.md"}


def test_extract_file_header_inside_fence() -> None:
    text = """```python
# file: src/app.py
x = 1
```"""
    files = extract_code_files(text)
    assert files[0].path == "src/app.py"
    assert "x = 1" in files[0].content


def test_extract_default_path_fallback() -> None:
    text = """```python
print(1)
```"""
    files = extract_code_files(text, default_paths=["fallback.py"])
    assert files[0].path == "fallback.py"


def test_extract_empty_raises() -> None:
    with pytest.raises(CodeParseError, match="Empty"):
        extract_code_files("   ")


def test_extract_no_blocks_raises() -> None:
    with pytest.raises(CodeParseError, match="No code blocks"):
        extract_code_files("Here is an explanation only.")
