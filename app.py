import streamlit as st
import pandas as pd
import random

st.set_page_config(layout="wide", page_title="옵치 내전 밸런서")

# --- 1. 초기 DB 세팅 (세션에 저장하여 앱 구동 중 유지) ---
if 'player_db' not in st.session_state:
    # 기본 샘플 데이터 (1~10점 스케일)
    st.session_state.player_db = pd.DataFrame({
        '이름': [f"플레이어{i}" for i in range(1, 13)], # 테스트용 12명
        '탱커': [random.randint(3, 10) for _ in range(12)],
        '메인딜러': [random.randint(3, 10) for _ in range(12)],
        '서브딜러': [random.randint(3, 10) for _ in range(12)],
        '힐러': [random.randint(3, 10) for _ in range(12)],
    })

# --- 2. 사이드바 메뉴 (화면 분리) ---
st.sidebar.title("메뉴")
menu = st.sidebar.radio("이동할 페이지를 선택하세요:", ["🏠 내전 팀 짜기", "👥 플레이어 DB 관리"])

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** 추후 DB 연동 작업 시, '플레이어 DB 관리' 화면의 데이터를 구글 시트로 연결하도록 업데이트하면 관리가 더욱 편해집니다.")


# ==========================================
# 화면 A: 플레이어 DB 관리 페이지
# ==========================================
if menu == "👥 플레이어 DB 관리":
    st.title("👥 플레이어 DB 관리")
    st.write("플레이어들의 포지션별 실력 점수(1~10점)를 미리 입력해 두는 곳입니다.")
    st.write("표 맨 아래 빈칸을 클릭해 **새로운 플레이어를 추가**하거나, 왼쪽 체크박스를 선택해 **삭제**할 수 있습니다. (플레이 불가능한 포지션은 0점)")
    
    # num_rows="dynamic" 옵션으로 자유로운 행 추가/삭제 지원
    edited_db = st.data_editor(
        st.session_state.player_db, 
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True
    )
    # 수정한 데이터를 세션에 덮어씌워 팀 짜기 화면에서도 반영되게 함
    st.session_state.player_db = edited_db


# ==========================================
# 화면 B: 내전 팀 짜기 페이지 (메인)
# ==========================================
elif menu == "🏠 내전 팀 짜기":
    st.title("🎮 오버워치 5:5 내전 팀 밸런서")
    st.write("DB에 등록된 인원 중 **오늘 참여할 10명**을 고르면 밸런스에 맞춰 팀을 나눕니다.")
    
    db_names = st.session_state.player_db['이름'].tolist()
    
    # 멀티셀렉트로 10명 고르기 (기본값으로 위에서부터 10명 자동 선택)
    selected_names = st.multiselect(
        "⚔️ 오늘 내전에 참여할 10명을 고르세요:", 
        options=db_names,
        default=db_names[:10] if len(db_names) >= 10 else db_names
    )
    
    if len(selected_names) != 10:
        st.warning(f"현재 {len(selected_names)}명 선택되었습니다. 정확히 10명을 선택해야 합니다.")
    else:
        if st.button("🚀 팀 나누기 시작!", type="primary"):
            # 선택된 10명의 데이터만 DB에서 추출
            selected_players_df = st.session_state.player_db[st.session_state.player_db['이름'].isin(selected_names)]
            players = selected_players_df.to_dict('records')
            
            # 포지션 슬롯 (각 팀: 탱1, 메딜1, 서딜1, 힐2) -> 번갈아가며 배정
            roles = ['탱커', '탱커', '메인딜러', '메인딜러', '서브딜러', '서브딜러', '힐러', '힐러', '힐러', '힐러']
            
            best_diff = float('inf')
            best_match = None
            
            with st.spinner('최적의 황금 밸런스를 계산 중입니다...'):
                # 스케일이 1~10으로 작아졌으므로 시도 횟수를 늘려 정밀도 상승
                for _ in range(30000): 
                    random.shuffle(players)
                    is_valid = True
                    t1_score, t2_score = 0, 0
                    match_result = {'Team1': [], 'Team2': []}
                    
                    for i in range(10):
                        p, role = players[i], roles[i]
                        score = p[role]
                        
                        # 0점이거나 비어있으면 배정 불가
                        if pd.isna(score) or score <= 0:
                            is_valid = False
                            break
                        
                        if i % 2 == 0:
                            t1_score += score
                            match_result['Team1'].append({'포지션': role, '이름': p['이름'], '점수': int(score)})
                        else:
                            t2_score += score
                            match_result['Team2'].append({'포지션': role, '이름': p['이름'], '점수': int(score)})
                            
                    if is_valid:
                        diff = abs(t1_score - t2_score)
                        if diff < best_diff:
                            best_diff = diff
                            best_match = (match_result, t1_score, t2_score)
                            
                            # 1~10 스케일이므로 양 팀 점수 차이가 1점 이하면 즉시 종료
                            if diff <= 1: 
                                break

            if best_match:
                match, s1, s2 = best_match
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(f"🔵 블루 팀 (합계: {s1}점)")
                    st.dataframe(pd.DataFrame(match['Team1']), hide_index=True, use_container_width=True)
                    
                with col2:
                    st.subheader(f"🔴 레드 팀 (합계: {s2}점)")
                    st.dataframe(pd.DataFrame(match['Team2']), hide_index=True, use_container_width=True)
                    
                st.info(f"⚖️ 양 팀 점수 차이: **{abs(s1 - s2)}점**")
            else:
                st.error("🚨 10명의 포지션 폭이 겹쳐서 팀을 구성할 수 없습니다. DB에서 포지션별 점수를 확인해 주세요.")
