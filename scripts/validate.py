"""Локальная проверка стартовых контрактов; не серверный публикационный шлюз."""
from pathlib import Path
import copy
import hashlib
import json
import unicodedata
import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
validators = {}
examples = {}
for name in ("topic", "source", "article", "review"):
    schema = json.loads((ROOT / f"schemas/{name}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    example = json.loads((ROOT / f"examples/{name}.json").read_text())
    validator.validate(example)
    validators[name] = validator
    examples[name] = example

def must_fail(name, data):
    assert list(validators[name].iter_errors(data)), f"Негативный тест пропущен: {name}"

bad = copy.deepcopy(examples["article"])
bad.update(status="published", review_id=None, publication=None)
must_fail("article", bad)
bad = copy.deepcopy(examples["review"])
bad["human"] = False
must_fail("review", bad)
bad = copy.deepcopy(examples["review"])
bad["decision"] = "approved"
must_fail("review", bad)
bad = copy.deepcopy(examples["source"])
bad["checked_at"] = "не дата"
must_fail("source", bad)
bad = copy.deepcopy(examples["topic"])
bad["unexpected"] = True
must_fail("topic", bad)
bad = copy.deepcopy(examples["article"])
bad["claims"][0].update(support="supported", source_ids=[])
must_fail("article", bad)

article = examples["article"]
review = examples["review"]
assert article["topic_id"] == examples["topic"]["id"]
assert set(article["source_ids"]) == {s for c in article["claims"] for s in c["source_ids"]}
assert set(article["source_ids"]) == {examples["source"]["id"]}
assert review["article_id"] == article["id"] and review["article_version"] == article["version"]
assert article["review_id"] == review["id"]
def normalize(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    if isinstance(value, list):
        return [normalize(x) for x in value]
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    return value
payload = normalize({k: article[k] for k in ("title", "body_markdown", "claims", "disclosures", "specialty", "language")})
digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
assert digest == article["content_hash"] == review["content_hash"]
models = yaml.safe_load((ROOT / "config/models.yaml").read_text())
specialties = yaml.safe_load((ROOT / "config/specialties.yaml").read_text())
assert models["external_calls_enabled"] is False
assert not models["experiments"]["deepseek_super_agent"]["production_allowed"]
assert [k for k, v in specialties["specialties"].items() if v["enabled"]] == ["cosmetology"]
assert len(models["routing"]) == len(list((ROOT / "prompts").glob("*.md"))) == 8
print("OK: 4 схемы, 4 примера, 6 негативных проверок, связи и хеш примеров, 2 YAML, 8 ролей.")
print("Не проверены: приложение, авторизация, CMS, реальные источники и публикационный шлюз — они ещё не реализованы.")
