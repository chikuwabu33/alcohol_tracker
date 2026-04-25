"""
飲酒記録アプリのフロントエンド (Streamlit)
"""
import streamlit as st
import requests
from datetime import datetime, date
from zoneinfo import ZoneInfo
import calendar
import os
from io import StringIO
import json

# APIサーバーのURLと設定ファイルパス
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
SETTINGS_FILE = "/settings/settings.json"

st.set_page_config(page_title="Alcohol Tracker", page_icon="🍺", layout="wide")

def save_settings():
    """ユーザー設定（1日の目標量）をファイルに保存する"""
    if not os.path.exists(os.path.dirname(SETTINGS_FILE)):
        os.makedirs(os.path.dirname(SETTINGS_FILE))
    with open(SETTINGS_FILE, "w") as f:
        # セッション状態から目標量を取得して保存
        json.dump({"daily_limit": st.session_state.daily_limit}, f)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f).get("daily_limit", 20)
        except:
            pass
    return 20

# アプリの状態を管理する変数の初期化
if "daily_limit" not in st.session_state:
    st.session_state.daily_limit = load_settings()
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None

# タイムゾーン考慮した今日の日付
today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
# サイドバーでの年月選択
year = st.sidebar.selectbox("年", range(today.year - 1, today.year + 2), index=1)
month = st.sidebar.selectbox("月", range(1, 13), index=today.month - 1)

def get_color_style(alc, limit):
    """アルコール摂取量に応じてカレンダーのセルの色を決定する"""
    if alc == 0:
        return "white"
    if alc <= limit:
        return "rgba(40, 167, 69, 0.3)"
    ratio = min((alc - limit) / limit, 1.0)
    r = 255
    g = int(230 * (1 - ratio))
    return f"rgba({r}, {g}, 0, 0.6)"

@st.cache_data
def fetch_monthly_data(y, m):
    """バックエンドから1ヶ月分の飲酒データを取得してキャッシュする"""
    try:
        res = requests.get(f"{BACKEND_URL}/intakes", params={"year": y, "month": m})
        if res.status_code == 200:
            return {str(i["date"]): i for i in res.json()}
    except:
        st.error("バックエンドに接続できません")
    return {}

@st.cache_data
def fetch_alcohol_masters():
    """バックエンドからお酒のマスタデータを取得してキャッシュする"""
    try:
        res = requests.get(f"{BACKEND_URL}/alcohols")
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return []

def save_alcohol_master(name, percent, default_ml):
    """新しいお酒の種類を登録する"""
    try:
        res = requests.post(f"{BACKEND_URL}/alcohols", json={"name": name, "percent": percent, "default_ml": default_ml})
        return res.status_code == 200
    except:
        return False

def delete_alcohol_master(alc_id):
    """お酒の種類を削除する"""
    try:
        res = requests.delete(f"{BACKEND_URL}/alcohols/{alc_id}")
        return res.status_code == 200
    except:
        return False

# ⭐ HTMLクリック用
def calendar_button(day, alc, color, date_str, is_today=False):
    """
    カレンダーの1日分を表示するボタン(HTML形式)。
    クリック時にクエリパラメータを使用して日付を選択状態にする。
    """
    label = f"<b>{day}</b><br><small>{int(alc)}g</small>"
    border_style = "2px solid #FF0000" if is_today else "1px solid #aaa"
    return f"""
    <form action="" method="get">
        <button name="selected" value="{date_str}" 
        style="
            width:100%;
            height:70px;
            border:{border_style};
            border-radius:10px;
            background:{color};
            color:#333;
            font-weight:normal;
            cursor:pointer;
        ">
            {label}
        </button>
    </form>
    """

monthly_data = fetch_monthly_data(year, month)
total_month_alc = sum(d["total_pure_alcohol"] for d in monthly_data.values())
# 統計情報の計算 (今月の平均値算出ロジック)

if year < today.year or (year == today.year and month < today.month):
    # 過去の月：月間合計をその月の日数で割る
    num_days_to_count = calendar.monthrange(year, month)[1]
    avg_month_alc = total_month_alc / num_days_to_count if num_days_to_count > 0 else 0
elif year == today.year and month == today.month:
    # 今月：前日までの純アルコール量合計を、経過日数（昨日まで）で割る
    total_until_yesterday = sum(d["total_pure_alcohol"] for dt_str, d in monthly_data.items() if date.fromisoformat(dt_str).day < today.day)
    num_days_to_count = today.day - 1
    avg_month_alc = total_until_yesterday / num_days_to_count if num_days_to_count > 0 else 0
else:
    # 未来の月
    avg_month_alc = 0

# タイトルと今月の総純アルコール量を横並びに表示
col_title, col_total, col_avg = st.columns([2, 1, 1])
with col_title:
    st.title("🍺 Alcohol Tracker")
with col_total:
    st.metric("今月の総純アルコール量", f"{int(total_month_alc)} g")
with col_avg:
    st.metric("1日あたりの平均", f"{int(avg_month_alc)} g")

# AI医師のアドバイスセクション
with st.expander("🩺 AI医師によるマンスリー分析", expanded=False):
    if st.button("アドバイスを生成する", use_container_width=True):
        with st.spinner("AI医師がデータを分析しています..."):
            try:
                params = {
                    "year": year,
                    "month": month,
                    "daily_limit": st.session_state.daily_limit
                }
                res = requests.get(f"{BACKEND_URL}/ai-advice", params=params)
                if res.status_code == 200:
                    st.markdown(res.json()["advice"])
                else:
                    error_detail = res.json().get("detail", "不明なエラー")
                    st.error(f"アドバイスの取得に失敗しました: {error_detail}")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

st.info("**純アルコール量計算式:** 量(ml) × (度数/100) × 0.8")

# 登録済みマスタの読み込みと辞書化
alcohol_masters = fetch_alcohol_masters()
master_options = {m["name"]: m for m in alcohol_masters}
master_names = ["-- 選択してください --"] + list(master_options.keys())

# カレンダーの描画
st.header(f"{year}年{month}月のカレンダー")
calendar.setfirstweekday(calendar.SUNDAY)
cal = calendar.monthcalendar(year, month)

# 曜日見出し
days = ["日", "月", "火", "水", "木", "金", "土"]
cols = st.columns(7)
for i, d in enumerate(days):
    cols[i].write(f"**{d}**")

# ⭐ URLパラメータでクリック検知
params = st.query_params
if "selected" in params:
    st.session_state.selected_date = date.fromisoformat(params["selected"])
else:
    st.session_state.selected_date = None

# 週ごとの行ループ
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].write("")
        else:
            curr_date = date(year, month, day)
            date_str = str(curr_date)
            is_today = (curr_date == today)

            data = monthly_data.get(date_str)
            alc = data["total_pure_alcohol"] if data else 0.0

            limit = st.session_state.daily_limit
            color = get_color_style(alc, limit)

            html = calendar_button(day, alc, color, date_str, is_today=is_today)
            cols[i].markdown(html, unsafe_allow_html=True)

# ===== 以下は元コードほぼそのまま =====
# 日付選択時の入力フォーム表示

if st.session_state.selected_date:
    selected_date = st.session_state.selected_date
    st.divider()
    st.subheader(f"📝 {selected_date} の記録")

    # 既に記録があれば初期値として読み込む
    existing_data = monthly_data.get(str(selected_date), {}).get("items", [])

    items = []
    for i in range(5):
        c1, c2 = st.columns([3, 1])

        default_name = "-- 選択してください --"

        # 既存データの反映ロジック
        if i < len(existing_data):
            for name, m in master_options.items():
                if m["percent"] == existing_data[i]["percent"]:
                    default_name = name
                    break

        # お酒の選択
        selected_name = c1.selectbox(
            f"お酒 {i+1}",
            master_names,
            index=master_names.index(default_name) if default_name in master_names else 0,
            key=f"name_{i}"
        )

        input_ml = 0
        # 選択されたお酒のデフォルト量を設定
        if selected_name != "-- 選択してください --":
            m = master_options[selected_name]
            # 保存データがあれば優先、なければマスタの登録量を初期値にする
            val = int(existing_data[i]["ml"]) if i < len(existing_data) else int(m["default_ml"])
            input_ml = c2.number_input("量(ml)", min_value=0, step=1, value=int(val), key=f"ml_input_{i}")

        if selected_name != "-- 選択してください --" and input_ml > 0:
            m = master_options[selected_name]
            items.append({"percent": int(m["percent"]), "ml": int(input_ml)})

    c_save, c_cancel = st.columns(2)

    if c_save.button("記録を保存", type="primary", use_container_width=True):
        try:
            res = requests.post(f"{BACKEND_URL}/intakes", json={"date": str(selected_date), "items": items})
            if res.status_code == 200:
                # 成功したらキャッシュを消して再読み込み
                fetch_monthly_data.clear() # キャッシュをクリア
                st.session_state.selected_date = None
                st.query_params.clear()
                st.rerun()
            else:
                st.error("保存に失敗しました")
        except Exception as e:
            st.error(f"エラー: {e}")

    if c_cancel.button("保存せずに閉じる", use_container_width=True):
        st.session_state.selected_date = None
        st.query_params.clear()
        st.rerun()

# サイドバーの設定項目
st.sidebar.divider()
st.sidebar.header("🎯 目標設定")
st.sidebar.info(""" 背景色がオレンジの日は目標の純アルコール量を上回った日です。 """)

st.sidebar.number_input(
    "1日の純アルコール限度 (g)",
    min_value=1,
    step=1,
    key="daily_limit",
    on_change=save_settings
)

# 飲める量の逆算シミュレーター
with st.sidebar.expander("🔍 飲める量計算機"):
    st.write("設定した目標値に達する量を計算します。")
    calc_percent = st.number_input("アルコール度数 (%)", min_value=0.1, max_value=100.0, value=5.0, step=0.5, key="calc_pct")
    limit_g = st.session_state.daily_limit
    calc_ml = limit_g / (calc_percent / 100 * 0.8)
    st.metric(f"目標 {limit_g}g までの目安", f"{int(calc_ml)} ml")

st.sidebar.divider()
def handle_master_registration():
    """マスタ登録ボタンのコールバック処理"""
    name = st.session_state.get("master_name_input")
    pct = st.session_state.get("master_pct_input")
    def_ml = st.session_state.get("master_def_ml_input")
    
    if name:
        full_name = f"{name}({pct}%)"
        if save_alcohol_master(full_name, pct, def_ml):
            # コールバック内であれば、ウィジェットに紐づく値を安全にリセット可能
            st.session_state.master_name_input = ""
            fetch_alcohol_masters.clear()
            st.query_params.clear()
            st.session_state.master_reg_error = None
        else:
            st.session_state.master_reg_error = "保存に失敗しました"
    else:
        st.session_state.master_reg_error = "名前を入力してください"

# お酒の種類を管理するセクション
with st.sidebar.expander("📝 お酒のマスタ設定"):
    st.text_input("お酒の名前", key="master_name_input")
    st.number_input("度数 (%)", value=5, step=1, key="master_pct_input")
    st.number_input("デフォルトの量 (ml)", value=350, step=1, key="master_def_ml_input")
    st.button("登録", use_container_width=True, on_click=handle_master_registration)
    
    # エラーメッセージがある場合は表示し、その後クリアする
    if st.session_state.get("master_reg_error"):
        st.error(st.session_state.master_reg_error)
        st.session_state.master_reg_error = None

    if alcohol_masters:
        st.write("登録済みリスト:")
        for m in alcohol_masters:
            col1, col2 = st.columns([4, 1])
            col1.write(m['name'])
            if col2.button("🗑️", key=f"del_{m['id']}"):
                if delete_alcohol_master(m["id"]):
                    fetch_alcohol_masters.clear() # キャッシュをクリア
                    st.query_params.clear()
                    st.rerun()

# ===== データ管理（バックアップ・復元）セクション =====
st.sidebar.divider()
st.sidebar.header("💾 データ管理")

# バックアップ機能
if st.sidebar.button("データベースをバックアップ", use_container_width=True):
    try:
        with st.spinner("バックアップデータを取得中..."):
            response = requests.get(f"{BACKEND_URL}/backup")
            if response.status_code == 200:
                backup_data = response.json()
                # JSONデータを整形して文字列化
                json_string = json.dumps(backup_data, indent=2, ensure_ascii=False)
                
                # ダウンロードボタンを表示
                st.sidebar.download_button(
                    label="バックアップファイルをダウンロード",
                    data=json_string,
                    file_name=f"alcohol_tracker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    key="download_backup_button"
                )
                st.sidebar.success("バックアップデータが生成されました。ダウンロードボタンをクリックしてください。")
            else:
                st.sidebar.error(f"バックアップデータの取得に失敗しました: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        st.sidebar.error("バックエンドに接続できません。バックエンドサービスが実行されていることを確認してください。")
    except Exception as e:
        st.sidebar.error(f"バックアップ中にエラーが発生しました: {e}")

st.sidebar.markdown("---") # 区切り線

# 復元機能
st.sidebar.subheader("データ復元")
st.sidebar.warning("⚠️ **注意:** 復元を実行すると、**現在のデータベースのデータは全て上書きされます**。")

uploaded_file = st.sidebar.file_uploader(
    "バックアップファイルをアップロード",
    type=["json"],
    key="restore_file_uploader",
    help="以前にダウンロードしたJSON形式のバックアップファイルを選択してください。"
)

if uploaded_file is not None:
    # アップロードされたファイルを読み込む
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    try:
        backup_data_to_restore = json.load(stringio)
        
        if st.sidebar.button("アップロードしたデータで復元を実行", type="primary", use_container_width=True):
            with st.spinner("データベースを復元中..."):
                response = requests.post(f"{BACKEND_URL}/restore", json=backup_data_to_restore)
                if response.status_code == 200:
                    st.sidebar.success("データベースが正常に復元されました。画面を再読み込みします。")
                    fetch_monthly_data.clear() # キャッシュをクリアして最新データを取得
                    fetch_alcohol_masters.clear() # キャッシュをクリアして最新データを取得
                    st.rerun() # 画面を再描画
                else:
                    st.sidebar.error(f"データベースの復元に失敗しました: {response.status_code} - {response.text}")
    except json.JSONDecodeError:
        st.sidebar.error("無効なJSONファイルです。正しいバックアップファイルを選択してください。")
    except requests.exceptions.ConnectionError:
        st.sidebar.error("バックエンドに接続できません。バックエンドサービスが実行されていることを確認してください。")
    except Exception as e:
        st.sidebar.error(f"復元中にエラーが発生しました: {e}")