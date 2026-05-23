"""修复 MinerU 输出中因 PDF 字体编码损坏导致的英文乱码。

方案3: 共享映射表 — 同源 PDF 复用映射
方案4: 种子扩展 — GB/T 种子 + 约束搜索 + 词级精炼
"""

import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    from importlib.resources import files
    _MAPPING_DIR = files("gb_parser") / "mappings"
except Exception:
    _MAPPING_DIR = Path(__file__).parent / "mappings"


# 国标中常见英文术语（按长度索引）
DICTIONARY_BY_LEN: Dict[int, List[str]] = {}
_RAW_DICT = [
    # 2 字母
    "GB", "EN", "to", "in", "is", "on", "at", "by", "of", "or",
    "mm", "cm", "kg",
    # 3 字母
    "the", "and", "for", "not", "are", "all", "use", "set",
    "ISO", "PVC", "key", "low", "top", "end", "fit", "cut",
    "air", "bar", "fan", "oil", "gas", "hot", "wet", "dry",
    # 4 字母
    "with", "from", "this", "that", "have", "test", "type",
    "part", "door", "leaf", "open", "wall", "edge", "side",
    "area", "size", "high", "form", "line", "main", "bolt",
    "face", "fire", "flat", "heat", "iron", "lock", "seal",
    "slot", "turn", "unit", "vent", "wide", "wood", "zone",
    "ANSI", "AAMA", "ASTM",
    # 5 字母
    "frame", "glass", "hinge", "panel", "place", "steel",
    "close", "fixed", "metal", "shown", "storm", "strip",
    "upper", "lower", "light", "means", "posts", "shall",
    "sheet", "screw", "cover", "water", "width",
    "depth", "angle", "block", "floor", "glaze", "joint",
    "latch", "level", "outer", "plate", "sash", "style",
    "table", "value", "wheel",
    # 6 字母
    "window", "handle", "infill", "centre", "filler",
    "device", "bottom", "secure", "safety", "system",
    "active", "double", "single", "sliding",
    "method", "moulding", "locking", "height", "ground",
    "rebate", "timber",
    # 7 字母
    "opening", "section", "control", "general", "folding",
    "glazing", "meeting", "plastic", "profile", "support",
    "weather", "surface", "purpose", "release", "organic",
    # 8 字母
    "building", "hardware", "standard", "vertical", "aluminum",
    "bilateral", "operable", "interior", "exterior", "accessory",
    "coating", "drainage", "fastener",
    # 9 字母
    "technical", "component", "equipment", "inactive",
    "structure", "unrebated", "appendant", "dimension",
    "tolerance", "clearance",
    # 10+ 字母
    "structural", "terminology", "ventilation",
    "requirement", "intelligent", "residential",
    "multilateral", "unilateral",
    "threshold", "transom", "mullion",
    "skylight", "subframe", "projecting", "horizontally",
    "permanently", "habitable",
    # 多词组合（无空格连写）
    "windowsanddoors", "windowanddoor",
    "activeleaf", "fixedleaf", "inactiveleaf", "fixeddoor",
    "activepartofwindowanddoor", "fixedpartofwindowanddoor",
    "insidewindowanddoorframe",
    "slidingprojecting", "trackslidingsash", "horizontalslidingsash",
    "verticallyslidingsash", "verticalslidingsash",
    "coupledwindow", "combinationwindow", "secondarywindow", "secondarydoor",
    "frenchwindow", "escapewindow", "louveredwindow",
    "combinationtransomandmullion",
    "structuralopening", "structuralrebate",
    "horizontalpivotcasement", "verticalpivotcasement",
    "hungcasement", "sidehungshutterwindow",
    "thickness", "hookedstile", "hungdoor", "casements"
]

for w in _RAW_DICT:
    k = len(w)
    DICTIONARY_BY_LEN.setdefault(k, []).append(w.lower())


def extract_garbled_runs(text: str) -> List[str]:
    """检测编码乱码的CJK连续段：高文档频率 + 窄码位区间 + 连坐法。"""
    cjk_runs: List[str] = re.findall(r'[一-鿿]{2,}', text)
    if not cjk_runs:
        return []

    char_df: Counter = Counter()
    for run in cjk_runs:
        for c in set(run):
            char_df[c] += 1

    total = len(cjk_runs)
    threshold = max(3, min(8, int(total * 0.01)))
    high_df = {c for c, df in char_df.items() if df > threshold}

    codes = sorted(ord(c) for c in high_df)
    if not codes:
        return []

    best_start, best_cnt = codes[0], 0
    for lo in codes:
        cnt = sum(1 for c in codes if lo <= c <= lo + 80)
        if cnt > best_cnt:
            best_cnt, best_start = cnt, lo

    if best_cnt < 15:
        return []

    garbled_chars = {c for c in high_df if best_start <= ord(c) <= best_start + 80}

    for run in cjk_runs:
        run_set = set(run)
        if not (run_set & garbled_chars):
            continue
        for c in run_set:
            code = ord(c)
            if best_start - 30 <= code <= best_start + 110:
                garbled_chars.add(c)

    return [run for run in cjk_runs if all(c in garbled_chars for c in run)]


def extract_seeds(text: str) -> Dict[str, str]:
    """从 'GB/T XXXX' 的乱码版本提取 G,B,T 种子。"""
    seeds: Dict[str, str] = {}
    std_match = re.search(r'([一-鿿]{2})[／/]([一-鿿])\d{4}', text)
    if std_match:
        gb = std_match.group(1)
        t = std_match.group(2)
        seeds[gb[0]] = 'G'
        seeds[gb[1]] = 'B'
        seeds[t] = 'T'
    return seeds


def auto_split_case(chars: Set[str]) -> Tuple[Set[str], Set[str]]:
    """按码位间隙自动区分大小写CJK字符。"""
    codes = sorted(ord(c) for c in chars)
    if len(codes) < 2:
        return chars, set()

    max_gap, gap_at = 0, 0
    for i in range(len(codes) - 1):
        gap = codes[i + 1] - codes[i]
        if gap > max_gap:
            max_gap, gap_at = gap, i

    if max_gap > 5:
        mid = (codes[gap_at] + codes[gap_at + 1]) // 2
        return ({c for c in chars if ord(c) <= mid},
                {c for c in chars if ord(c) > mid})
    return chars, set()


def decode_run(run: str, mapping: Dict[str, str]) -> str:
    return "".join(mapping.get(c, "?") for c in run)


def guess_from_longest(
    garbled_runs: List[str], mapping: Dict[str, str], seed_text: str
) -> Dict[str, str]:
    """用正确的英文标题（种子文本）推导映射。保留原始大小写。"""
    if not seed_text:
        return mapping

    clean_seed = re.sub(r'[\s\-—–/／]', '', seed_text)
    seed_len = len(clean_seed)

    for run in garbled_runs:
        if len(run) != seed_len:
            continue
        for gc, sc in zip(run, clean_seed):
            if gc in mapping and mapping[gc] != sc:
                break
        else:
            for gc, sc in zip(run, clean_seed):
                mapping[gc] = sc
            return mapping

    return mapping


def _score(mapping: Dict[str, str], garbled_runs: List[str]) -> int:
    """评估映射质量：计数能解码为词典词的词段数。"""
    score = 0
    for run in garbled_runs:
        decoded = decode_run(run, mapping)
        if "?" in decoded:
            continue
        if decoded in DICTIONARY_BY_LEN.get(len(run), []):
            score += 5
            continue
        for wlen in sorted(DICTIONARY_BY_LEN.keys(), reverse=True):
            if wlen > len(run):
                continue
            for word in DICTIONARY_BY_LEN[wlen]:
                if word in decoded:
                    score += 1
                    break
    return score


def crack_by_constraint_search(
    garbled_runs: List[str], trusted: Dict[str, str]
) -> Dict[str, str]:
    """约束搜索破解未映射字符。不修改已信任的映射。"""
    mapping = dict(trusted)

    all_chars: Set[str] = set()
    for run in garbled_runs:
        all_chars.update(run)
    low_codes, high_codes = auto_split_case(all_chars)

    seeds_upper = {c for c, l in mapping.items() if l.isupper()}
    if seeds_upper:
        if seeds_upper & low_codes:
            upper_cjk, lower_cjk = low_codes, high_codes
        else:
            upper_cjk, lower_cjk = high_codes, low_codes
    else:
        freq_low = sum(1 for c in low_codes if c in mapping)
        freq_high = sum(1 for c in high_codes if c in mapping)
        if freq_low >= freq_high:
            lower_cjk, upper_cjk = low_codes, high_codes
        else:
            lower_cjk, upper_cjk = high_codes, low_codes

    freq = Counter()
    for run in garbled_runs:
        for c in run:
            if c not in mapping:
                freq[c] += 1

    unmapped_upper = sorted(
        [c for c in upper_cjk if c not in mapping],
        key=lambda c: freq.get(c, 0), reverse=True)
    used_upper = {ch for ch in mapping.values() if ch.isupper()}
    letters_upper = [l for l in "ETAOINSRHLDCUMFPGWYBVKXJQZ" if l not in used_upper]
    for i, cj in enumerate(unmapped_upper):
        if i < len(letters_upper):
            mapping[cj] = letters_upper[i]

    unmapped_lower = [c for c in lower_cjk if c not in mapping]
    if not unmapped_lower:
        return mapping

    anchors = []
    for rlen in [3, 4, 5, 2, 6]:
        for run in garbled_runs:
            if len(run) != rlen:
                continue
            if not all(c in lower_cjk or c in mapping for c in run):
                continue
            unmapped_in_run = sum(1 for c in run if c not in mapping)
            if unmapped_in_run >= 2 and run not in anchors:
                anchors.append(run)
            if len(anchors) >= 3:
                break
        if len(anchors) >= 3:
            break

    if not anchors:
        freq_lower = Counter()
        for run in garbled_runs:
            for c in run:
                if c in lower_cjk and c not in mapping:
                    freq_lower[c] += 1
        freq_sorted = [c for c, _ in freq_lower.most_common()]
        used_lower = {ch for ch in mapping.values() if ch.islower()}
        letters_lower = [l for l in "etaoinsrhldcumfpgwybvkxjqz" if l not in used_lower]
        for i, cj in enumerate(freq_sorted):
            if i < len(letters_lower):
                mapping[cj] = letters_lower[i]
        return mapping

    best_mapping = dict(mapping)
    best_score = -1

    anchor0 = anchors[0]
    candidates = DICTIONARY_BY_LEN.get(len(anchor0), [])

    for word in candidates:
        candidate = dict(mapping)
        for gc, cc in zip(anchor0, word):
            if gc not in mapping:
                candidate[gc] = cc

        for other in anchors[1:]:
            od = DICTIONARY_BY_LEN.get(len(other), [])
            partial = decode_run(other, candidate)
            matched = [w for w in od
                       if all(candidate.get(gc, w[i]) == w[i]
                              for i, gc in enumerate(other))]
            if len(matched) == 1:
                for gc, cc in zip(other, matched[0]):
                    if gc not in mapping:
                        candidate[gc] = cc

        s = _score(candidate, garbled_runs)
        if s > best_score:
            best_score, best_mapping = s, dict(candidate)

    return best_mapping


def _match_word_at(run: str, start: int, word: str, mapping: Dict[str, str],
                   trusted: Dict[str, str]) -> bool:
    """检查词典词在 run 中从 start 位置开始能否匹配。"""
    for j, wc in enumerate(word):
        gc = run[start + j]
        if gc in trusted and trusted[gc] != wc:
            return False
        if gc in mapping and gc not in trusted and mapping[gc] != wc:
            pass
    return True


def _update_from_match(run: str, start: int, word: str, mapping: Dict[str, str],
                       trusted: Dict[str, str]) -> bool:
    """从匹配位置更新映射。返回是否有变化。"""
    changed = False
    for j, wc in enumerate(word):
        gc = run[start + j]
        if gc not in trusted and (gc not in mapping or mapping[gc] != wc):
            mapping[gc] = wc
            changed = True
    return changed


def refine_by_word_expansion(
    garbled_runs: List[str], mapping: Dict[str, str],
    trusted: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """词级模式匹配迭代精炼。trusted 中的映射不会被覆盖。"""
    if trusted is None:
        trusted = {}

    for _ in range(8):
        improved = False

        for run in garbled_runs:
            candidates = DICTIONARY_BY_LEN.get(len(run), [])
            if not candidates:
                continue
            partial = decode_run(run, mapping)
            unknown = sum(1 for ch in partial if ch == "?")
            if unknown == 0 or unknown == len(run):
                continue

            matched = []
            for word in candidates:
                if all(
                    gc not in mapping or mapping[gc] == word[i]
                    for i, gc in enumerate(run)
                ):
                    matched.append(word)

            if not matched and unknown <= len(run) * 0.5:
                for word in candidates:
                    if all(
                        gc not in trusted or trusted[gc] == word[i]
                        for i, gc in enumerate(run)
                    ):
                        matched.append(word)

            if len(matched) == 1:
                if _update_from_match(run, 0, matched[0], mapping, trusted):
                    improved = True

        proposals: Dict[str, str] = {}
        conflicts: Set[str] = set()

        for run in garbled_runs:
            for wlen in sorted(DICTIONARY_BY_LEN.keys()):
                if wlen >= len(run) or wlen < 4:
                    continue
                max_start = len(run) - wlen
                run_matches: List[Tuple[int, str]] = []
                for word in DICTIONARY_BY_LEN[wlen]:
                    for start in range(max_start + 1):
                        if _match_word_at(run, start, word, mapping, trusted):
                            run_matches.append((start, word))
                if len(run_matches) == 1:
                    start, word = run_matches[0]
                    for j, wc in enumerate(word):
                        gc = run[start + j]
                        if gc in trusted or gc in mapping:
                            continue
                        if gc in conflicts:
                            continue
                        if gc in proposals and proposals[gc] != wc:
                            conflicts.add(gc)
                            del proposals[gc]
                        elif gc not in proposals:
                            proposals[gc] = wc

        for gc, wc in proposals.items():
            mapping[gc] = wc
            improved = True

        if not improved:
            break
    return mapping


def apply_mapping(text: str, mapping: Dict[str, str]) -> str:
    return "".join(mapping.get(c, c) for c in text)


# ---- 方案3: 共享映射表 ----

def load_shared_mappings() -> Dict[str, Dict[str, str]]:
    mappings: Dict[str, Dict[str, str]] = {}
    mapping_dir = Path(_MAPPING_DIR)
    if mapping_dir.exists():
        for f in mapping_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    mappings[f.stem] = json.load(fp)
            except (json.JSONDecodeError, Exception):
                pass
    return mappings


def save_mapping(mapping: Dict[str, str], name: str) -> Path:
    mapping_dir = Path(_MAPPING_DIR)
    mapping_dir.mkdir(parents=True, exist_ok=True)
    path = mapping_dir / f"{name}.json"
    with open(path, "w") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    return path


def match_shared_mapping(
    garbled_runs: List[str], shared: Dict[str, Dict[str, str]]
) -> Optional[Dict[str, str]]:
    all_chars: Set[str] = set()
    for run in garbled_runs:
        all_chars.update(run)
    if not all_chars:
        return None
    for name, mapping in shared.items():
        covered = sum(1 for c in all_chars if c in mapping)
        if covered / len(all_chars) > 0.8:
            return mapping
    return None


# ---- 主流程 ----

def fix_file(filepath: str | Path, seed_text: str = "") -> dict:
    """修复单个 Markdown 文件的英文乱码，返回状态报告 dict。

    Returns:
        {"detected": bool, "fixed": bool, "runs_found": int,
         "unique_chars": int, "chars_mapped": int, "chars_unmapped": int,
         "score": int, "seed_used": bool, "mapping_file": str | None,
         "residual_runs": int}
    """
    path = Path(filepath)

    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        return {"detected": False, "fixed": False, "error": f"读取文件失败: {e}"}

    garbled_runs = extract_garbled_runs(text)
    if not garbled_runs:
        return {
            "detected": False, "fixed": True,
            "runs_found": 0, "unique_chars": 0,
            "chars_mapped": 0, "chars_unmapped": 0,
            "score": 0, "seed_used": bool(seed_text),
            "mapping_file": None, "residual_runs": 0,
        }

    all_chars: Set[str] = set()
    for run in garbled_runs:
        all_chars.update(run)

    shared = load_shared_mappings()
    mapping = match_shared_mapping(garbled_runs, shared)
    reused = mapping is not None

    if mapping is None:
        seeds = extract_seeds(text)
        mapping = dict(seeds)
        if seed_text:
            mapping = guess_from_longest(garbled_runs, mapping, seed_text)

        trusted = dict(mapping)
        mapping = crack_by_constraint_search(garbled_runs, mapping)
        mapping = refine_by_word_expansion(garbled_runs, mapping, trusted)
        mapping.update(trusted)

        score = _score(mapping, garbled_runs)

        mapping_file = str(save_mapping(mapping, path.stem))
    else:
        score = _score(mapping, garbled_runs)
        mapping_file = None  # 复用时不重复保存

    # 应用映射
    fixed_text = apply_mapping(text, mapping)

    # 写回文件
    with open(path, "w", encoding="utf-8") as f:
        f.write(fixed_text)

    remaining = extract_garbled_runs(fixed_text)

    unmapped = [c for c in all_chars if c not in mapping]

    return {
        "detected": True,
        "fixed": len(remaining) == 0,
        "runs_found": len(garbled_runs),
        "unique_chars": len(all_chars),
        "chars_mapped": len(mapping),
        "chars_unmapped": len(unmapped),
        "score": score,
        "seed_used": bool(seed_text),
        "mapping_file": mapping_file,
        "residual_runs": len(remaining),
        "reused": reused,
    }


def fix_directory(dirpath: str | Path, seed_text: str = "") -> List[dict]:
    """批量修复目录中的 Markdown 文件。返回状态报告列表。"""
    results = []
    for md_file in sorted(Path(dirpath).rglob("*.md")):
        result = fix_file(md_file, seed_text=seed_text)
        results.append({"file": str(md_file), **result})
    return results
