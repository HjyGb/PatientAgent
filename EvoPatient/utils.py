"""Shared utility functions to eliminate duplicate definitions across modules."""

import json
import re
from pathlib import Path


def ensure_parent(path: Path) -> None:
    """Ensure the parent directory of *path* exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def match_star(context: str, symbol: str = "*") -> str:
    """Match **...** or ##...## style markers and return the content without symbols.

    Args:
        context: The text to search in.
        symbol: The marker symbol. Default "*" matches **...**; pass "#" for ##...##.

    Returns:
        The matched content with symbols stripped; empty string if no match.
    """
    sym = symbol.replace("\\", "")
    pat = f"{re.escape(sym)}{re.escape(sym)}(.*?){re.escape(sym)}{re.escape(sym)}"
    m = re.search(pat, context, flags=re.DOTALL)
    if not m:
        return ""
    return re.sub(re.escape(sym), "", m.group(0))


def match_star_strict(context: str) -> str:
    """Strict version of match_star: match **...**, raise ValueError if not found."""
    m = re.search(r"\*\*(.*?)\*\*", context, flags=re.DOTALL)
    if not m:
        raise ValueError(f"No **...** match found in text: {context[:80]}...")
    return re.sub(r"\*", "", m.group(0))


def read_prompt(json_path: str = "Simulated/Prompt/prompt_data.json") -> dict:
    """Read prompt_data.json and join list-type values into complete strings."""
    p = Path(json_path)
    data = json.loads(p.read_text(encoding="utf-8"))
    final = {}
    for k, v in data.items():
        final[k] = "".join(v) if isinstance(v, list) else str(v)
    return final


def clean_token_count(base_dir: str = ".") -> None:
    """Clear token count files."""
    tp_overall = Path(base_dir) / "make_task" / "token_count" / "token_overall.txt"
    tp_stream = Path(base_dir) / "make_task" / "token_count" / "token_stream.txt"
    for tp in (tp_overall, tp_stream):
        ensure_parent(tp)
        tp.write_text("", encoding="utf-8")


def get_token_count(base_dir: str = ".") -> str:
    """Read cumulative token count; return '0' if file missing or empty."""
    tp_stream = Path(base_dir) / "make_task" / "token_count" / "token_stream.txt"
    if not tp_stream.exists():
        return "0"
    token_str = tp_stream.read_text(encoding="utf-8")
    nums = re.findall(r"\d+", token_str)
    return nums[-1] if nums else "0"


def count_chinese_characters(text: str) -> int:
    """Count Chinese characters in the text."""
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def split_string(input_string: str) -> list[str]:
    """Split by Chinese or English comma; return single-element list if no comma."""
    if "," in input_string:
        return [s.strip() for s in input_string.split(",")]
    if "，" in input_string:
        return [s.strip() for s in input_string.split("，")]
    return [input_string.strip()]
