import json
from datetime import date
from typing import List
from pydantic import BaseModel

# JSONで定義されたモデルをシンプルに再定義
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

# JSONファイルを読み込んで検証
json_path = r"c:\Users\gaoga\OneDrive\デスクトップ\alcohol_tracker_backup_20260425_094628.json"
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 60)
print("JSONデータの検証開始")
print("=" * 60)

try:
    backup = BackupPayload(**data)
    print("✓ BackupPayload: OK")
    print(f"  - daily_intakes: {len(backup.daily_intakes)}件")
    print(f"  - alcohol_masters: {len(backup.alcohol_masters)}件")
except Exception as e:
    print(f"✗ BackupPayload: NG")
    print(f"  エラータイプ: {type(e).__name__}")
    print(f"  詳細: {str(e)}")
    print()
    
    # より詳細なエラー情報を表示
    if hasattr(e, 'errors'):
        print("詳細なエラー情報:")
        for error in e.errors():
            print(f"  - {error}")
