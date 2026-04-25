from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import calendar
import os
import json
import logging
import hashlib
from google import genai
from typing import List
from datetime import date
from functools import lru_cache
from pydantic import BaseModel
from .database import engine, get_db, Base
from .models import DailyIntake, AlcoholMaster

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini APIの設定
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# スキーマ変更を反映させるため、一時的にテーブルを削除して再作成する
#Base.metadata.drop_all(bind=engine) 
Base.metadata.create_all(bind=engine)

# FastAPIアプリケーションのインスタンス化
app = FastAPI()

class AlcoholItem(BaseModel):
    """1回に飲んだお酒の情報を保持するスキーマ"""
    percent: int  # アルコール度数 (%)
    ml: int       # 飲んだ量 (ml)

class AlcoholMasterBase(BaseModel):
    """お酒のマスタデータの基本構造"""
    name: str        # お酒の名前（例: ビール、ハイボール）
    percent: int     # デフォルトの度数 (%)
    default_ml: int  # デフォルトの量 (ml)

class AlcoholMasterResponse(AlcoholMasterBase):
    """APIレスポンス用のお酒マスタスキーマ"""
    id: int  # データベース上のID
    class Config:
        from_attributes = True

class IntakeCreate(BaseModel):
    """飲酒記録作成時のリクエストスキーマ"""
    date: date               # 記録対象の日付
    items: List[AlcoholItem] # 飲んだお酒のリスト

class BackupPayload(BaseModel):
    """データベースのバックアップデータを保持するスキーマ"""
    daily_intakes: List[IntakeCreate]
    alcohol_masters: List[AlcoholMasterBase]

@app.get("/")
def read_root():
    """ルートパスへのアクセスに対するウェルカムメッセージ"""
    return {"message": "Alcohol Tracker API is running", "docs": "/docs"}

@app.get("/health")
def health_check():
    """サーバーの稼働確認用エンドポイント"""
    return {"status": "ok"}

@app.get("/alcohols", response_model=List[AlcoholMasterResponse])
def get_alcohol_masters(db: Session = Depends(get_db)):
    """登録済みのお酒マスタ一覧を取得する"""
    return db.query(AlcoholMaster).all()

@app.post("/alcohols", response_model=AlcoholMasterResponse)
def save_alcohol_master(data: AlcoholMasterBase, db: Session = Depends(get_db)):
    """お酒のマスタを新規登録または更新する"""
    db_item = db.query(AlcoholMaster).filter(AlcoholMaster.name == data.name).first()
    if db_item:
        # 既存の場合は情報を更新
        db_item.percent = data.percent
        db_item.default_ml = data.default_ml
    else:
        # 新規登録
        db_item = AlcoholMaster(**data.model_dump())
        db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/alcohols/{alc_id}")
def delete_alcohol_master(alc_id: int, db: Session = Depends(get_db)):
    """指定されたIDのお酒マスタを削除する"""
    db_item = db.query(AlcoholMaster).filter(AlcoholMaster.id == alc_id).first()
    if db_item:
        db.delete(db_item)
        db.commit()
    return {"status": "deleted"}

@app.get("/intakes")
def get_intakes(year: int, month: int, db: Session = Depends(get_db)):
    """指定された年月（1ヶ月分）の飲酒記録を取得する"""
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    results = db.query(DailyIntake).filter(
        DailyIntake.date >= start_date,
        DailyIntake.date <= end_date
    ).all()
    return results

@app.post("/intakes")
def save_intake(data: IntakeCreate, db: Session = Depends(get_db)):
    """特定の日付の飲酒記録を保存する"""
    if len(data.items) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 items allowed")
    
    # 純アルコール量計算: ml * (percent/100) * 0.8
    total_pure = sum([ 
        item.ml * (item.percent / 100) * 0.8
        for item in data.items
    ])

    db_item = db.query(DailyIntake).filter(DailyIntake.date == data.date).first()
    items_json = [item.model_dump() for item in data.items]

    if db_item:
        # 既存の記録がある場合は更新
        db_item.items = items_json
        db_item.total_pure_alcohol = int(total_pure + 0.5)
    else:
        # 新規の記録を作成
        db_item = DailyIntake(
            date=data.date,
            items=items_json,
            total_pure_alcohol=int(total_pure + 0.5)
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/intake/{target_date}")
def get_day_intake(target_date: date, db: Session = Depends(get_db)):
    """特定の日付の飲酒詳細データを取得する"""
    return db.query(DailyIntake).filter(DailyIntake.date == target_date).first()

@app.get("/backup")
def backup_data(db: Session = Depends(get_db)):
    """データベースの全データをJSON形式でバックアップする"""
    all_daily_intakes = db.query(DailyIntake).all()
    all_alcohol_masters = db.query(AlcoholMaster).all()

    # DBオブジェクトをPydanticモデルに変換し、IDを含まない形式にする
    # これにより、復元時に新しいIDが自動生成される
    daily_intakes_data = []
    for intake in all_daily_intakes:
        try:
            # DailyIntake.itemsはJSON型なので、Pythonのリスト/辞書として取得される
            # IntakeCreateのitemsはList[AlcoholItem]なので、辞書のリストをそのまま渡す
            daily_intakes_data.append({
                "date": intake.date.isoformat(),
                "items": intake.items
            })
        except Exception as e:
            print(f"Warning: Failed to backup intake {intake.date}: {str(e)}")
            continue

    alcohol_masters_data = [
        AlcoholMasterBase(name=master.name, percent=master.percent, default_ml=master.default_ml).model_dump()
        for master in all_alcohol_masters
    ]

    return {
        "daily_intakes": daily_intakes_data,
        "alcohol_masters": alcohol_masters_data
    }

@app.post("/restore")
def restore_data(backup_data: BackupPayload, db: Session = Depends(get_db)):
    """JSONデータからデータベースを復元する。既存データは上書きされる。"""
    try:
        logger.info("Starting database restore process...")

        # 1. 既存データを確実に削除し、一旦コミットしてデータベースを物理的に空にする
        logger.info("Checking existing data...")
        existing_masters = db.query(AlcoholMaster).count()
        existing_intakes = db.query(DailyIntake).count()
        logger.info(f"Found {existing_masters} alcohol masters and {existing_intakes} daily intakes")

        logger.info("Deleting existing data...")
        try:
            # より強力な削除方法を試す
            # まずTRUNCATEを試す
            db.execute(text("TRUNCATE TABLE daily_intakes RESTART IDENTITY CASCADE"))
            db.execute(text("TRUNCATE TABLE alcohol_master RESTART IDENTITY CASCADE"))
            db.commit()
            logger.info("Existing data cleared successfully with TRUNCATE")
        except Exception as e:
            logger.warning(f"TRUNCATE failed: {str(e)}, trying alternative methods...")
            try:
                # TRUNCATEが失敗した場合、個別に削除
                for intake in db.query(DailyIntake).all():
                    db.delete(intake)
                for master in db.query(AlcoholMaster).all():
                    db.delete(master)
                db.commit()
                logger.info("Existing data cleared successfully with individual DELETE")
            except Exception as e2:
                logger.error(f"Individual DELETE also failed: {str(e2)}")
                # 最後の手段として、SQLAlchemyのバルク削除を試す
                try:
                    db.query(DailyIntake).delete()
                    db.query(AlcoholMaster).delete()
                    db.commit()
                    logger.info("Existing data cleared successfully with query DELETE")
                except Exception as e3:
                    logger.error(f"All deletion methods failed: {str(e3)}")
                    raise HTTPException(status_code=500, detail=f"Failed to clear existing data: {str(e3)}")

        # 削除後の確認
        remaining_masters = db.query(AlcoholMaster).count()
        remaining_intakes = db.query(DailyIntake).count()
        logger.info(f"After deletion: {remaining_masters} alcohol masters and {remaining_intakes} daily intakes remain")

        if remaining_masters > 0 or remaining_intakes > 0:
            logger.error(f"Failed to clear all data. Remaining: {remaining_masters} masters, {remaining_intakes} intakes")
            raise HTTPException(status_code=500, detail=f"Failed to clear existing data completely. {remaining_masters} masters and {remaining_intakes} intakes remain.")

        # セッション内の古いキャッシュをクリア
        db.expire_all()

        # お酒マスタを挿入（入力データの重複排除を行い、一意制約エラーを防止する）
        unique_masters = {m.name: m for m in backup_data.alcohol_masters}
        logger.info(f"Inserting {len(unique_masters)} alcohol masters...")
        for master_data in unique_masters.values():
            try:
                # 既存のデータを確認してから挿入
                existing = db.query(AlcoholMaster).filter(AlcoholMaster.name == master_data.name).first()
                if existing:
                    logger.warning(f"Master '{master_data.name}' already exists, updating...")
                    existing.percent = master_data.percent
                    existing.default_ml = master_data.default_ml
                else:
                    # IDは自動生成されるため、Pydanticモデルから直接作成
                    new_master = AlcoholMaster(**master_data.model_dump())
                    db.add(new_master)
                    logger.debug(f"Added master: {master_data.name}")
            except Exception as e:
                logger.error(f"Error inserting alcohol master '{master_data.name}': {str(e)}")
                raise HTTPException(status_code=400, detail=f"Error inserting alcohol master '{master_data.name}': {str(e)}")

        # 飲酒記録を挿入
        logger.info(f"Inserting {len(backup_data.daily_intakes)} daily intakes...")
        for idx, intake_data in enumerate(backup_data.daily_intakes, 1):
            try:
                # 既存のデータを確認してから挿入
                existing = db.query(DailyIntake).filter(DailyIntake.date == intake_data.date).first()
                if existing:
                    logger.warning(f"Intake for date '{intake_data.date}' already exists, updating...")
                    # 純アルコール量を再計算（計算ロジックの変更に対応するため）
                    total_pure = sum([
                        item.ml * (item.percent / 100) * 0.8
                        for item in intake_data.items
                    ])

                    # itemsの変換（辞書またはオブジェクトの両方に対応）
                    items_list = []
                    for item in intake_data.items:
                        if isinstance(item, dict):
                            items_list.append(item)
                        else:
                            items_list.append(item.model_dump())

                    existing.items = items_list
                    existing.total_pure_alcohol = int(total_pure + 0.5)
                else:
                    # 純アルコール量を再計算（計算ロジックの変更に対応するため）
                    total_pure = sum([
                        item.ml * (item.percent / 100) * 0.8
                        for item in intake_data.items
                    ])

                    # itemsの変換（辞書またはオブジェクトの両方に対応）
                    items_list = []
                    for item in intake_data.items:
                        if isinstance(item, dict):
                            items_list.append(item)
                        else:
                            items_list.append(item.model_dump())

                    new_intake = DailyIntake(
                        date=intake_data.date,
                        items=items_list,
                        total_pure_alcohol=int(total_pure + 0.5)
                    )
                    db.add(new_intake)
                    logger.debug(f"Added intake: {intake_data.date} with {len(items_list)} items")
            except Exception as e:
                logger.error(f"Error inserting alcohol intake for '{intake_data.date}': {str(e)}")
                raise HTTPException(status_code=400, detail=f"Error inserting intake: {str(e)}")

        db.commit()
        logger.info("Database restore completed successfully.")
        return {"status": "restored", "message": "Database restored successfully."}
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Unexpected error during database restore: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to restore database: {str(e)}")

def generate_fallback_advice(year: int, month: int, daily_limit: int, results: list) -> str:
    """AIが利用できない場合に、内部的なルールベースで代替アドバイスを生成する"""
    month_days = calendar.monthrange(year, month)[1]
    total_alc = sum(r.total_pure_alcohol for r in results)
    avg_alc = total_alc / month_days
    drink_days = len(results)
    no_drink_days = sum(1 for r in results if r.total_pure_alcohol == 0)
    above_limit_days = sum(1 for r in results if r.total_pure_alcohol > daily_limit)
    high_risk_days = sum(1 for r in results if r.total_pure_alcohol >= daily_limit * 1.5)

    advice_lines = [
        f"対象年月: {year}年{month}月の飲酒傾向をまとめます。",
        f"この期間の総純アルコール量は {total_alc}g、1日あたりの平均は {avg_alc:.1f}g です。",
        f"{no_drink_days}日間は休肝日がありました。",
        f"目標量を上回った日は {above_limit_days}日、特に高リスクだった日は {high_risk_days}日です。",
        "",
    ]

    if no_drink_days == 0:
        advice_lines.append(":red[休肝日が1日もないため、1週間に1〜2日の休肝日を設けることを強くおすすめします。]")
    elif no_drink_days < max(1, month_days // 10):
        advice_lines.append("休肝日はありますが、もう少し増やすと体と肝臓の回復につながります。")
    else:
        advice_lines.append("休肝日が一定数あるのは良い傾向です。継続してください。")

    if above_limit_days == 0:
        advice_lines.append("目標量を超える日はありませんが、平均摂取量は目標に近いため油断は禁物です。")
    else:
        advice_lines.append(
            f"目標量を超えた日は {above_limit_days} 日あります。特に、:red[{high_risk_days} 日は 目標の 1.5 倍以上の摂取でした。]"
        )
        advice_lines.append("過剰摂取日は、翌日に水分補給や休肝日を意識すると良いです。")

    if avg_alc > daily_limit:
        advice_lines.append("平均摂取量が目標を上回っています。まずは1日あたり10〜20g程度の節酒を目標にしてください。")
    else:
        advice_lines.append("平均摂取量は目標を下回っていますが、引き続き無理のない節酒を心がけましょう。")

    advice_lines.append("具体的には、飲む量を少しずつ減らし、夜遅い時間帯の飲酒を控えることが効果的です。")
    advice_lines.append("また、ストレスや習慣による飲酒には注意し、代替としてお茶や炭酸水を取り入れてください。")

    return "\n\n".join(advice_lines)


@lru_cache(maxsize=64)
def _get_ai_advice_from_api(prompt: str):
    """
    AI APIを実際に呼び出す内部関数。
    lru_cacheにより、全く同じプロンプト（データ内容）ならAPIを呼ばずに結果を返す。
    """
    if not os.getenv("GOOGLE_API_KEY"):
        return None

    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt
        )
        return response.text
    except Exception as e:
        raise e


@app.get("/ai-advice")
def get_ai_advice(year: int, month: int, daily_limit: int, db: Session = Depends(get_db)):
    """生成AIを使用して、1ヶ月の飲酒データに基づく医師のアドバイスを取得する"""
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    
    results = db.query(DailyIntake).filter(
        DailyIntake.date >= start_date,
        DailyIntake.date <= end_date
    ).order_by(DailyIntake.date).all()

    if not results:
        return {"advice": "この月のデータが登録されていないため、アドバイスを生成できません。"}

    # データのサマリー作成
    data_summary = "\n".join([f"- {r.date}: {r.total_pure_alcohol}g" for r in results])
    total_alc = sum(r.total_pure_alcohol for r in results)
    avg_alc = total_alc / last_day

    prompt = f"""
    あなたは親しみやすく、かつ専門的な知見を持つ医師です。
    以下の1ヶ月間の飲酒データに基づき、患者へのアドバイスを日本語で提供してください。

    【基本情報】
    - 対象年月: {year}年{month}月
    - 1日の目標摂取量: {daily_limit}g
    - 1ヶ月の総純アルコール量: {total_alc}g
    - 1日あたりの平均摂取量: {avg_alc:.1f}g

    【日別の摂取データ (日付: 純アルコール量g)】
    {data_summary if data_summary else "データなし"}

    アドバイスには以下の項目を含めてください：
    1. 現在の飲酒傾向の分析（休肝日の頻度や、過剰摂取のパターンなど）
    2. 健康面でのリスク評価
    3. 具体的で無理のない減酒・節酒のアクションプラン

    【重要】特に注意が必要な箇所や改善すべき重要なポイントは、Streamlitのカラー表記である `:red[重要表現]` という形式を使用して、赤文字で強調してください。
    """.strip()

    try:
        ai_text = _get_ai_advice_from_api(prompt)
        if ai_text:
            return {"advice": ai_text}
        else:
            return {"advice": generate_fallback_advice(year, month, daily_limit, results)}
    except Exception as e:
        error_str = str(e)
        logger.error(f"AI Advice Error: {error_str}")
        
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            msg = (
                ":red[【原因: AIの利用回数制限】]\n\n"
                "Google APIの無料枠の制限（1分間あたりのリクエスト数、または1日の合計上限）に達しました。\n\n"
                "**解決策:** 1分ほど待ってから再度ボタンを押すか、上限がリセットされる明日以降に再度お試しください。"
            )
        elif "API_KEY" in error_str or "403" in error_str:
            msg = (
                ":red[【原因: APIキーの漏洩または無効化】]\n\n"
                "お使いのGoogle APIキーが漏洩したと報告されたか、無効化されています。\n\n"
                "**解決策:** Google AI Studio (または Google Cloud Console) で**新しいAPIキーを生成し**、"
                "`.env` ファイルの `GOOGLE_API_KEY` を更新してください。"
                "古いキーは使用できません。"
            )
        elif "404" in error_str or "NOT_FOUND" in error_str:
            # 利用可能なモデルをログに出力して調査を容易にする
            available_models = []
            try:
                available_models = [m.name for m in client.models.list()]
            except:
                pass
            logger.error(f"Available models for this key: {available_models}")
            
            msg = (
                ":red[【原因: モデルが見つかりません (404)】]\n\n"
                f"指定されたモデル名が認識されませんでした。APIキーが Google AI Studio のものか確認してください。\n\n"
                f"**解決策:** `gemini-1.5-flash-latest` や `gemini-1.5-pro` への変更を試してください。また、ライブラリ更新 (`pip install -U google-genai`) も有効です。"
            )
        else:
            msg = (
                f":red[【原因: 通信またはシステムエラー】]\n\n"
                f"AIとの通信中に問題が発生しました。内容: `{error_str[:100]}...`\n\n"
                "**解決策:** しばらく時間を置いてから再度お試しください。"
            )
        
        return {"advice": msg + "\n\n---\n### 代替の節酒アドバイス\n\n" + generate_fallback_advice(year, month, daily_limit, results)}
