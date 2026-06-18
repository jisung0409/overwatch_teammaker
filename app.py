import streamlit as st
import pandas as pd
import random
import requests

st.set_page_config(layout="wide", page_title="옵치 내전 시스템")

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwzO63tMB7jkr9tUAPU0cZTgxv4OjKj9iZi-zfkSkVxdc83Hn05CDFzQe4N5u5x0fyF0w/exec"

STATS_COLS = ['총_경기', '총_승리', '탱커_판', '탱커_승', '메인딜러_판', '메인딜러_승', '서브딜러_판', '서브딜러_승', '힐러_판', '힐러_승']

@st.cache_data(ttl=0)
def load_data():
    try:
        response = requests.get(WEB_APP_URL)
        data = response.json()
        base_columns = ['이름', '주_포지션', '탱커', '메인딜러', '서브딜러', '힐러'] + STATS_COLS
        if not data: return pd.DataFrame(columns=base_columns)
        
        df = pd.DataFrame(data)
        if '주_포지션' not in df.columns: df.insert(1, '주_포지션', '없음')
        for col in STATS_COLS:
            if col not in df.columns: df[col] = 0
                
        for col in ['탱커', '메인딜러', '서브딜러', '힐러'] + STATS_COLS:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error("🚨 구글 시트 연결 실패!")
        return pd.DataFrame(columns=['이름', '주_포지션', '탱커', '메인딜러', '서브딜러', '힐러'] + STATS_COLS)

def save_to_db(df):
    with st.spinner("구글 시트에 동기화 중..."):
        response = requests.post(WEB_APP_URL, json=df.to_dict('records'))
        if response.status_code == 200:
            st.session_state.player_db = df
            st.cache_data.clear()
            return True
        return False

if 'player_db' not in st.session_state: st.session_state.player_db = load_data()
if 'current_match' not in st.session_state: st.session_state.current_match = None

st.sidebar.title("메뉴")
menu = st.sidebar.radio("페이지 이동:", ["🏠 내전 팀 짜기", "🏆 명예의 전당", "👥 플레이어 DB 관리"])

if menu == "🏠 내전 팀 짜기":
    st.title("🎮 오버워치 내전 메이커")
    st.caption("AI 다중 최적화: 밸런스를 맞추면서 동시에 플레이어들의 주 포지션과 최고 실력을 보장합니다.")
    
    db_names = [name for name in st.session_state.player_db['이름'].tolist() if str(name).strip() != '']
    selected_names = st.multiselect("⚔️ 참여할 10명을 고르세요:", options=db_names, default=db_names[:10] if len(db_names) >= 10 else db_names)
    
    if len(selected_names) == 10:
        if st.button("🚀 최적 조합 찾기!", type="primary"):
            players = st.session_state.player_db[st.session_state.player_db['이름'].isin(selected_names)].to_dict('records')
            roles = ['탱커', '탱커', '메인딜러', '메인딜러', '서브딜러', '서브딜러', '힐러', '힐러', '힐러', '힐러']
            
            # 비교를 위한 최고 기록 변수들
            best_diff = float('inf')
            best_weighted_skill = -float('inf')
            best_tie_breakers = (float('inf'), float('inf'), float('inf'))
            best_match = None
            
            with st.spinner('수만 가지 경우의 수를 분석하여 황금 밸런스를 찾습니다...'):
                for _ in range(50000): # 연산 횟수 5만번으로 증가
                    random.shuffle(players)
                    is_valid = True
                    
                    t1_base = {'탱커':0, '딜러':0, '힐러':0, '총점':0}
                    t2_base = {'탱커':0, '딜러':0, '힐러':0, '총점':0}
                    t1_weighted, t2_weighted = 0, 0
                    match_result = {'Team1': [], 'Team2': []}
                    
                    for i in range(10):
                        p = players[i]
                        role = roles[i]
                        base_score = float(p.get(role, 0))
                        if base_score <= 0:
                            is_valid = False
                            break
                        
                        # 띄어쓰기 오류 방지 (.strip())
                        is_main = str(p.get('주_포지션', '')).strip() == role
                        weighted_score = base_score + 0.5 if is_main else base_score
                        
                        display_score = f"{weighted_score} ⭐" if is_main else f"{weighted_score}"
                        player_info = {'포지션': role, '이름': p['이름'], '점수': display_score, '원점수': weighted_score}
                        
                        role_group = '딜러' if '딜러' in role else role
                        if i % 2 == 0:
                            t1_base['총점'] += base_score
                            t1_base[role_group] += base_score
                            t1_weighted += weighted_score
                            match_result['Team1'].append(player_info)
                        else:
                            t2_base['총점'] += base_score
                            t2_base[role_group] += base_score
                            t2_weighted += weighted_score
                            match_result['Team2'].append(player_info)
                            
                    if is_valid:
                        # 밸런스 차이는 '가중치 없는 순수 점수(base)'로만 계산하여 0.5점의 함정 방지
                        total_diff = abs(t1_base['총점'] - t2_base['총점'])
                        tank_diff = abs(t1_base['탱커'] - t2_base['탱커'])
                        dps_diff = abs(t1_base['딜러'] - t2_base['딜러'])
                        heal_diff = abs(t1_base['힐러'] - t2_base['힐러'])
                        
                        total_weighted_skill = t1_weighted + t2_weighted # 전체 실력 + 가중치 합
                        current_tie_breakers = (tank_diff, dps_diff, heal_diff)
                        is_better = False
                        
                        if best_match is None:
                            is_better = True
                        else:
                            # [핵심 로직] 1. 밸런스가 허용 범위(격차 2 이하)인가?
                            if total_diff <= 2 and best_diff <= 2:
                                # 2. 밸런스가 맞다면, 유저들이 가장 잘하는 포지션에 갔는가? (전체 실력 합 비교)
                                if total_weighted_skill > best_weighted_skill:
                                    is_better = True
                                elif total_weighted_skill == best_weighted_skill:
                                    # 3. 실력도 같다면 더 정밀하게 격차가 적은 쪽
                                    if total_diff < best_diff:
                                        is_better = True
                                    elif total_diff == best_diff:
                                        # 4. 동점일 경우 탱커 -> 딜러 -> 힐러 격차 비교
                                        if tank_diff < best_tie_breakers[0]: is_better = True
                                        elif tank_diff == best_tie_breakers[0] and dps_diff < best_tie_breakers[1]: is_better = True
                                        elif tank_diff == best_tie_breakers[0] and dps_diff == best_tie_breakers[1] and heal_diff < best_tie_breakers[2]: is_better = True
                            else:
                                if total_diff <= 2 and best_diff > 2: is_better = True
                                elif total_diff > 2 and best_diff > 2:
                                    if total_diff < best_diff: is_better = True
                                    elif total_diff == best_diff and total_weighted_skill > best_weighted_skill: is_better = True

                        if is_better:
                            best_diff = total_diff
                            best_weighted_skill = total_weighted_skill
                            best_tie_breakers = current_tie_breakers
                            best_match = (match_result, t1_weighted, t2_weighted)

            if best_match:
                st.session_state.current_match = best_match
            else:
                st.error("🚨 구성할 수 있는 조합이 없습니다.")
                st.session_state.current_match = None

    if st.session_state.current_match:
        match, s1, s2 = st.session_state.current_match
        st.write("---")
        col1, col2 = st.columns(2)
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

elif menu == "👥 플레이어 DB 관리":
    st.title("👥 플레이어 DB 관리")
    edited_db = st.data_editor(st.session_state.player_db, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("💾 구글 시트에 변경사항 저장하기"):
        save_to_db(edited_db)
        st.success("성공적으로 구글 시트에 반영되었습니다!")
