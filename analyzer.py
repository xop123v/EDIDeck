# analyzer.py
from collections import Counter

def analyze(containers):
    issues = []
    seen = set()
    for c in containers:
        cid = c.get("container")
        if not cid:
            issues.append("Контейнер без ID (пустой EQD).")
        else:
            if cid in seen:
                issues.append(f"Дубликат контейнера: {cid}")
            seen.add(cid)
        if c.get("dg") and not c.get("unno"):
            issues.append(f"DG без UN No: {cid}")
        if c.get("reefer") and not c.get("temperature"):
            issues.append(f"Reefer без температуры: {cid}")
        if not c.get("bay") or not c.get("row") or not c.get("tier"):
            issues.append(f"Неполная позиция (bay/row/tier) для {cid}")
    total = len(containers)
    dg_count = sum(1 for c in containers if c.get("dg"))
    reefer_count = sum(1 for c in containers if c.get("reefer"))
    ports = Counter(c.get("pod") or "UNKNOWN" for c in containers)
    summary = {"total": total, "dg_count": dg_count, "reefer_count": reefer_count, "ports": dict(ports)}
    return issues, summary
