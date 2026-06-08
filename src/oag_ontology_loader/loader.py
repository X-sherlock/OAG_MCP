from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from oag_ontology_loader.models import ONTOLOGY_FILE_NAMES, OntologyCatalog
from oag_ontology_loader.period_expander import expand_period_templates, load_period_variants
from oag_ontology_loader.validator import validate_catalog_sections


# 项目根目录用于让脚本、测试和包内代码在不同 cwd 下都能定位 ontology 目录。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ONTOLOGY_DIR = PROJECT_ROOT / "ontology"


def load_ontology(ontology_dir: str | Path | None = None) -> OntologyCatalog:
    """加载本体目录并返回经过结构校验的 OntologyCatalog。

    ontology_dir 为空时读取项目内置 ontology 目录；显式传入路径主要用于测试、
    打包验证或加载一套替代本体配置。
    """

    root = Path(ontology_dir) if ontology_dir is not None else DEFAULT_ONTOLOGY_DIR
    sections = {
        section: _load_yaml_compatible_json(root / filename)
        for section, filename in ONTOLOGY_FILE_NAMES.items()
    }
    validated = validate_catalog_sections(sections)
    periods = load_period_variants(root)
    expanded = expand_period_templates(validated, periods).sections
    return OntologyCatalog(ontology_dir=root, **expanded)


def _load_yaml_compatible_json(path: Path) -> Any:
    """读取一个本体文件，优先按 JSON 解析，必要时回退到 PyYAML。

    这里允许 JSON-compatible YAML，是为了让本体文件既能被简单 JSON 解析器读取，
    又能在需要注释或更自然列表写法时使用 YAML 语法。
    """

    if not path.exists():
        raise FileNotFoundError(f"Ontology file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError(
                f"{path} is not JSON-compatible YAML and PyYAML is not installed"
            ) from exc
        parsed = yaml.safe_load(text)
        return parsed
