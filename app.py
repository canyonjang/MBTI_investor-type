import streamlit as st
from supabase import create_client, Client
import pandas as pd
from scipy import stats
import plotly.express as px
import time

# 1. Supabase 연결 설정 (streamlit secrets 사용)
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# 페이지 기본 설정
st.set_page_config(page_title="투자성향 분석 실험", layout="wide")

# 2. 메인 화면 및 역할 분기
st.sidebar.title("로그인")
role = st.sidebar.radio("역할을 선택하세요", ("학생", "교수"))

def main():
    if role == "교수":
        password = st.sidebar.text_input("비밀번호", type="password")
        if password == "3383":
            professor_view()
        elif password:
            st.sidebar.error("비밀번호가 틀렸습니다.")
            
    elif role == "학생":
        nickname = st.sidebar.text_input("사용할 별명을 입력하세요 (예: 튼튼한통장)")
        if nickname:
            student_view(nickname)

# 3. 교수용 화면
def professor_view():
    st.title("👨‍🏫 실험 통제 및 결과 패널")
    
    # 상단 컨트롤 버튼
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("실험 시작 (학생 화면 열기)"):
            supabase.table("experiment_control").update({"is_started": True}).eq("id", 1).execute()
            st.success("학생들의 화면에 설문이 열렸습니다!")
    with col2:
        if st.button("실험 종료 (학생 화면 닫기)"):
            supabase.table("experiment_control").update({"is_started": False}).eq("id", 1).execute()
            st.warning("실험이 종료되었습니다.")
    with col3:
        if st.button("새로고침"):
            st.rerun()

    st.divider()
    
    # 탭으로 기능 분리
    tab1, tab2, tab3 = st.tabs(["참여자 현황", "우리 반 포지션 맵", "통계 결과 확인"])
    
    # 데이터 불러오기
    res = supabase.table("mbti_investment_survey").select("*").execute()
    df = pd.DataFrame(res.data)
    
    # 결측치 제거된 데이터프레임 준비 (설문 완료자만)
    if not df.empty:
        df_clean = df.dropna(subset=['cognitive_score', 'behavioral_score']).copy()
    else:
        df_clean = pd.DataFrame()

    # [탭 1] 참여자 현황 및 인지-행동 불일치 지수
    with tab1:
        st.subheader("👥 참여 학생 및 불일치 지수")
        if df.empty:
            st.info("아직 접속한 학생이 없습니다.")
        else:
            completed_count = len(df_clean)
            st.write(f"**총 접속자:** {len(df)} 명 / **설문 완료자:** {completed_count} 명")
            
            for index, row in df.iterrows():
                name = row['nickname']
                cog = row['cognitive_score']
                beh = row['behavioral_score']
                
                if pd.notna(cog) and pd.notna(beh):
                    # 불일치 지수 계산 (단순 차이 또는 절대값)
                    gap = cog - beh
                    gap_abs = abs(gap)
                    
                    if gap > 1:
                        status = "머리가 앞서는 타입 (인지 > 행동)"
                        color = "blue"
                    elif gap < -1:
                        status = "행동이 앞서는 타입 (행동 > 인지)"
                        color = "red"
                    else:
                        status = "일치형 (안정적)"
                        color = "green"
                        
                    st.markdown(f"- **{name}** | 인지: {cog:.1f} | 행동: {beh:.2f} | "
                                f"불일치 지수(차이): **{gap_abs:.2f}** $\\rightarrow$ :{color}[{status}]")
                else:
                    st.markdown(f"- **{name}** | ⏳ 설문 진행 중...")

    # [탭 2] 우리 반 포지션 맵
    with tab2:
        st.subheader("📍 우리 반 포지션 맵")
        if df_clean.empty:
            st.warning("설문을 완료한 학생이 없어 맵을 그릴 수 없습니다.")
        else:
            avg_cog = df_clean['cognitive_score'].mean()
            avg_beh = df_clean['behavioral_score'].mean()
            
            # 산점도 그리기 (Plotly 사용)
            fig = px.scatter(
                df_clean, 
                x='cognitive_score', 
                y='behavioral_score', 
                text='nickname',
                title="학생별 인지적-행동적 투자성향 분포",
                labels={'cognitive_score': '인지적 투자성향 (점수)', 'behavioral_score': '행동적 투자성향 (평균 점수)'},
                range_x=[0.5, 5.5], 
                range_y=[0.5, 5.5]
            )
            
            # 점 위쪽에 별명 표시
            fig.update_traces(textposition='top center', marker=dict(size=10, color='indigo'))
            
            # 평균선 그리기
            fig.add_vline(x=avg_cog, line_dash="dash", line_color="red", 
                          annotation_text=f"인지 평균 ({avg_cog:.2f})", annotation_position="top right")
            fig.add_hline(y=avg_beh, line_dash="dash", line_color="blue", 
                          annotation_text=f"행동 평균 ({avg_beh:.2f})", annotation_position="bottom right")
            
            st.plotly_chart(fig, use_container_width=True)

    # [탭 3] 실험 결과 확인 (표4, 표6, 상관관계)
    with tab3:
        st.subheader("📊 실험 결과 분석 (논문 표 4, 표 6 비교)")
        if len(df_clean) < 2:
            st.warning("통계 분석을 위해 2명 이상의 완료된 데이터가 필요합니다.")
        else:
            # 피어슨 상관계수
            corr, p_val = stats.pearsonr(df_clean['cognitive_score'], df_clean['behavioral_score'])
            st.info(f"**인지적 성향과 행동적 성향의 상관계수 (Pearson's r):** {corr:.3f} (p-value: {p_val:.3f})")
            st.divider()

            # T-test 헬퍼 함수
            def display_ttest(dim_col, val_col, group1, group2, title):
                g1_data = df_clean[df_clean[dim_col] == group1][val_col]
                g2_data = df_clean[df_clean[dim_col] == group2][val_col]
                
                if len(g1_data) > 0 and len(g2_data) > 0:
                    # t-test 수행 (분산이 다를 수 있음을 가정: equal_var=False)
                    t_stat, p = stats.ttest_ind(g1_data, g2_data, equal_var=False)
                    mean1, mean2 = g1_data.mean(), g2_data.mean()
                    
                    sig = "🚨 **유의미한 차이 있음**" if p < 0.05 else "차이 없음"
                    color = "green" if p < 0.05 else "gray"
                    
                    st.markdown(f"**{title} ({group1} vs {group2})**")
                    st.markdown(f"- **{group1} 평균:** {mean1:.2f} (n={len(g1_data)}) / **{group2} 평균:** {mean2:.2f} (n={len(g2_data)})")
                    st.markdown(f"- t값: {t_stat:.2f}, p-value: {p:.3f} $\\rightarrow$ :{color}[{sig}]")
                else:
                    st.markdown(f"**{title} ({group1} vs {group2})**")
                    st.write("- 두 그룹을 비교하기 위한 데이터가 충분하지 않습니다.")
                st.write("---")

            colA, colB = st.columns(2)
            with colA:
                st.markdown("### 인지적 특성에 따른 투자성향")
                display_ttest('mbti_e_i', 'cognitive_score', 'E', 'I', '외향(E) vs 내향(I)')
                display_ttest('mbti_s_n', 'cognitive_score', 'S', 'N', '감각(S) vs 직관(N)')
                display_ttest('mbti_t_f', 'cognitive_score', 'T', 'F', '사고(T) vs 감정(F)')
                display_ttest('mbti_j_p', 'cognitive_score', 'J', 'P', '판단(J) vs 인식(P)')
            with colB:
                st.markdown("### 행동적 특성에 따른 투자성향")
                display_ttest('mbti_e_i', 'behavioral_score', 'E', 'I', '외향(E) vs 내향(I)')
                display_ttest('mbti_s_n', 'behavioral_score', 'S', 'N', '감각(S) vs 직관(N)')
                display_ttest('mbti_t_f', 'behavioral_score', 'T', 'F', '사고(T) vs 감정(F)')
                display_ttest('mbti_j_p', 'behavioral_score', 'J', 'P', '판단(J) vs 인식(P)')

# 4. 학생용 화면
def student_view(nickname):
    st.title(f"반갑습니다, {nickname}님! 👋")
    
    # 학생 닉네임 DB 등록
    try:
        supabase.table("mbti_investment_survey").insert({"nickname": nickname}).execute()
    except Exception:
        pass # 이미 존재하는 닉네임일 경우 무시
    
    # 실험 통제 상태 확인
    state = supabase.table("experiment_control").select("is_started").eq("id", 1).execute()
    
    if not state.data[0]['is_started']:
        st.info("⏳ 교수님이 실험을 시작할 때까지 잠시만 대기해 주세요...")
        time.sleep(3)
        st.rerun()
    else:
        st.success("실험이 시작되었습니다! 아래 질문에 답해 주세요.")
        
        # 이미 제출했는지 확인
        user_data = supabase.table("mbti_investment_survey").select("cognitive_score").eq("nickname", nickname).execute()
        if user_data.data and user_data.data[0].get("cognitive_score") is not None:
            st.info("✅ 이미 설문을 제출하셨습니다. 교수님의 화면에서 전체 결과를 확인해 보세요!")
            return
        
        with st.form("survey_form"):
            st.subheader("1. 나의 MBTI")
            col1, col2, col3, col4 = st.columns(4)
            e_i = col1.selectbox("에너지 방향", ["E", "I"])
            s_n = col2.selectbox("정보 수집", ["S", "N"])
            t_f = col3.selectbox("의사 결정", ["T", "F"])
            j_p = col4.selectbox("생활 양식", ["J", "P"])
            
            st.subheader("2. 인지적 투자성향")
            cog_choice = st.radio("가장 본인과 가까운 성향을 선택하세요:", [
                "1점: 어떤 위험도 회피하며 예금 등 안전한 성장 추구",
                "2점: 안정적으로 투자하되 10~20%의 위험성 고려",
                "3점: 안정적으로 투자하되 30% 이상의 위험성 고려",
                "4점: 투자원금의 10~20% 손실을 감수하며 고수익 추구",
                "5점: 투자원금의 20% 이상 손실을 감수하며 고수익 추구"
            ])
            cog_score = int(cog_choice[0])
            
            st.subheader("3. 행동적 투자성향")
            st.write("각 문항에 대해 1점(전혀 그렇지 않다)부터 5점(매우 그렇다) 사이로 응답해 주세요.")
            b1 = st.slider("주식, 채권 등에 직접 투자한다.", 1, 5, 3)
            b2 = st.slider("단기적으로 투자한다.", 1, 5, 3)
            b3 = st.slider("좋은 투자기회가 있다면 빚을 내서라도 투자한다.", 1, 5, 3)
            b4 = st.slider("한 가지 상품에 집중적으로 투자한다.", 1, 5, 3)
            b5 = st.slider("원금 손실 위험이 있더라도 투자 수익성이 우선이다.", 1, 5, 3)
            
            submitted = st.form_submit_button("결과 제출하기")
            
            if submitted:
                beh_score = (b1 + b2 + b3 + b4 + b5) / 5.0
                
                supabase.table("mbti_investment_survey").update({
                    "mbti_e_i": e_i, "mbti_s_n": s_n, "mbti_t_f": t_f, "mbti_j_p": j_p,
                    "cognitive_score": cog_score, "behavioral_score": beh_score
                }).eq("nickname", nickname).execute()
                
                st.success("응답이 성공적으로 제출되었습니다. 수고하셨습니다!")
                st.rerun()

if __name__ == "__main__":
    main()
