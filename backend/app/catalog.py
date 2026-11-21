import json
from pathlib import Path


_catalog_path = Path(__file__).resolve().parents[2] / 'frontend' / 'src' / 'careers.json'
CAREER_CATALOG = json.loads(_catalog_path.read_text(encoding='utf-8'))
CAREER_LABELS = frozenset(
    career['label'] for group in CAREER_CATALOG['groups'] for career in group['careers']
)
