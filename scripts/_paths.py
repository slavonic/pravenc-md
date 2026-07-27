#!/usr/bin/env python3
"""
Shared repository paths, so the scripts can be run from any working directory.
"""

from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent

ARTICLES_DIR = REPO_ROOT / "articles"
DATA_DIR = REPO_ROOT / "data"
CHAR_MAPS_DIR = DATA_DIR / "char-maps"

ARTICLE_URLS_FILE = REPO_ROOT / "article_urls.txt"
CU_MAPPING_FILE = DATA_DIR / "cu.json"
