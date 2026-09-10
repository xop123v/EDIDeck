# filters.py
from typing import List, Dict

def filter_dg(containers):
    return [c for c in containers if c.get("dg")]

def filter_reefer(containers):
    return [c for c in containers if c.get("reefer")]

def filter_movement(containers, movement):
    return [c for c in containers if (c.get("movement") or "unknown") == movement]

def filter_pod(containers, pod_code):
    return [c for c in containers if (c.get("pod") or "").upper() == pod_code.upper()]

def filter_pol(containers, pol_code):
    return [c for c in containers if (c.get("pol") or "").upper() == pol_code.upper()]

def filter_unno(containers, unno):
    return [c for c in containers if (c.get("unno") or "") == unno]

def filter_weight_range(containers, min_w=None, max_w=None):
    out = []
    for c in containers:
        try:
            w = float(c.get("weight") or 0)
        except:
            w = 0
        if min_w is not None and w < min_w:
            continue
        if max_w is not None and w > max_w:
            continue
        out.append(c)
    return out

def text_search(containers, text):
    t = text.lower()
    out = []
    for c in containers:
        hay = " ".join([
            str(c.get("container","")), str(c.get("pol","")), str(c.get("pod","")),
            str(c.get("unno","")), str(c.get("psn","")), str(c.get("remark","")), " ".join(c.get("rff",[]))
        ]).lower()
        if t in hay:
            out.append(c)
    return out

def combine_filters(*funcs):
    def combined(containers):
        res = containers
        for f in funcs:
            res = f(res)
        return res
    return combined
