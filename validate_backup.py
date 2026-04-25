"""
DBバックアップの検証スクリプト
このスクリプトは、DBに保存する前にJSONファイルが正しく構造化されているか検証します。
"""

import json
import sys
from datetime import date
from typing import List
from pathlib import Path

try:
    from pydantic import BaseModel, ValidationError
except ImportError:
    print("ERROR: pydantic is not installed. Run: pip install pydantic")
    sys.exit(1)


# モデル定義（backend.pyと同じ）
class AlcoholItem(BaseModel):
    percent: int
    ml: int


class AlcoholMasterBase(BaseModel):
    name: str
    percent: int
    default_ml: int


class IntakeCreate(BaseModel):
    date: date
    items: List[AlcoholItem]


class BackupPayload(BaseModel):
    daily_intakes: List[IntakeCreate]
    alcohol_masters: List[AlcoholMasterBase]


def validate_backup_file(file_path: str) -> bool:
    """
    JSONバックアップファイルを検証して、DB復旧可能か判定します。
    
    Args:
        file_path: JSONファイルのパス
        
    Returns:
        検証成功時True、失敗時False
    """
    print("=" * 70)
    print("DB Backup Validation")
    print("=" * 70)
    
    # ファイルの存在確認
    if not Path(file_path).exists():
        print(f"ERROR: File not found: {file_path}")
        return False
    
    print(f"File: {file_path}")
    print("-" * 70)
    
    try:
        # JSONファイルを読み込む
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("JSON parsing: OK")
        
        # BackupPayloadで検証
        backup = BackupPayload(**data)
        print("Schema validation: OK")
        print()
        
        # 統計情報を表示
        print("Backup Statistics:")
        print(f"  - Alcohol Masters: {len(backup.alcohol_masters)} records")
        for i, master in enumerate(backup.alcohol_masters, 1):
            print(f"    {i}. {master.name}")
            print(f"       Percent: {master.percent}%, Default ml: {master.default_ml}")
        
        print(f"\n  - Daily Intakes: {len(backup.daily_intakes)} records")
        
        # 日付と飲酒内容を表示
        total_records = 0
        for intake in backup.daily_intakes:
            total_records += 1
            if total_records <= 5:
                items_str = ", ".join([f"{item.percent}%: {item.ml}ml" for item in intake.items])
                print(f"    {intake.date}: {items_str}")
        
        if len(backup.daily_intakes) > 5:
            print(f"    ... and {len(backup.daily_intakes) - 5} more records")
        
        print()
        print("=" * 70)
        print("Validation Result: PASSED")
        print("=" * 70)
        print()
        print("このファイルはDB復旧に使用できます。")
        print("Webアプリケーションで 'データ復元' > 'バックアップファイルをアップロード' で")
        print("このファイルを選択して、復旧を実行してください。")
        print()
        return True
        
    except json.JSONDecodeError as e:
        print(f"JSON Parsing Error: {str(e)}")
        print("  JSONファイルが正しくありません。")
        return False
        
    except ValidationError as e:
        print(f"Schema Validation Error: {str(e)}")
        print("\n詳細なエラー情報:")
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error['loc'])
            print(f"  Field: {loc}")
            print(f"  Error: {error['msg']}")
            print(f"  Value: {error.get('input', 'N/A')}")
            print()
        return False
        
    except Exception as e:
        print(f"Unexpected Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # JSONファイルパス
    import os
    home = os.path.expanduser("~")
    json_path = os.path.join(home, r"OneDrive\デスクトップ\alcohol_tracker_backup_20260425_094628.json")
    
    # ユーザーが引数を指定した場合はそれを使用
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    
    success = validate_backup_file(json_path)
    sys.exit(0 if success else 1)
