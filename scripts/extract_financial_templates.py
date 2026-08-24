import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_PATH = ROOT / "tmp_pravilnik_text.txt"
OUT_PATH = ROOT / "data" / "financial_statement_templates.json"


SECTIONS = [
    ("Биланс на состојба", 1, 137, "balance_sheet", 303, 613),
    ("Биланс на успех", 200, 281, "income_statement", 626, 841),
    ("Cash Flow", 300, 353, "cash_flow", 852, 993),
]


def clean_name(parts):
    text = " ".join(part for part in parts if part)
    text = re.sub(r"--- PAGE \d+ ---", " ", text)
    text = re.sub(r"^\d+\s+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.)])", r"\1", text)
    return text


def infer_type(statement, code, name):
    if statement == "Биланс на состојба":
        return "Актива" if code <= 84 else "Пасива"
    if statement == "Биланс на успех":
        if re.search(r"ДОБИВКА|ЗАГУБА|ДАНОК", name):
            return "Пресметка"
        if 200 <= code <= 225:
            return "Приход"
        if 226 <= code <= 275:
            return "Расход"
        return "Пресметка"
    if statement == "Cash Flow":
        if 300 <= code <= 305 or 317 <= code <= 325 or 337 <= code <= 340 or code == 347:
            return "Прилив"
        if 306 <= code <= 314 or 326 <= code <= 334 or 341 <= code <= 344 or code == 348:
            return "Одлив"
        return "Пресметка"
    return ""


def parse_positions(section_lines, statement, min_code, max_code, report_key):
    rows = []
    buffer = []
    seen = set()

    def add(code, parts):
        if code < min_code or code > max_code or code in seen:
            return
        name = clean_name(parts)
        skip = {
            "во денари",
            "ПОЗИЦИЈА",
            "АКТИВА",
            "ПАСИВА",
            "Датум:",
            "Изготвил: (име и презиме и потпис)",
        }
        if code == min_code:
            for marker in ("A. ", "А. "):
                if marker in name:
                    name = name[name.index(marker):]
                    break
        if not name or name in skip or "Одговорно лице" in name:
            return
        rows.append(
            {
                "statement": statement,
                "report_key": report_key,
                "code": f"{code:03d}",
                "position": name,
                "accounts": "",
                "type": infer_type(statement, code, name),
                "source": "Pravilnik-za-finansiskite-izvestai.pdf",
            }
        )
        seen.add(code)

    for raw in section_lines:
        line = raw.strip()
        if (
            not line
            or line.startswith("--- PAGE")
            or line.startswith("Образец")
            or line.startswith("ОБРАЗЕЦ")
            or line.startswith("Назив на")
            or "ЕМБС" in line
        ):
            continue
        if line in {
            "Број на",
            "позиција",
            "Износ",
            "Тековна",
            "деловна",
            "година",
            "Претходна",
            "Број на белешка",
        }:
            continue

        fixed = re.sub(r"(\d{1,2})\s+(\d{1,2})\s*$", r"\1\2", line)
        match = re.search(r"(.+?)\s+(\d{3})\s*$", fixed)
        if match:
            add(int(match.group(2)), buffer + [match.group(1).strip()])
            buffer = []
            continue

        standalone_code = re.fullmatch(r"(\d{3})", fixed)
        if standalone_code:
            add(int(standalone_code.group(1)), buffer)
            buffer = []
            continue

        if re.fullmatch(r"[\d\s]+", fixed):
            continue
        buffer.append(fixed)

    return sorted(rows, key=lambda item: item["code"])


def main():
    lines = [line.strip() for line in TEXT_PATH.read_text(encoding="utf-8").splitlines()]
    templates = []
    for statement, min_code, max_code, report_key, start, end in SECTIONS:
        templates.extend(
            parse_positions(
                lines[start:end],
                statement,
                min_code,
                max_code,
                report_key,
            )
        )

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(
        json.dumps({"templates": templates}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"written {OUT_PATH} ({len(templates)} rows)")


if __name__ == "__main__":
    main()
