import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# =============================
# 페이지 설정
# =============================
st.set_page_config(
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

# =============================
# 한글 폰트 깨짐 방지
# =============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =============================
# 경로 설정
# =============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# =============================
# EC 조건
# =============================
SCHOOL_EC = {
    "송도고": 1.0,
    "하늘고": 2.0,   # 최적
    "아라고": 4.0,
    "동산고": 8.0
}

# =============================
# 유니코드 안전 함수
# =============================
def normalize(text):
    return unicodedata.normalize("NFC", text)

def find_file(directory: Path, target_name: str):
    target = normalize(target_name)
    for file in directory.iterdir():
        if normalize(file.name) == target:
            return file
    return None

# =============================
# 데이터 로딩
# =============================
@st.cache_data
def load_env_data():
    data = {}
    for school in SCHOOL_EC:
        file = find_file(DATA_DIR, f"{school}_환경데이터.csv.csv")
        if file is None:
            st.error(f"❌ 환경 데이터 없음: {school}")
            continue
        df = pd.read_csv(file)
        df["학교"] = school
        data[school] = df
    return data

@st.cache_data
def load_growth_data():
    file = find_file(DATA_DIR, "4개교_생육결과데이터.xlsx.xlsx")
    if file is None:
        st.error("❌ 생육 결과 파일 없음")
        return {}

    xls = pd.ExcelFile(file)
    data = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["학교"] = sheet
        data[sheet] = df
    return data

# =============================
# 데이터 로딩 실행
# =============================
with st.spinner("📂 데이터 불러오는 중..."):
    env_data = load_env_data()
    growth_data = load_growth_data()

if not env_data or not growth_data:
    st.stop()

# =============================
# 사이드바
# =============================
st.sidebar.title("🏫 학교 선택")
school_option = st.sidebar.selectbox(
    "학교 선택",
    ["전체"] + list(SCHOOL_EC.keys())
)

# =============================
# 제목
# =============================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ======================================================
# Tab 1
# ======================================================
with tab1:
    st.subheader("🔬 연구 목적")
    st.write("EC 농도 차이에 따른 극지식물 생육 반응을 분석하여 최적 EC를 도출한다.")

    rows = []
    total = 0
    for s, ec in SCHOOL_EC.items():
        cnt = len(growth_data.get(s, []))
        total += cnt
        rows.append({"학교": s, "EC": ec, "개체수": cnt})

    df_info = pd.DataFrame(rows)
    st.dataframe(df_info, use_container_width=True)

    all_env = pd.concat(env_data.values())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total)
    c2.metric("평균 온도", f"{all_env['temperature'].mean():.2f} ℃")
    c3.metric("평균 습도", f"{all_env['humidity'].mean():.2f} %")
    c4.metric("🌟 최적 EC", "2.0 (하늘고)")

# ======================================================
# Tab 2
# ======================================================
with tab2:
    st.subheader("🌡️ 환경 데이터 비교")

    avg = []
    for s, df in env_data.items():
        avg.append({
            "학교": s,
            "온도": df["temperature"].mean(),
            "습도": df["humidity"].mean(),
            "pH": df["ph"].mean(),
            "EC": df["ec"].mean(),
            "목표 EC": SCHOOL_EC[s]
        })
    avg_df = pd.DataFrame(avg)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["온도"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["습도"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["pH"], row=2, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["EC"], name="실측 EC", row=2, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["목표 EC"], name="목표 EC", row=2, col=2)

    fig.update_layout(
        height=600,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    if school_option != "전체":
        df = env_data[school_option]
        fig_ts = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig_ts.add_scatter(x=df["time"], y=df["temperature"], row=1, col=1, name="온도")
        fig_ts.add_scatter(x=df["time"], y=df["humidity"], row=2, col=1, name="습도")
        fig_ts.add_scatter(x=df["time"], y=df["ec"], row=3, col=1, name="EC")
        fig_ts.add_hline(y=SCHOOL_EC[school_option], row=3, col=1, line_dash="dash")
        fig_ts.update_layout(height=700)
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("📄 환경 데이터 원본"):
        env_all = pd.concat(env_data.values())
        st.dataframe(env_all)
        buf = io.BytesIO()
        env_all.to_csv(buf, index=False)
        buf.seek(0)
        st.download_button("CSV 다운로드", buf, "환경데이터_전체.csv", "text/csv")

# ======================================================
# Tab 3
# ======================================================
with tab3:
    st.subheader("📊 생육 결과 분석")

    growth_all = pd.concat(growth_data.values())
    growth_all["EC"] = growth_all["학교"].map(SCHOOL_EC)

    ec_mean = growth_all.groupby("EC")["생중량(g)"].mean()
    best = ec_mean.idxmax()

    st.metric("🥇 최적 EC 평균 생중량", f"EC {best} → {ec_mean[best]:.2f} g")

    fig_box = px.box(growth_all, x="학교", y="생중량(g)", color="학교")
    fig_box.update_layout(font=dict(family="Malgun Gothic"))
    st.plotly_chart(fig_box, use_container_width=True)

    fig_sc1 = px.scatter(growth_all, x="잎 수(장)", y="생중량(g)", color="학교")
    fig_sc2 = px.scatter(growth_all, x="지상부 길이(mm)", y="생중량(g)", color="학교")
    st.plotly_chart(fig_sc1, use_container_width=True)
    st.plotly_chart(fig_sc2, use_container_width=True)

    with st.expander("📄 생육 데이터 원본"):
        st.dataframe(growth_all)
        buf = io.BytesIO()
        growth_all.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        st.download_button(
            "XLSX 다운로드",
            buf,
            "생육결과_전체.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
