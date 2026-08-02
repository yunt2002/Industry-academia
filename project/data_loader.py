import os
import sys
from typing import Optional

import pandas as pd

def load_from_file(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {path}")

    if path.endswith(".csv"):
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)
    return df

def load_from_database(conn_string: str, query: str) -> pd.DataFrame:
    from sqlalchemy import create_engine

    engine = create_engine(conn_string)
    df = pd.read_sql(query, engine)
    return df

def load_from_api(url: str, headers: Optional[dict] = None) -> pd.DataFrame:
    import requests

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    records = data["results"] if isinstance(data, dict) and "results" in data else data
    return pd.DataFrame(records)

def load_from_gsheet(sheet_id: str, sheet_name: str = "Sheet1") -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Load a CSV or Excel file and export it to CSV.")
    parser.add_argument("source", nargs="?", default=os.path.join("data", "your_sales_data.csv"),
                        help="Input file path (CSV or Excel). Default: data/your_sales_data.csv")
    parser.add_argument("--output", "-o", default=os.path.join("data", "sales_raw.csv"),
                        help="Output CSV path. Default: data/sales_raw.csv")
    args = parser.parse_args()

    source_path = args.source
    output_path = args.output
    output_dir = os.path.dirname(output_path) or "."

    if not os.path.exists(source_path):
        print(f"ERROR: 데이터 파일을 찾을 수 없습니다: {source_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    df = load_from_file(source_path)
    df.to_csv(output_path, index=False)
    print(f"불러오기 완료: {len(df)}행 -> {output_path}")


if __name__ == "__main__":
    main()