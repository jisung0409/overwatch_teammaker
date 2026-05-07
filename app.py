import streamlit as st
import pandas as pd
import random
import requests

st.set_page_config(layout="wide", page_title="옵치 내전 시스템")

# 🔴 여기에 본인의 웹 앱 URL을 넣으세요!
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyTYisY1s5QEP8UqGV01_zj1SeI_yqCjlz1HgNwzXnIAsAoJE1tsC0oAag27vA02QwnQA/exec"

# 전적 관련 추가할 기본 컬럼들
STATS_COLS = ['총_경기', '총_승리', '탱커_판', '탱커_승', '메인딜러_판', '메인딜러_승', '서브딜러_판', '서브딜러_승', '힐러_판', '힐러_승']

@st.cache_data(ttl=0)
def load_data():
    try:
        response = requests.get(WEB_APP_URL)
        data = response.json()
        if not data: 
            df = pd.DataFrame(columns=['이름', '탱커', '메인딜러', '서브딜러', '힐러'] + STATS_COLS)
            return df
        
        df = pd.DataFrame(data)
        
        # 기존 DB에 전적 컬럼이 없으면 0으로 채워서 생성
        for col in STATS_COLS:
            if col not in df.columns:
                df[col] = 0
                
        # 빈칸(NaN)이나 문자열로 된 숫자를 정수형으로 변환
        for col in ['탱커', '메인딜러', '서브딜러', '힐러'] + STATS_COLS:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
        return df
    except Exception as e:
        st.error("🚨 구글 시트 연결 실패!")
        return pd.DataFrame(columns=['이름', '탱커', '메인딜러', '서브딜러', '힐러'] + STATS_COLS)

def save_to_db(df):
    with st.spinner("구글 시트에 동기화 중..."):
        json_data = df.to_dict('records')
        response = requests.post(WEB_APP_URL, json=json_data)
        if response.status_code == 200:
            st.session_state.player_db = df
            st.cache_data.clear()
            return True
        return False

# 세션 상태 초기화
if 'player_db' not in st.session_state:
    st.session_state.player_db = load_data()
if 'current_match' not in st.session_state:
    st.session_state.current_match = None

# 사이드바 메뉴
st.sidebar.title("메뉴")
menu = st.sidebar.radio("페이지 이동:", ["🏠 내전 팀 짜기", "🏆 명예의 전당", "👥 플레이어 DB 관리"])


# ==========================================
# 화면 A: 내전 팀 짜기 (승패 기록 기능 추가)
# ==========================================
if menu == "🏠 내전 팀 짜기":
    st.title("🎮 오버워치 내전 메이커 & 기록실")
    
    db_names = [name for name in st.session_state.player_db['이름'].tolist() if str(name).strip() != '']
    selected_names = st.multiselect("⚔️ 참여할 10명을 고르세요:", options=db_names, default=db_names[:10] if len(db_names) >= 10 else db_names)
    
    if len(selected_names) == 10:
        if st.button("🚀 팀 나누기 시작!", type="primary"):
            selected_players_df = st.session_state.player_db[st.session_state.player_db['이름'].isin(selected_names)]
            players = selected_players_df.to_dict('records')
            roles = ['탱커', '탱커', '메인딜러', '메인딜러', '서브딜러', '서브딜러', '힐러', '힐러', '힐러', '힐러']
            
            best_diff, best_match = float('inf'), None
            
            with st.spinner('황금 밸런스를 계산 중입니다...'):
                for _ in range(30000): 
                    random.shuffle(players)
                    is_valid, t1_score, t2_score = True, 0, 0
                    match_result = {'Team1': [], 'Team2': []}
                    
                    for i in range(10):
                        p, role = players[i], roles[i]
                        score = p.get(role, 0)
                        if score <= 0:
                            is_valid = False
                            break
                        
                        player_info = {'포지션': role, '이름': p['이름'], '점수': score}
                        if i % 2 == 0:
                            t1_score += score
                            match_result['Team1'].append(player_info)
                        else:
                            t2_score += score
                            match_result['Team2'].append(player_info)
                            
                    if is_valid:
                        diff = abs(t1_score - t2_score)
                        if diff < best_diff:
                            best_diff, best_match = diff, (match_result, t1_score, t2_score)
                            if diff <= 1: break
            
            if best_match:
                # 결과 세션에 저장 (버튼 눌러도 안 날아가게)
                st.session_state.current_match = best_match
            else:
                st.error("🚨 포지션 폭이 겹쳐서 팀을 구성할 수 없습니다.")
                st.session_state.current_match = None

    # 매치가 생성되어 있다면 결과 보여주고 기록 버튼 활성화
    if st.session_state.current_match:
        match, s1, s2 = st.session_state.current_match
        st.write("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"🔵 블루 팀 (합계: {s1}점)")
            st.dataframe(pd.DataFrame(match['Team1']), hide_index=True, use_container_width=True)
        with col2:
            st.subheader(f"🔴 레드 팀 (합계: {s2}점)")
            st.dataframe(pd.DataFrame(match['Team2']), hide_index=True, use_container_width=True)
            
        st.info(f"⚖️ 양 팀 점수 차이: **{abs(s1 - s2)}점**")
        
        st.write("### 📝 경기 결과 기록")
        st.caption("경기가 끝난 후 승리한 팀을 클릭하면 데이터베이스에 전적이 기록됩니다.")
        
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        
        # 결과 기록 로직 함수
        def record_result(winning_team):
            db = st.session_state.player_db.copy()
            for team_name in ['Team1', 'Team2']:
                is_win = (team_name == winning_team)
                for p in match[team_name]:
                    idx = db[db['이름'] == p['이름']].index[0]
                    role = p['포지션']
                    
                    # 총적 업데이트
                    db.at[idx, '총_경기'] += 1
                    if is_win: db.at[idx, '총_승리'] += 1
                    
                    # 포지션별 전적 업데이트
                    db.at[idx, f'{role}_판'] += 1
                    if is_win: db.at[idx, f'{role}_승'] += 1
                    
            if save_to_db(db):
                st.success("🎉 경기 결과가 성공적으로 반영되었습니다!")
                st.session_state.current_match = None # 기록 후 매치 정보 초기화
        
        with btn_col1:
            if st.button("🔵 블루 팀 승리!", use_container_width=True): record_result('Team1')
        with btn_col2:
            if st.button("🔴 레드 팀 승리!", use_container_width=True): record_result('Team2')
        with btn_col3:
            if st.button("❌ 기록하지 않고 취소", use_container_width=True): 
                st.session_state.current_match = None
                st.rerun()


# ==========================================
# 화면 B: 명예의 전당 (승률 통계)
# ==========================================
elif menu == "🏆 명예의 전당":
    st.title("🏆 명예의 전당 & 전적 통계")
    
    df = st.session_state.player_db.copy()
    
    # 0으로 나누는 에러 방지 및 승률 계산
    df['전체승률(%)'] = (df['총_승리'] / df['총_경기'].replace(0, 1) * 100).round(1)
    
    # 3경기 이상 한 사람만 랭킹에 표시 (신뢰도)
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
        st.info("데이터가 충분하지 않습니다. (최소 3경기 이상 플레이한 유저가 3명 이상이어야 TOP3가 표시됩니다.)")

    st.write("---")
    st.subheader("📊 전체 플레이어 세부 전적")
    
    # 보기 편하게 데이터프레임 가공
    display_df = df[['이름', '총_경기', '총_승리', '전체승률(%)']].copy()
    for role in ['탱커', '메인딜러', '서브딜러', '힐러']:
        display_df[f'{role} 승률'] = (df[f'{role}_승'] / df[f'{role}_판'].replace(0, 1) * 100).round(1).astype(str) + "%"
        display_df[f'{role} 승률'] = display_df[f'{role} 승률'].replace("0.0%", "-") # 안 한 포지션은 - 처리
        
    st.dataframe(display_df.sort_values(by='전체승률(%)', ascending=False), hide_index=True, use_container_width=True)


# ==========================================
# 화면 C: 플레이어 DB 관리
# ==========================================
elif menu == "👥 플레이어 DB 관리":
    st.title("👥 플레이어 DB 관리")
    st.caption("실력 점수 수정 및 플레이어 관리를 할 수 있습니다. (전적 데이터도 확인 가능)")
    
    edited_db = st.data_editor(st.session_state.player_db, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    if st.button("💾 구글 시트에 변경사항 저장하기"):
        save_to_db(edited_db)
        st.success("성공적으로 구글 시트에 반영되었습니다!")
