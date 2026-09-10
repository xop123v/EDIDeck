# edi_parser.py
import re
import os

SEG_SEP_CANDIDATES = ["'", "\n", "~"]  # возможные разделители сегментов
DATA_SEP = "+"

def _norm(s):
    return s.strip() if s else ""

def _detect_segment_separator(raw):
    # Попытаемся определить разделитель сегментов: чаще всего "'" но иногда "~" или только переводы строки
    counts = {sep: raw.count(sep) for sep in SEG_SEP_CANDIDATES}
    # выберем самый частый
    sep = max(counts, key=counts.get)
    if counts[sep] == 0:
        return "\n"
    # Дополнительная проверка: если первый сегмент после разделения не начинается с известного тега, попробуем другой сепаратор
    def first_tag_with(sep_char):
        parts = [s.strip() for s in raw.split(sep_char) if s.strip()]
        if not parts:
            return ""
        first = parts[0]
        return first.split(DATA_SEP)[0].strip().upper()
    first = first_tag_with(sep)
    known_tags = {"UNH","EQD","LOC","MEA","FTX","DGS","IMD","RFF","TMP"}
    if first and first not in known_tags:
        # попробуем другие кандидаты
        for s in SEG_SEP_CANDIDATES:
            if s == sep:
                continue
            f = first_tag_with(s)
            if f in known_tags:
                return s
        # fallback
        return "\n"
    return sep

def _extract_container_from_eqd(parts):
    # EQD+CN+MSDU 5708672+45G1+++5
    if len(parts) >= 3:
        candidate = parts[2].replace(" ", "")
        # простая валидация: контейнеры обычно содержат буквы+цифры, длина > 4
        if re.search(r"[A-Z0-9]{4,}", candidate, re.IGNORECASE):
            return candidate
        return candidate
    return ""

def _parse_loc_147(value):
    # value examples: "0240988::5" or "0520608::5" or "24/09/88"
    s = value.split(":")[0]
    digits = re.sub(r"\D", "", s)
    if len(digits) >= 6:
        bay = digits[:3].lstrip("0") or digits[:3]
        row = digits[3:5].lstrip("0") or digits[3:5]
        tier = digits[5:].lstrip("0") or digits[5:]
        return bay, row, tier
    m = re.findall(r"\d+", s)
    if len(m) >= 3:
        bay = m[0].zfill(3)
        row = m[1].zfill(2)
        tier = m[2]
        return bay.lstrip("0") or bay, row.lstrip("0") or row, tier.lstrip("0") or tier
    return s, "", ""

def _safe_open(path):
    # Попытка открыть файл в нескольких кодировках
    encs = ["utf-8", "utf-8-sig", "cp1251", "latin-1"]
    for e in encs:
        try:
            with open(path, "r", encoding=e, errors="strict") as f:
                return f.read()
        except Exception:
            continue
    # fallback: открыть с игнорированием ошибок
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def parse_edi(file_path):
    """
    Возвращает список контейнеров — словарей с полями:
    container, size, bay, row, tier, pol, pod, weight, unno, class, packing_group,
    flash_point, ems, psn, remark, dg (bool), reefer (bool), temperature, ventilation,
    ftx (list), rff (list), movement (load/discharge/unknown), raw_segments (list)
    """
    containers = []
    raw = _safe_open(file_path)
    # Нормализуем: удалим лишние двойные пробелы
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    seg_sep = _detect_segment_separator(raw)
    # Разбиваем на сегменты
    segments = [s.strip() for s in raw.split(seg_sep) if s.strip()]
    current = None

    for seg in segments:
        # Уберём возможные лидирующие/трейлинг символы
        seg = seg.strip()
        # Разделим по '+', но не теряем содержимое
        parts = seg.split(DATA_SEP)
        tag = parts[0].strip() if parts else ""
        # Начало блока контейнера
        if tag == "EQD":
            cont_id = _extract_container_from_eqd(parts)
            size = parts[3] if len(parts) > 3 else ""
            current = {
                "container": cont_id,
                "size": _norm(size),
                "bay": "",
                "row": "",
                "tier": "",
                "pol": "",
                "pod": "",
                "weight": "",
                "unno": "",
                "class": "",
                "packing_group": "",
                "flash_point": "",
                "ems": "",
                "psn": "",
                "remark": "",
                "dg": False,
                "reefer": False,
                "temperature": "",
                "ventilation": "",
                "ftx": [],
                "rff": [],
                "raw_segments": [],
                "movement": "unknown"
            }
            containers.append(current)
            continue

        if current is None:
            # сегменты до первого EQD — игнорируем или можно расширить для общей информации
            continue

        current["raw_segments"].append(seg)

        # LOC
        if tag == "LOC":
            qual = parts[1] if len(parts) > 1 else ""
            val = parts[2] if len(parts) > 2 else ""
            qual = qual.strip()
            if qual == "147":
                bay, row, tier = _parse_loc_147(val)
                current["bay"] = bay
                current["row"] = row
                current["tier"] = tier
            elif qual == "9":
                current["pol"] = val.split(":")[0]
            elif qual == "11":
                current["pod"] = val.split(":")[0]
            elif qual == "76":
                current["movement"] = "load"
            elif qual == "83":
                current["movement"] = "discharge"

        # MEA VGM weight
        if tag == "MEA" and "VGM" in seg.upper():
            m = re.search(r":?KGM[:]?([0-9\.]+)", seg, re.IGNORECASE)
            if m:
                current["weight"] = m.group(1)

        # DGS / IMD
        if tag.startswith("DGS") or tag.startswith("IMD") or seg.upper().startswith("DGS") or seg.upper().startswith("IMD"):
            current["dg"] = True
            # сначала ищем явный UN или UNNO
            m_un = re.search(r"\bUN(?:NO)?[:​\s\-]*([0-9]{3,4})\b", seg, re.IGNORECASE)
            if not m_un:
                # fallback: 4-digit UN number standalone
                m_un = re.search(r"\b([0-9]{4})\b", seg)
            if m_un:
                current["unno"] = m_un.group(1)
            # попытка найти класс/packing group
            m_class = re.search(r"\bCLASS[:​\s]*([0-9A-Za-z\-]+)", seg, re.IGNORECASE)
            if m_class:
                current["class"] = m_class.group(1)

        # FTX free text
        if tag == "FTX":
            txt = ""
            if len(parts) >= 4:
                txt = parts[3]
            elif len(parts) >= 3:
                txt = parts[2]
            txt = txt.strip()
            if txt:
                current["ftx"].append(txt)
                if any(k in txt.upper() for k in ("LITHIUM","DANGEROUS","ENVIRONMENTALLY","RESIN","ACID","BATTERIES","SODIUM","DG")):
                    current["psn"] = (current.get("psn") + "; " + txt).strip("; ")
                    current["dg"] = True
                else:
                    current["remark"] = (current.get("remark") + "; " + txt).strip("; ")

        # TMP temperature for reefers
        if tag == "TMP":
            if len(parts) >= 3:
                m = re.search(r"([+-]?\d+)", parts[2])
                if m:
                    temp = m.group(1)
                    current["temperature"] = temp + "°C"
                    current["reefer"] = True
            else:
                m = re.search(r"([+-]?\d+)\s*:?\s*CEL", seg, re.IGNORECASE)
                if m:
                    current["temperature"] = m.group(1) + "°C"
                    current["reefer"] = True

        # RFF references
        if tag == "RFF":
            if len(parts) >= 2:
                current["rff"].append(parts[1])

        # Дополнительные эвристики
        if any("DG" in t.upper() or "DANGEROUS" in t.upper() for t in current.get("ftx", [])):
            current["dg"] = True

    # Постобработка
    for c in containers:
        for k in ["pol","pod","weight","unno","class","psn","remark","size","bay","row","tier","temperature","movement"]:
            c.setdefault(k, "")
        if isinstance(c.get("weight"), (int, float)):
            c["weight"] = str(c["weight"])
        c["dg"] = bool(c.get("dg"))
        c["reefer"] = bool(c.get("reefer"))
    return containers
