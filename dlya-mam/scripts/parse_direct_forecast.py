"""Разбирает выгрузки «Прогноз бюджета» Яндекс.Директа (.xls) в один CSV.

Запуск:  python3 -I dlya-mam/scripts/parse_direct_forecast.py
Вход:    dlya-mam/inputs/direct/*.xls (как их отдаёт Директ, без правок)
Выход:   dlya-mam/zamery/z03-direct-forecast.csv
Нужен пакет xlrd (pip install xlrd) — только для чтения старого формата .xls.
Числа берутся при объёме трафика 100 (верх) и 62 (середина), чтобы не зависеть
от того, какой объём выбрал человек при выгрузке.
"""
import csv
import pathlib
import re

import xlrd

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEAD = "Предложенные фразы"


def col(header, pattern):
    for i, h in enumerate(header):
        if re.search(pattern, h):
            return i
    raise KeyError(pattern)


def parse(path):
    sh = xlrd.open_workbook(str(path)).sheet_by_name("Фразы")
    cells = [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]
    regions = next(r[0] for r in cells if str(r[0]).startswith("Регионы показа")).split(":", 1)[1].strip()
    date = next(re.search(r"\d\d\.\d\d\.\d{4}", r[0]).group(0) for r in cells if "по состоянию на" in str(r[0]))
    h_i = next(i for i, r in enumerate(cells) if r[0] == HEAD)
    h = cells[h_i]
    c = {
        "requests": col(h, r"^Примерное количество запросов"),
        "imp100": col(h, r"показов в месяц \(при объёме трафика 100\)"),
        "clk100": col(h, r"переходов в месяц \(при объёме трафика 100\)"),
        "cpc100": col(h, r"списываемая цена клика \(при объёме трафика 100\)"),
        "bud100": col(h, r"бюджет, руб\. \(при объёме трафика 100\)"),
        "clk62": col(h, r"переходов в месяц \(при объёме трафика 62\)"),
        "cpc62": col(h, r"списываемая цена клика \(при объёме трафика 62\)"),
        "bud62": col(h, r"бюджет, руб\. \(при объёме трафика 62\)"),
    }
    for r in cells[h_i + 1:]:
        if not r[0] or str(r[0]).startswith("Итого"):
            break
        yield {"file": path.name, "price_date": date, "regions": regions, "phrase": r[0],
               **{k: r[i] for k, i in c.items()}}


def main():
    rows = [x for f in sorted((ROOT / "inputs" / "direct").glob("*.xls")) for x in parse(f)]
    out = ROOT / "zamery" / "z03-direct-forecast.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "строк →", out)


if __name__ == "__main__":
    main()
