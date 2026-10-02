import ast
from dataclasses import fields
from pathlib import Path

import advisor
from advisor.data.schema_map import ENTITY_MAPS, MODEL_FOR_ENTITY, TEAMMATE_ONLY_NAMES, TEAMMATE_TABLES

PACKAGE_ROOT = Path(advisor.__file__).resolve().parent
DATA_DIR = PACKAGE_ROOT / "data"


def test_teammate_tables_lists_all_23_v2_tables():
    assert len(TEAMMATE_TABLES) == 23


def test_every_model_field_is_mapped_and_no_extra_mappings():
    for entity, model in MODEL_FOR_ENTITY.items():
        field_names = {f.name for f in fields(model)}
        assert set(ENTITY_MAPS[entity].columns) == field_names, entity


def test_every_entity_except_log_export_has_a_model():
    assert set(ENTITY_MAPS) - set(MODEL_FOR_ENTITY) == {"log_export"}


def test_every_mapped_table_is_a_teammate_table():
    for entity_map in ENTITY_MAPS.values():
        assert entity_map.table in TEAMMATE_TABLES


def test_client_id_maps_to_customer_id():
    assert ENTITY_MAPS["client"].table == "customers"
    assert ENTITY_MAPS["client"].columns["client_id"] == "customer_id"
    assert ENTITY_MAPS["account"].columns["client_id"] == "customer_id"


def test_log_export_maps_to_chat_log_exports():
    entity_map = ENTITY_MAPS["log_export"]
    assert entity_map.table == "chat_log_exports"
    assert entity_map.columns["log_export_id"] == "log_id"
    assert entity_map.columns["chat_session_id"] == "session_id"


def _python_files_outside_data():
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if DATA_DIR in path.parents:
            continue
        yield path


def test_boundary_no_teammate_names_outside_data_package():
    violations = []
    files = list(_python_files_outside_data())
    assert files, "expected modules outside advisor/data/"
    for path in files:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in TEAMMATE_ONLY_NAMES:
                    violations.append(f"{path.name}:{node.lineno} string {node.value!r}")
            elif isinstance(node, ast.Name) and node.id == "customer_id":
                violations.append(f"{path.name}:{node.lineno} name customer_id")
            elif isinstance(node, ast.Attribute) and node.attr == "customer_id":
                violations.append(f"{path.name}:{node.lineno} attribute customer_id")
            elif isinstance(node, ast.arg) and node.arg == "customer_id":
                violations.append(f"{path.name}:{node.lineno} argument customer_id")
            elif isinstance(node, ast.keyword) and node.arg == "customer_id":
                violations.append(f"{path.name}:{node.lineno} keyword customer_id")
    assert violations == []
