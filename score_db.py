import sqlite3
import pandas as pd
import streamlit as st

# --- 기본 설정 및 스타일 정의 ---
st.set_page_config(
    page_title="스마트 성적 관리 시스템",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "scoreDB.db"

# --- 데이터베이스 관련 비즈니스 로직 함수 ---
def get_db_connection():
    """데이터베이스 연결 객체를 반환합니다."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # 컬럼명으로 데이터 접근이 가능하게 설정
    return conn

def init_database():
    """데이터베이스와 테이블을 생성하고, 데이터가 비어있을 경우 10개의 더미 데이터를 적재합니다."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 테이블 생성 (학번, 이름, 국어, 영어, 컴퓨터 점수)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS score (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                korean INTEGER NOT NULL CHECK(korean BETWEEN 0 AND 100),
                english INTEGER NOT NULL CHECK(english BETWEEN 0 AND 100),
                computer INTEGER NOT NULL CHECK(computer BETWEEN 0 AND 100)
            )
        """)
        conn.commit()
        
        # 데이터 존재 여부 확인
        cursor.execute("SELECT COUNT(*) FROM score")
        if cursor.fetchone()[0] == 0:
            # 임의의 학생 레코드 10개 삽입
            dummy_records = [
                ("김철수", 90, 85, 95),
                ("이영희", 78, 92, 80),
                ("박민수", 85, 70, 90),
                ("최수연", 95, 98, 100),
                ("정우성", 60, 65, 70),
                ("강호동", 50, 55, 45),
                ("유재석", 88, 90, 92),
                ("한지민", 92, 88, 94),
                ("이광수", 70, 60, 65),
                ("송지효", 82, 85, 88)
            ]
            cursor.executemany(
                "INSERT INTO score (name, korean, english, computer) VALUES (?, ?, ?, ?)",
                dummy_records
            )
            conn.commit()

def fetch_score_data(search_query="", grade_filter="전체"):
    """
    데이터베이스에서 학생 성적 정보를 조회해 옵니다.
    실시간으로 총점, 평균, 석차, 학점을 계산하여 Pandas DataFrame으로 반환합니다.
    """
    with get_db_connection() as conn:
        # 전체 학생 데이터를 기준으로 석차를 산출하기 위해 먼저 전체를 불러옵니다.
        query = "SELECT * FROM score WHERE 1=1"
        params = []
        
        if search_query:
            query += " AND name LIKE ?"
            params.append(f"%{search_query}%")
            
        df = pd.read_sql_query(query, conn, params=params)
        
    if df.empty:
        return df

    # 총점 및 평균 계산 수행
    df['총점'] = df['korean'] + df['english'] + df['computer']
    df['평균'] = (df['총점'] / 3.0).round(2)
    
    # [석차 계산]: 평균 점수를 기준으로 내림차순(점수가 높을수록 1등) 순위를 구합니다.
    # 동점자가 있을 경우 공동 순위(min 방식)로 처리합니다 (예: 공동 2등이 2명이면 다음 등수는 4등).
    df['석차'] = df['평균'].rank(ascending=False, method='min').astype(int)
    
    # 학점 산출 로직 정의
    def calculate_grade(avg):
        if avg >= 90: return 'A'
        elif avg >= 80: return 'B'
        elif avg >= 70: return 'C'
        elif avg >= 60: return 'D'
        else: return 'F'
        
    df['학점'] = df['평균'].apply(calculate_grade)
    
    # 컬럼 이름 가독성 개선 (영문 -> 한글 표기)
    df = df.rename(columns={
        'id': '학번',
        'name': '이름',
        'korean': '국어',
        'english': '영어',
        'computer': '컴퓨터'
    })
    
    # 컬럼 배치 순서 재조정 (학번, 이름 바로 옆에 석차를 배치하여 가시성을 확보합니다)
    column_order = ['학번', '이름', '석차', '국어', '영어', '컴퓨터', '총점', '평균', '학점']
    df = df[column_order]
    
    # 학점 필터 처리 (필터링되더라도 개별 학생의 전체 석차는 그대로 보존됩니다)
    if grade_filter != "전체":
        df = df[df['학점'] == grade_filter]
        
    # 기본 정렬 기준을 석차 순(오름차순)으로 지정하여 1등부터 보기 쉽게 나열합니다.
    df = df.sort_values(by='석차')
        
    return df

def add_student_record(name, kor, eng, comp):
    """새로운 학생 데이터를 데이터베이스에 안전하게 등록합니다."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO score (name, korean, english, computer) VALUES (?, ?, ?, ?)",
                (name, kor, eng, comp)
            )
            conn.commit()
            return True
    except Exception as e:
        st.error(f"데이터 저장 중 에러가 발생했습니다: {e}")
        return False

def delete_student_record(student_id):
    """지정된 학번의 학생 데이터를 데이터베이스에서 삭제합니다."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM score WHERE id = ?", (student_id,))
            conn.commit()
            return True
    except Exception as e:
        st.error(f"데이터 삭제 중 에러가 발생했습니다: {e}")
        return False

def reset_entire_database():
    """데이터베이스를 강제로 완전 초기화합니다."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS score")
        conn.commit()
    init_database()

# --- 데이터베이스 초기 실행 보장 ---
init_database()


# --- UI 및 레이아웃 구성 ---

# 타이틀 바 및 헤더
st.markdown("""
    <div style="background-color:#1e3d59;padding:20px;border-radius:10px;margin-bottom:25px;text-align:center;">
        <h1 style="color:white;margin:0;">🎓 Smart Score Management System</h1>
        <p style="color:#ffc13b;margin:5px 0 0 0;font-size:1.1rem;">SQLite3 & Streamlit 기반 실시간 성적 및 학점 조회 시스템</p>
    </div>
""", unsafe_allow_html=True)

# 메인 레이아웃 분할 (좌측 사이드바: 제어 및 추가 / 우측 메인: 조회 및 분석)
with st.sidebar:
    st.header("🛠️ 시스템 관리 및 제어")
    
    # 신규 학생 등록 섹션 (Expandable)
    with st.expander("➕ 신규 학생 성적 등록", expanded=False):
        with st.form("add_student_form", clear_on_submit=True):
            new_name = st.text_input("학생 이름", placeholder="이름을 입력하세요")
            new_kor = st.number_input("국어 점수", min_value=0, max_value=100, value=80, step=5)
            new_eng = st.number_input("영어 점수", min_value=0, max_value=100, value=80, step=5)
            new_comp = st.number_input("컴퓨터 점수", min_value=0, max_value=100, value=80, step=5)
            
            submit_btn = st.form_submit_button("학생 추가하기")
            if submit_btn:
                if not new_name.strip():
                    st.warning("학생 이름을 입력해 주세요.")
                else:
                    success = add_student_record(new_name.strip(), new_kor, new_eng, new_comp)
                    if success:
                        st.success(f"'{new_name}' 학생이 성공적으로 등록되었습니다.")
                        st.rerun()

    # 특정 학생 삭제 섹션
    with st.expander("❌ 학생 정보 삭제", expanded=False):
        delete_id = st.number_input("삭제할 학번(ID)", min_value=1, step=1)
        if st.button("학생 정보 삭제", type="primary", use_container_width=True):
            if delete_student_record(delete_id):
                st.success(f"학번 {delete_id}번 학생 데이터가 정상적으로 삭제되었습니다.")
                st.rerun()

    st.markdown("---")
    
    # DB 초기화 버튼
    st.subheader("⚠️ 데이터 팩토리 리셋")
    st.caption("기존 데이터를 모두 삭제하고 초기 더미 데이터 10개 상태로 되돌립니다.")
    if st.button("데이터베이스 초기화 수행", use_container_width=True, type="secondary"):
        reset_entire_database()
        st.success("데이터베이스가 깔끔하게 초기화되었습니다!")
        st.rerun()


# --- 우측 메인 대시보드 화면 ---

# 1단계: 검색 필터 UI 구성
col_search, col_filter = st.columns([3, 1])
with col_search:
    search_keyword = st.text_input("🔍 학생 이름으로 실시간 검색", placeholder="이름을 입력하여 실시간 필터링하세요...")
with col_filter:
    grade_filter_val = st.selectbox("🎯 학점 필터", ["전체", "A", "B", "C", "D", "F"])

# 2단계: 데이터 가공 및 가져오기
df_score = fetch_score_data(search_query=search_keyword, grade_filter=grade_filter_val)

if df_score.empty:
    st.info("검색 조건에 부합하는 학생 정보가 데이터베이스에 존재하지 않습니다.")
else:
    # 3단계: 상단 메트릭 요약 정보 제공
    st.subheader("📊 학급 성적 종합 브리핑")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    
    class_avg = df_score['평균'].mean()
    highest_row = df_score.loc[df_score['평균'].idxmax()]
    total_students = len(df_score)
    
    # 학점 비율 중 A학점 비율 계산
    a_grade_count = len(df_score[df_score['학점'] == 'A'])
    a_ratio = (a_grade_count / total_students) * 100 if total_students > 0 else 0
    
    m_col1.metric("총 등록 학생 수", f"{total_students} 명")
    m_col2.metric("학급 전체 평균", f"{class_avg:.2f} 점")
    m_col3.metric("최우수 학생 (평균)", f"{highest_row['이름']} ({highest_row['평균']:.1f}점)")
    m_col4.metric("A학점 취득률", f"{a_ratio:.1f} %")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 4단계: 성적 테이블 시각화
    st.subheader("📋 성적 상세 현황판")
    
    st.dataframe(
        df_score,
        use_container_width=True,
        hide_index=True,
        column_config={
            "학번": st.column_config.NumberColumn(format="%d"),
            "이름": st.column_config.TextColumn(),
            "석차": st.column_config.NumberColumn(format="%d등"),  # 석차 포맷팅 추가
            "국어": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "영어": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "컴퓨터": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "총점": st.column_config.NumberColumn(format="%d점"),
            "평균": st.column_config.NumberColumn(format="%.2f점"),
            "학점": st.column_config.TextColumn()
        }
    )
    
    # 5단계: 분석 차트 시각화
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📈 학업 분석 및 통계 차트")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown("**과목별 평균 분포 점수**")
        subject_averages = df_score[['국어', '영어', '컴퓨터']].mean()
        st.bar_chart(subject_averages, color="#1e3d59")
        
    with chart_col2:
        st.markdown("**학점 등급별 분포 현황**")
        # 모든 학점 등급이 차트에 표현될 수 있도록 인덱스를 정돈합니다.
        all_grades = ['A', 'B', 'C', 'D', 'F']
        grade_counts = df_score['학점'].value_counts().reindex(all_grades, fill_value=0)
        st.bar_chart(grade_counts, color="#ffc13b")

# --- Footer 영역 ---
st.markdown("""
    <hr style="border:0.5px solid #eaeaea;">
    <p style="text-align:center; color:gray; font-size:0.8rem;">
        Smart Score Manager v2.0 • SQLite3 Persistent DB Active • Designed by Senior Programmer (20 Years Exp)
    </p>
""", unsafe_allow_html=True)