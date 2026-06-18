import streamlit as st
import pandas as pd
import random
import requests

st.set_page_config(layout="wide", page_title="옵치 내전 시스템")

# 🔴 여기에 본인의 웹 앱 URL을 넣으세요!
WEB_APP_URL = "https://overwatchteammaker-5jtrdpszpquqq9bqm3jrfm.streamlit.app/"

# 전적 관련 컬럼들
STATS_COLS = ['총_경기', '총_승리', '탱커_판', '탱커_승', '메인딜러_판', '메인딜러_승', '서브딜러_판', '서브딜러_승', '힐러_판', '힐러_승']

@st.cache_data(ttl=0)
def load_data():
    try:
        response = requests.get(WEB_APP_URL)
        data = response.json()
        
        # '주_포지션' 열이 추가된 기본 뼈대
        base_columns = ['이름', '주_포지션', '탱커', '메인딜러', '서브딜러', '힐러'] + STATS_COLS
        
        if not data: 
            return pd.DataFrame(columns=base_columns)
        
        df = pd.DataFrame(data)
        
        # 없는 컬럼 자동 생성 (특히 새로 추가된 '주_포지션')
        if '주_포지션' not in df.columns:
            df.insert(1, '주_포지션', '없음')
            
        for col in STATS_COLS:
            if col not in df.columns:
                df[col] = 0
                
        # 점수 및 전적 숫자로 변환
        for col in ['탱커', '메인딜러', '서브딜러', '힐러'] + STATS_COLS:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
        return df
    except Exception as e:
        st.error("🚨 구글 시트 연결 실패! 권한이나 URL을 확인하세요.")
        return pd.DataFrame(columns=['이름', '주_포지션', '탱커', '메인딜러', '서브딜러', '힐러'] + STATS_COLS)

def save_to_db(df):
    with st.spinner("구글 시트에 동기화 중..."):
        json_data = df.to_dict('records')
        response = requests.post(WEB_APP_URL, json=json_data)
        if response.status_code == 200:
            st.session_state.player_db = df
            st.cache_data.clear()
            return True
        return False

if 'player_db' not in st.session_state:
    st.session_state.player_db = load_data()
if 'current_match' not in st.session_state:
    st.session_state.current_match = None

st.sidebar.title("메뉴")
menu = st.sidebar.radio("페이지 이동:", ["🏠 내전 팀 짜기", "🏆 명예의 전당", "👥 플레이어 DB 관리"])

# ==========================================
# 화면 A: 내전 팀 짜기 (가중치 및 타이브레이커 알고리즘 적용)
# ==========================================
if menu == "🏠 내전 팀 짜기":
    st.title("🎮 오버워치 내전 메이커 & 기록실")
    st.caption("수행평가 알고리즘 반영: 주 포지션 배정 시 실력 점수 +0.5점 가중치 부여 및 동점 시 포지션별 우선순위 판별")
    
    db_names = [name for name in st.session_state.player_db['이름'].tolist() if str(name).strip() != '']
    selected_names = st.multiselect("⚔️ 참여할 10명을 고르세요:", options=db_names, default=db_names[:10] if len(db_names) >= 10 else db_names)
    
    if len(selected_names) == 10:
        if st.button("🚀 팀 나누기 시작!", type="primary"):
            selected_players_df = st.session_state.player_db[st.session_state.player_db['이름'].isin(selected_names)]
            players = selected_players_df.to_dict('records')
            roles = ['탱커', '탱커', '메인딜러', '메인딜러', '서브딜러', '서브딜러', '힐러', '힐러', '힐러', '힐러']
            
            best_diff = float('inf')
            best_tie_breakers = (float('inf'), float('inf'), float('inf')) # (탱커차이, 딜러차이, 힐러차이)
            best_match = None
            
            with st.spinner('최적의 밸런스와 주 포지션을 계산 중입니다...'):
                for _ in range(40000): # 정밀도를 위해 시뮬레이션 횟수 증가
                    random.shuffle(players)
                    is_valid = True
                    t1_scores = {'탱커':0, '딜러':0, '힐러':0, '총점':0}
                    t2_scores = {'탱커':0, '딜러':0, '힐러':0, '총점':0}
                    match_result = {'Team1': [], 'Team2': []}
                    
                    for i in range(10):
                        p = players[i]
                        role = roles[i]
                        base_score = p.get(role, 0)
                        
                        if base_score <= 0:
                            is_valid = False
                            break
                        
                        # [알고리즘 1] 주 포지션 일치 시 가중치 +0.5 부여
                        is_main = (p.get('주_포지션', '') == role)
                        final_score = base_score + 0.5 if is_main else float(base_score)
                        
                        display_score = f"{final_score} ⭐" if is_main else f"{final_score}"
                        player_info = {'포지션': role, '이름': p['이름'], '점수': display_score, '원점수': final_score}
                        
                        role_group = '딜러' if '딜러' in role else role
                        
                        if i % 2 == 0:
                            t1_scores['총점'] += final_score
                            t1_scores[role_group] += final_score
                            match_result['Team1'].append(player_info)
                        else:
                            t2_scores['총점'] += final_score
                            t2_scores[role_group] += final_score
                            match_result['Team2'].append(player_info)
                            
                    if is_valid:
                        total_diff = abs(t1_scores['총점'] - t2_scores['총점'])
                        tank_diff = abs(t1_scores['탱커'] - t2_scores['탱커'])
                        dps_diff = abs(t1_scores['딜러'] - t2_scores['딜러'])
                        heal_diff = abs(t1_scores['힐러'] - t2_scores['힐러'])
                        
                        current_tie_breakers = (tank_diff, dps_diff, heal_diff)
                        
                        # [알고리즘 2] 점수 차이가 더 작으면 무조건 갱신
                        if total_diff < best_diff:
                            best_diff = total_diff
                            best_tie_breakers = current_tie_breakers
                            best_match = (match_result, t1_scores['총점'], t2_scores['총점'])
                            
                        # [알고리즘 3] 총점 차이가 같을 경우 (동점 발생 시 순서도 로직)
                        elif total_diff == best_diff:
                            # 1. 탱커 격차 비교
                            if tank_diff < best_tie_breakers[0]:
                                best_tie_breakers = current_tie_breakers
                                best_match = (match_result, t1_scores['총점'], t2_scores['총점'])
                            elif tank_diff == best_tie_breakers[0]:
                                # 2. 딜러 격차 비교
                                if dps_diff < best_tie_breakers[1]:
                                    best_tie_breakers = current_tie_breakers
                                    best_match = (match_result, t1_scores['총점'], t2_scores['총점'])
                                elif dps_diff == best_tie_breakers[1]:
                                    # 3. 힐러 격차 비교
                                    if heal_diff < best_tie_breakers[2]:
                                        best_tie_breakers = current_tie_breakers
                                        best_match = (match_result, t1_scores['총점'], t2_scores['총점'])

            if best_match:
                st.session_state.current_match = best_match
            else:
                st.error("🚨 포지션 폭이 겹쳐서 팀을 구성할 수 없습니다.")
                st.session_state.current_match = None

    if st.session_state.current_match:
        match, s1, s2 = st.session_state.current_match
        st.write("---")
        col1, col2 = st.columns(2)
        
        # 보기 좋게 DataFrame 가공 (원점수 숨기기)
        df1 = pd.DataFrame(match['Team1']).drop(columns=['원점수'])
        df2 = pd.DataFrame(match['Team2']).drop(columns=['원점수'])
        
        with col1:
            st.subheader(f"🔵 블루 팀 (총합: {s1}점)")
            st.dataframe(df1, hide_index=True, use_container_width=True)
        with col2:
            st.subheader(f"🔴 레드 팀 (총합: {s2}점)")
            st.dataframe(df2, hide_index=True, use_container_width=True)
            
        st.info(f"⚖️ 양 팀 점수 차이: **{abs(s1 - s2)}점** (⭐는 주 포지션 가중치 +0.5 적용됨)")
        
        st.write("### 📝 경기 결과 기록")
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        
        def record_result(winning_team):
            db = st.session_state.player_db.copy()
            for team_name in ['Team1', 'Team2']:
                is_win = (team_name == winning_team)
                for p in match[team_name]:
                    idx = db[db['이름'] == p['이름']].index[0]
                    role = p['포지션']
                    
                    db.at[idx, '총_경기'] += 1
                    if is_win: db.at[idx, '총_승리'] += 1
                    db.at[idx, f'{role}_판'] += 1
                    if is_win: db.at[idx, f'{role}_승'] += 1
                    
            if save_to_db(db):
                st.success("🎉 경기 결과가 성공적으로 반영되었습니다!")
                st.session_state.current_match = None
        
        with btn_col1:
            if st.button("🔵 블루 팀 승리!", use_container_width=True): record_result('Team1')
        with btn_col2:
            if st.button("🔴 레드 팀 승리!", use_container_width=True): record_result('Team2')
        with btn_col3:
            if st.button("❌ 기록 취소", use_container_width=True): 
                st.session_state.current_match = None
                st.rerun()

# ==========================================
# 화면 B: 명예의 전당 (이전과 동일)
# ==========================================
elif menu == "🏆 명예의 전당":
    st.title("🏆 명예의 전당 & 전적 통계")
    df = st.session_state.player_db.copy()
    df['전체승률(%)'] = (df['총_승리'] / df['총_경기'].replace(0, 1) * 100).round(1)
    
    ranked_df = df[df['총_경기'] >= 3].sort_values(by=['전체승률(%)', '총_승리'], ascending=[False, False])
    
    if len(ranked_df) >= 3:
        st.subheader("🔥 TOP 3 플레이어 (최소 3경기 이상)")
        col1, col2, col3 = st.columns(3)
        medals = ["🥇 1등", "🥈 2등", "🥉 3등"]
        for i, col in enumerate([col1, col2, col3]):
            with col:
                player = ranked_df.iloc[i]
                st.markdown(f"### {medals[i]} {player['이름']}")
                st.metric("승률", f"{player['전체승률(%)']}%", f"{player['총_승리']}승 {player['총_경기']-player['총_승리']}패")
    else:
        st.info("최소 3경기 이상 플레이한 유저가 3명 이상이어야 TOP3가 표시됩니다.")

    st.write("---")
    st.subheader("📊 전체 플레이어 세부 전적")
    display_df = df[['이름', '주_포지션', '총_경기', '총_승리', '전체승률(%)']].copy()
    for role in ['탱커', '메인딜러', '서브딜러', '힐러']:
        display_df[f'{role} 승률'] = (df[f'{role}_승'] / df[f'{role}_판'].replace(0, 1) * 100).round(1).astype(str) + "%"
        display_df[f'{role} 승률'] = display_df[f'{role} 승률'].replace("0.0%", "-")
        
    st.dataframe(display_df.sort_values(by='전체승률(%)', ascending=False), hide_index=True, use_container_width=True)

# ==========================================
# 화면 C: 플레이어 DB 관리 (주 포지션 추가)
# ==========================================
elif menu == "👥 플레이어 DB 관리":
    st.title("👥 플레이어 DB 관리")
    st.caption("주 포지션(탱커/메인딜러/서브딜러/힐러/없음)을 입력하면 배정 시 +0.5점의 가중치가 부여됩니다.")
    
    edited_db = st.data_editor(st.session_state.player_db, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    if st.button("💾 구글 시트에 변경사항 저장하기"):
        save_to_db(edited_db)
        st.success("성공적으로 구글 시트에 반영되었습니다!")
