# grimscribe.py
# Educational wordlist generator (Grimscribe)
# Usage: from grimscribe import generate_wordlist, WordlistConfig

import re
import random
import itertools
from urllib.parse import urlparse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Iterable, Set

# ------------------------------
# Config dataclass
# ------------------------------

@dataclass
class WordlistConfig:
    max_words: int = 20000
    max_token_length: int = 32
    min_token_length: int = 2
    max_combos: int = 50000
    max_depth: int = 3
    leet_levels: int = 2
    add_casing: bool = True
    add_number_tails: bool = True
    number_tail_range: range = range(0, 21)   # réduit à 0..20
    add_prefix_suffix: bool = True
    balance_mode: str = "balanced"            # "words", "numbers", "balanced"
    seed: Optional[int] = None
    allow_duplicates: bool = False

# ------------------------------
# Helpers
# ------------------------------

BASIC_STOPWORDS = {"the","and","or","of","a","an","to","in","on","for","by","with","at","from"}

BASIC_SYNONYMS = {
    "admin": ["administrator","root","sysadmin"],
    "password": ["pass","pwd","key","secret"],
    "login": ["signin","auth","access"],
    "nebula": ["cosmos","galaxy","nova","star"],
    "team": ["crew","group","squad","guild"],
    "hack": ["hacker","hacking","exploit","crack"],
    "secure": ["security","safe","protection","shield"],
}

LEET_MAP_EXTENDED = {
    "a": ["a","@","4"],
    "b": ["b","8"],
    "e": ["e","3"],
    "g": ["g","9"],
    "i": ["i","1","!"],
    "l": ["l","1"],
    "o": ["o","0"],
    "s": ["s","5","$"],
    "t": ["t","7"],
    "z": ["z","2"]
}

def normalize_text(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\-_.:/ ]+", " ", s)
    return re.sub(r"\s+", " ", s)

def split_tokens(s: str) -> List[str]:
    return [p for p in re.split(r"[ \-_.:/]+", s) if p]

def parse_url(url: str) -> Dict[str, str]:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.split(":")[0]
        root = domain.split(".")[-2] if "." in domain else domain
        return {"host": parsed.netloc, "path": parsed.path.strip("/"), "domain": domain, "root": root}
    except Exception:
        return {"host":"", "path":"", "domain":"", "root":""}

def expand_synonyms(tokens: List[str]) -> List[str]:
    out = set(tokens)
    for t in tokens:
        if t in BASIC_SYNONYMS:
            out |= set(BASIC_SYNONYMS[t])
    return list(out)

def expand_word_derivatives(token: str) -> List[str]:
    derivs = []
    if token.endswith("ing"):
        derivs.append(token[:-3])
    elif token.endswith("er"):
        derivs.append(token[:-2])
    elif token.endswith("s"):
        derivs.append(token[:-1])
    else:
        derivs += [token+"ing", token+"er", token+"s"]
    return derivs

def casing_variants(token: str) -> List[str]:
    return [token, token.capitalize(), token.upper(), token.title()]

def leet_variants(token: str, level: int) -> List[str]:
    if level <= 0: return [token]
    m = LEET_MAP_EXTENDED
    variants = {token}
    for i, ch in enumerate(token):
        low = ch.lower()
        if low in m:
            for rep in m[low]:
                variants.add(token[:i] + rep + token[i+1:])
    return list(variants)

def add_number_tails(tokens: Iterable[str], rng: range) -> List[str]:
    out = []
    for t in tokens:
        out.append(t)
        for n in rng:
            out.append(f"{t}{n}")
    return out

def filter_tokens(tokens: Iterable[str], cfg: WordlistConfig) -> List[str]:
    out = []
    for t in tokens:
        if cfg.min_token_length <= len(t) <= cfg.max_token_length:
            out.append(t)
    return list(dict.fromkeys(out))  # dedup en gardant l'ordre

def combine_tokens(tokens: List[str], cfg: WordlistConfig) -> List[str]:
    combos = set()
    base = tokens[:200]  # limiter explosion
    for depth in range(2, cfg.max_depth+1):
        for combo in itertools.combinations(base, depth):
            combos.add("-".join(combo))
            combos.add("_".join(combo))
    return list(combos)

# ------------------------------
# Public API
# ------------------------------

def generate_wordlist(inputs: Dict[str,str], extra_terms: Optional[List[str]]=None, config: Optional[WordlistConfig]=None) -> List[str]:
    cfg = config or WordlistConfig()
    if cfg.seed: random.seed(cfg.seed)

    raw = []
    for k,v in (inputs or {}).items():
        if v: raw.append(normalize_text(v))
    if extra_terms: raw.append(normalize_text(" ".join(extra_terms)))

    if "url" in inputs and inputs["url"]:
        url_info = parse_url(inputs["url"])
        raw += [url_info.get("domain",""), url_info.get("root",""), url_info.get("path","")]

    tokens = []
    for chunk in raw: tokens += split_tokens(chunk)
    tokens = [t for t in tokens if t not in BASIC_STOPWORDS]
    tokens = filter_tokens(tokens, cfg)

    enriched = set(tokens)
    enriched |= set(expand_synonyms(tokens))
    for t in tokens: enriched |= set(expand_word_derivatives(t))

    variants = set()
    for t in enriched:
        vset = {t}
        if cfg.add_casing: vset |= set(casing_variants(t))
        vset |= set(leet_variants(t, cfg.leet_levels))
        if cfg.balance_mode != "words" and cfg.add_number_tails:
            vset |= set(add_number_tails(vset, cfg.number_tail_range))
        variants |= vset

    variants = filter_tokens(list(variants), cfg)
    combos = combine_tokens(variants, cfg)

    final = []
    seen = set()
    for w in variants + combos:
        if not cfg.allow_duplicates and w in seen: continue
        final.append(w); seen.add(w)
        if len(final) >= cfg.max_words: break

    return final

# ------------------------------
# CLI demo
# ------------------------------

if __name__ == "__main__":
    demo_inputs = {
        "url": "https://orbital-sec.net/solutions/skyshield",
        "title": "SkyShield Satellite Defense",
        "company": "Orbital Security",
        "keywords": "satellite encryption orbital defense telemetry comms",
        "location": "Houston",
        "user": "astrosec",
        "events": "launch2024 solarstorm",
        "base": "SkyShield"
    }
    wl = generate_wordlist(demo_inputs, extra_terms=["uplink","payload","orbit"], config=WordlistConfig(seed=42))
    print("\n".join(wl[:50]))
