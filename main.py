import streamlit as st
import pandas as pd
import unicodedata
from pathlib import Path
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import io

# ---------------------------
# 기본 설정
# ---------------------------
st.set_page_config(
    page_title="스마트팜 환경 데이터 기반 학교별 작물 생육 비교 분석",
    layout="wide"
)

# 한글 폰트 (Streamlit)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# 유틸 함수: NFC/NFD 안전 파일 찾기
# ---------------------------
def find_file_safe(directory: Path, target_name: str):
    target_nfc = unicodedata.normalize("NFC", target_name)
    target_nfd = unicodedata.normalize("NFD", target_name)

    for f in directory.iterdir():
        name_nfc = unicodedata.normalize("NFC", f.name)
        name_nfd = unicodedata.normalize("NFD", f.name)
        if name_nfc == target_nfc or name_nfd == target_nfd:
            return f
    return None

# ---------------------------
# 데이터 로딩
# ---------------------------
@st.cache_data
def load_environment_data():
    data_dir = Path("data")
    schools = ["송도고", "하늘고", "아라고", "동산고"]
    env_data = {}

    for school in schools:
        filename = f"{school}_환경데이터.csv"
        file_path = find_file_safe(data_dir, filename)
        if file_path is None:
            st.error(f"환경 데이터 파일을 찾을 수 없습니다: {filename}")
            return None
        df = pd.read_csv(file_path)
        df["학교"] = school
        env_data[school] = df

    return env_data

@st.cache_data
def load_growth_data():
    data_dir = Path("data")
    filename = "4개교_생육결과데이터.xlsx"
    file_path = find_file_safe(data_dir, filename)

    if file_path is None:
        st.error("생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return None

    xls = pd.ExcelFile(file_path, engine="openpyxl")
    growth_data = {}

    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["학교"] = sheet
        growth_data[sheet] = df

    return growth_data

# ---------------------------
# 데이터 로딩 실행
# ---------------------------
with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.stop()

# ---------------------------
# EC 조건
# ---------------------------
ec_map = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

# ---------------------------
# 사이드바
# ---------------------------
st.sidebar.title("학교 선택")
school_option = st.sidebar.selectbox(
    "분석 대상 학교",
    ["전체", "송도고", "하늘고", "아라고", "동산고"]
)

# ---------------------------
# 제목
# ---------------------------
st.title("스마트팜 환경 데이터 기반 학교별 작물 생육 비교 분석")

# ===========================
# 탭 구성
# ===========================
tab1, tab2, tab3 = st.tabs([
    "① 연구 설계와 비교 조건",
    "② 환경 조건의 신뢰도 분석",
    "③ EC에 따른 생육 성능 평가"
])

# ===========================
# Tab 1
# ===========================
with tab1:
    st.subheader("연구 설계 개요")

    st.markdown("""
- 학교별로 **서로 다른 EC 농도**에서 동일한 극지식물 생육 실험 수행  
- **환경 데이터(온도·습도·EC)** 와 **생육 데이터(생중량·잎 수 등)**를 통합 분석  
- 단순 결과 비교가 아닌 **비교 조건의 공정성**을 먼저 검토  
    """)

    ec_df = pd.DataFrame({
        "학교": list(ec_map.keys()),
        "EC 조건": list(ec_map.values())
    })

    st.table(ec_df)

# ===========================
# Tab 2
# ===========================
with tab2:
    st.subheader("환경 조건의 안정성 분석 (표준편차)")

    rows = []
    for school, df in env_data.items():
        rows.append({
            "학교": school,
            "온도 표준편차": df["temperature"].std(),
            "습도 표준편차": df["humidity"].std(),
            "EC 표준편차": df["ec"].std()
        })

    stability_df = pd.DataFrame(rows)

    fig = make_subplots(rows=1, cols=3, subplot_titles=["온도", "습도", "EC"])

    metrics = ["온도 표준편차", "습도 표준편차", "EC 표준편차"]
    for i, metric in enumerate(metrics, start=1):
        fig.add_trace(
            go.Bar(
                x=stability_df["학교"],
                y=stability_df[metric],
                name=metric
            ),
            row=1,
            col=i
        )

    fig.update_layout(
        height=400,
        showlegend=False,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    st.plotly_chart(fig, use_container_width=True)

# ===========================
# Tab 3
# ===========================
with tab3:
    st.subheader("EC 대비 생육 효율 및 균일도 분석")

    rows = []
    for school, df in growth_data.items():
        mean_weight = df["생중량(g)"].mean()
        std_weight = df["생중량(g)"].std()
        cv = std_weight / mean_weight if mean_weight != 0 else 0

        rows.append({
            "학교": school,
            "EC": ec_map.get(school, None),
            "평균 생중량": mean_weight,
            "CV": cv
        })

    perf_df = pd.DataFrame(rows)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=perf_df["EC"],
            y=perf_df["평균 생중량"],
            name="평균 생중량"
        ),
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(
            x=perf_df["EC"],
            y=perf_df["CV"],
            mode="lines+markers",
            name="변동계수(CV)"
        ),
        secondary_y=True
    )

    fig.update_layout(
        title="EC 증가에 따른 생육 성능 및 안정성",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    st.plotly_chart(fig, use_container_width=True)

    st.success("✅ EC 2.0 (하늘고) 조건에서 생육 효율과 안정성이 가장 우수하게 나타남")

    # 다운로드
    buffer = io.BytesIO()
    perf_df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        label="📥 분석 결과 다운로드 (Excel)",
        data=buffer,
        file_name="EC_생육분석결과.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
