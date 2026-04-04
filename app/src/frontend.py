import streamlit as st
import requests
from datetime import date
import calendar
import os
import json

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
SETTINGS_FILE = "settings.json"

st.set_page_config(page_title="Alcohol Tracker", page_icon="🍺", layout="wide")

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"daily_limit": st.session_state.daily_limit}, f)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f).get("daily_limit", 20.0)
        except:
            pass
    return 20.0

if "daily_limit" not in st.session_state:
    st.session_state.daily_limit = load_settings()
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None

today = date.today()
year = st.sidebar.selectbox("年", range(today.year - 1, today.year + 2), index=1)
month = st.sidebar.selectbox("月", range(1, 13), index=today.month - 1)

def get_color_style(alc, limit):
    if alc == 0:
        return "white"
    if alc <= limit:
        return "rgba(40, 167, 69, 0.3)"
    ratio = min((alc - limit) / limit, 1.0)
    r = 255
    g = int(230 * (1 - ratio))
    return f"rgba({r}, {g}, 0, 0.6)"

def fetch_monthly_data(y, m):
    try:
        res = requests.get(f"{BACKEND_URL}/intakes", params={"year": y, "month": m})
        if res.status_code == 200:
            return {str(i["date"]): i for i in res.json()}
    except:
        st.error("バックエンドに接続できません")
    return {}

def fetch_alcohol_masters():
    try:
        res = requests.get(f"{BACKEND_URL}/alcohols")
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return []

def save_alcohol_master(name, percent, ml):
    try:
        requests.post(f"{BACKEND_URL}/alcohols", json={"name": name, "percent": percent, "ml": ml})
        return True
    except:
        return False

def delete_alcohol_master(alc_id):
    try:
        requests.delete(f"{BACKEND_URL}/alcohols/{alc_id}")
        return True
    except:
        return False

# ⭐ HTMLクリック用
def calendar_button(day, alc, color, date_str, is_today=False):
    label = f"<b>{day}</b><br><small>{alc:.1f}g</small>"
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
num_days = calendar.monthrange(year, month)[1]
avg_month_alc = total_month_alc / num_days

# タイトルと今月の総純アルコール量を横並びに表示
col_title, col_total, col_avg = st.columns([2, 1, 1])
with col_title:
    st.title("🍺 Alcohol Tracker")
with col_total:
    st.metric("今月の総純アルコール量", f"{total_month_alc:.1f} g")
with col_avg:
    st.metric("1日あたりの平均", f"{avg_month_alc:.1f} g")

st.info("**純アルコール量計算式:** 量(ml) × (度数/100) × 0.8")

alcohol_masters = fetch_alcohol_masters()
master_options = {m["name"]: m for m in alcohol_masters}
master_names = ["-- 選択してください --"] + list(master_options.keys())

st.header(f"{year}年{month}月のカレンダー")
cal = calendar.monthcalendar(year, month)

days = ["月", "火", "水", "木", "金", "土", "日"]
cols = st.columns(7)
for i, d in enumerate(days):
    cols[i].write(f"**{d}**")

# ⭐ URLパラメータでクリック検知
params = st.query_params
if "selected" in params:
    st.session_state.selected_date = date.fromisoformat(params["selected"])

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

            limit = float(st.session_state.daily_limit)
            color = get_color_style(alc, limit)

            html = calendar_button(day, alc, color, date_str, is_today=is_today)
            cols[i].markdown(html, unsafe_allow_html=True)

# ===== 以下は元コードほぼそのまま =====

if st.session_state.selected_date:
    selected_date = st.session_state.selected_date
    st.divider()
    st.subheader(f"📝 {selected_date} の記録")

    existing_data = monthly_data.get(str(selected_date), {}).get("items", [])

    items = []
    for i in range(5):
        c1, c2 = st.columns([3, 1])

        default_name = "-- 選択してください --"
        default_count = 0

        if i < len(existing_data):
            default_count = int(existing_data[i]["count"])
            for name, m in master_options.items():
                if m["percent"] == existing_data[i]["percent"] and m["ml"] == existing_data[i]["ml"]:
                    default_name = name
                    break

        selected_name = c1.selectbox(
            f"お酒 {i+1}",
            master_names,
            index=master_names.index(default_name) if default_name in master_names else 0,
            key=f"name_{i}"
        )

        cnt = c2.number_input("個数", min_value=0, step=1, value=default_count, key=f"cnt_{i}")

        if selected_name != "-- 選択してください --" and cnt > 0:
            m = master_options[selected_name]
            items.append({"percent": m["percent"], "ml": m["ml"], "count": cnt})

    c_save, c_cancel = st.columns(2)

    if c_save.button("記録を保存", type="primary", use_container_width=True):
        try:
            res = requests.post(f"{BACKEND_URL}/intakes", json={"date": str(selected_date), "items": items})
            if res.status_code == 200:
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

st.sidebar.divider()
st.sidebar.header("🎯 目標設定")
st.sidebar.info(""" 背景色がオレンジの日は目標の純アルコール量を上回った日です。 """)

st.sidebar.number_input(
    "1日の純アルコール限度 (g)",
    min_value=1.0,
    step=1.0,
    key="daily_limit",
    on_change=save_settings
)

st.sidebar.divider()
with st.sidebar.expander("📝 お酒のマスタ設定"):
    with st.form("add_alcohol"):
        new_name = st.text_input("お酒の名前")
        new_pct = st.number_input("度数 (%)", min_value=0.0, max_value=100.0, value=5.0)
        new_ml = st.number_input("量 (ml)", min_value=0.0, step=10.0, value=350.0)
        if st.form_submit_button("登録/更新"):
            if new_name:
                # 名称に度数と量を自動的に付与 (例: ビール(5%)(350ml))
                p_str = int(new_pct) if new_pct.is_integer() else new_pct
                m_str = int(new_ml) if new_ml.is_integer() else new_ml
                full_name = f"{new_name}({p_str}%,{m_str}ml)"
                
                if save_alcohol_master(full_name, new_pct, new_ml):
                    st.rerun()
            else:
                st.error("名前を入力してください")

    if alcohol_masters:
        st.write("登録済みリスト:")
        for m in alcohol_masters:
            col1, col2 = st.columns([4, 1])
            col1.write(m['name'])
            if col2.button("🗑️", key=f"del_{m['id']}"):
                if delete_alcohol_master(m["id"]):
                    st.rerun()