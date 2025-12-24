import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# =============================
# 기본 설정
# =============================
st.set_page_config(
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

# =============================
# 한글 폰트 깨짐 방지 (Streamlit)
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
# 상수 정의
# =============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SCHOOL_EC = {
    "송도고": 1.0,
    "하늘고": 2.0,  # 최적
    "아라고": 4.0,
    "동산고": 8.0
}

SCHOOL_COLOR = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728"
}

# =============================
# 유니코드 안전 파일 탐색
# =============================
def normalize(text):
    return unicodedata.normalize("NFC", text)

def find_file_by_name(directory: Path, target_name: str):
    target_nfc = normalize(target_name)
    for file in directory.iterdir():
        if normalize(file.name) == target_nfc:
            return file
    return None

# =============================
# 데이터 로딩 함수
# =============================
@st.cache_data
def load_environment_data():
    env_data = {}
    for school in SCHOOL_EC.keys():
        file = find_file_by_name(DATA_DIR, f"{school}_환경데이터.csv")
        if file is None:
            st.error(f"❌ 환경 데이터 파일을 찾을 수 없습니다: {school}")
            continue
        df = pd.read_csv(file)
        df["학교"] = school
        env_data[school] = df
    return env_data

@st.cache_data
def load_growth_data():
    file = find_file_by_name(DATA_DIR, "4개교_생육결과데이터.xlsx")
    if file is None:
        st.error("❌ 생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return {}
    xls = pd.ExcelFile(file)
    growth_data = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["학교"] = sheet
        growth_data[sheet] = df
    return growth_data

# =============================
# 데이터 로딩
# =============================
with st.spinner("📂 데이터 로딩 중..."):
    env_data = load_environment_data()
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

# =============================
# 탭 구성
# =============================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ======================================================
# Tab 1: 실험 개요
# ======================================================
with tab1:
    st.subheader("🔬 연구 배경 및 목적")
    st.markdown("""
    본 연구는 **극지식물의 생육에 영향을 미치는 EC(전기전도도) 농도**를 분석하여  
    **최적의 EC 조건을 도출**하는 것을 목표로 한다.
    """)

    # 학교별 EC 조건 표
    summary_rows = []
    total_plants = 0
    for school, ec in SCHOOL_EC.items():
        count = len(growth_data.get(school, []))
        total_plants += count
        summary_rows.append({
            "학교명": school,
            "EC 목표": ec,
            "개체수": count,
            "색상": SCHOOL_COLOR[school]
        })
    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(summary_df, use_container_width=True)

    # 주요 지표
    all_env = pd.concat(env_data.values())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 개체수", total_plants)
    col2.metric("평균 온도(℃)", round(all_env["temperature"].mean(), 2))
    col3.metric("평균 습도(%)", round(all_env["humidity"].mean(), 2))
    col4.metric("🌟 최적 EC", "2.0 (하늘고)")

# ======================================================
# Tab 2: 환경 데이터
# ======================================================
with tab2:
    st.subheader("🌡️ 학교별 환경 데이터 비교")

    avg_rows = []
    for school, df in env_data.items():
        avg_rows.append({
            "학교": school,
            "temperature": df["temperature"].mean(),
            "humidity": df["humidity"].mean(),
            "ph": df["ph"].mean(),
            "ec": df["ec"].mean(),
            "target_ec": SCHOOL_EC[school]
        })
    avg_df = pd.DataFrame(avg_rows)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["temperature"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["humidity"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ph"], row=2, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ec"], name="실측 EC", row=2, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["target_ec"], name="목표 EC", row=2, col=2)

    fig.update_layout(
        height=600,
        showlegend=True,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    # 시계열
    if school_option != "전체":
        df = env_data[school_option]
        fig_ts = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig_ts.add_scatter(x=df["time"], y=df["temperature"], row=1, col=1, name="온도")
        fig_ts.add_scatter(x=df["time"], y=df["humidity"], row=2, col=1, name="습도")
        fig_ts.add_scatter(x=df["time"], y=df["ec"], row=3, col=1, name="EC")
        fig_ts.add_hline(
            y=SCHOOL_EC[school_option],
            line_dash="dash",
            row=3, col=1
        )
        fig_ts.update_layout(
            height=700,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("📄 환경 데이터 원본"):
        combined_env = pd.concat(env_data.values())
        st.dataframe(combined_env)
        buffer = io.BytesIO()
        combined_env.to_csv(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            "CSV 다운로드",
            data=buffer,
            file_name="환경데이터_전체.csv",
            mime="text/csv"
        )

# ======================================================
# Tab 3: 생육 결과
# ======================================================
with tab3:
    st.subheader("📊 EC별 생육 결과 분석")

    growth_all = pd.concat(growth_data.values())
    growth_all["EC"] = growth_all["학교"].map(SCHOOL_EC)

    ec_weight = growth_all.groupby("EC")["생중량(g)"].mean().reset_index()
    best_ec = ec_weight.loc[ec_weight["생중량(g)"].idxmax()]

    st.metric("🥇 최적 EC 평균 생중량", f"{best_ec['EC']} / {best_ec['생중량(g)']:.2f} g")

    metrics = {
        "평균 생중량": "생중량(g)",
        "평균 잎 수": "잎 수(장)",
        "평균 지상부 길이": "지상부 길이(mm)",
        "개체수": "개체번호"
    }

    fig_metrics = make_subplots(rows=2, cols=2, subplot_titles=list(metrics.keys()))
    idx = 0
    for name, col in metrics.items():
        r, c = divmod(idx, 2)
        data = growth_all.groupby("EC")[col].mean() if col != "개체번호" else growth_all.groupby("EC")[col].count()
        fig_metrics.add_bar(x=data.index, y=data.values, row=r+1, col=c+1)
        idx += 1

    fig_metrics.update_layout(
        height=600,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_metrics, use_container_width=True)

    fig_box = px.box(
        growth_all,
        x="학교",
        y="생중량(g)",
        color="학교"
    )
    fig_box.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig_box, use_container_width=True)

    fig_scatter1 = px.scatter(growth_all, x="잎 수(장)", y="생중량(g)", color="학교")
    fig_scatter2 = px.scatter(growth_all, x="지상부 길이(mm)", y="생중량(g)", color="학교")
    st.plotly_chart(fig_scatter1, use_container_width=True)
    st.plotly_chart(fig_scatter2, use_container_width=True)

    with st.expander("📄 생육 데이터 원본"):
        st.dataframe(growth_all)
        buffer = io.BytesIO()
        growth_all.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
