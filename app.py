import streamlit as st
import pandas as pd
import random
import requests
import json

st.set_page_config(layout="wide", page_title="옵치 내전 밸런서")

# 아까 복사해둔 Apps Script 웹 앱 URL을 여기에 넣으세요!
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwvJh8WjDUALBD7sB7ht-e4yFxivOvzPyUGOsMLYTcdJ6vbQYJaZEbR5KchUKh3K8i3zQ/exec"

# 시트에서 데이터 불러오기
@st.cache_data(ttl=0) 
def load_data():
    try:
        response = requests.get(WEB_APP_URL)
        # 구글 로그인 창(HTML)이 넘어오면 json() 변환에서 에러가 남
        data = response.json() 
        if not data: 
            return pd.DataFrame(columns=['이름', '탱커', '메인딜러', '서브딜러', '힐러'])
        return pd.DataFrame(data)
    except Exception as e:
        # 에러가 나더라도 '이름' 열이 존재하는 빈 표를 만들어서 사이트가 뻗는 걸 막아줌
        st.error("🚨 구글 시트 연결 실패! URL 주소, 앱스 스크립트 권한, 시트 이름을 다시 확인해 주세요.")
        return pd.DataFrame(columns=['이름', '탱커', '메인딜러', '서브딜러', '힐러'])

# 초기 데이터 로드
if 'player_db' not in st.session_state:
    st.session_state.player_db = load_data()

st.sidebar.title("메뉴")
menu = st.sidebar.radio("페이지 이동:", ["🏠 내전 팀 짜기", "👥 플레이어 DB 관리"])

# ==========================================
# 화면 A: 플레이어 DB 관리 페이지
# ==========================================
if menu == "👥 플레이어 DB 관리":
    st.title("👥 플레이어 DB 관리 (Apps Script 연동)")
    st.write("여기서 수정한 내용은 구글 시트에 실시간으로 저장됩니다.")
    
    # 데이터 수정 에디터
    edited_db = st.data_editor(
        st.session_state.player_db, 
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True
    )
    
    # 저장 버튼
    if st.button("💾 구글 시트에 변경사항 저장하기"):
        with st.spinner("구글 시트에 동기화 중..."):
            edited_db = edited_db.fillna(0) # 빈칸 0점 처리
            
            # DataFrame을 JSON으로 변환하여 POST 요청 보내기
            json_data = edited_db.to_dict('records')
            response = requests.post(WEB_APP_URL, json=json_data)
            
            if response.status_code == 200:
                st.session_state.player_db = edited_db
                st.success("성공적으로 구글 시트에 반영되었습니다!")
                st.cache_data.clear()
            else:
                st.error("저장 실패! 연결 상태를 확인해 주세요.")

# ==========================================
# 화면 B: 내전 팀 짜기 페이지 (이전 코드와 완전 동일)
# ==========================================
elif menu == "🏠 내전 팀 짜기":
    st.title("🎮 오버워치 5:5 내전 팀 밸런서")
    
    # NaN이나 빈 문자열 등 잘못된 데이터 전처리
    db_names = [name for name in st.session_state.player_db['이름'].tolist() if pd.notna(name) and str(name).strip() != '']
    
    selected_names = st.multiselect(
        "⚔️ 오늘 내전에 참여할 10명을 고르세요:", 
        options=db_names,
        default=db_names[:10] if len(db_names) >= 10 else db_names
    )
    
    if len(selected_names) != 10:
        st.warning(f"현재 {len(selected_names)}명 선택되었습니다. 정확히 10명을 선택해야 합니다.")
    else:
        if st.button("🚀 팀 나누기 시작!", type="primary"):
            selected_players_df = st.session_state.player_db[st.session_state.player_db['이름'].isin(selected_names)]
            players = selected_players_df.to_dict('records')
            
            roles = ['탱커', '탱커', '메인딜러', '메인딜러', '서브딜러', '서브딜러', '힐러', '힐러', '힐러', '힐러']
            best_diff = float('inf')
            best_match = None
            
            with st.spinner('최적의 황금 밸런스를 계산 중입니다...'):
                for _ in range(30000): 
                    random.shuffle(players)
                    is_valid = True
                    t1_score, t2_score = 0, 0
                    match_result = {'Team1': [], 'Team2': []}
                    
                    for i in range(10):
                        p, role = players[i], roles[i]
                        
                        # Apps Script에서 넘어오면서 문자열로 인식될 수 있으니 int/float 처리
                        try:
                            score = float(p.get(role, 0))
                        except ValueError:
                            score = 0
                            
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
                            if diff <= 1: 
                                break

            if best_match:
                match, s1, s2 = best_match
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(f"🔵 블루 팀 (합계: {int(s1)}점)")
                    st.dataframe(pd.DataFrame(match['Team1']), hide_index=True, use_container_width=True)
                    
                with col2:
                    st.subheader(f"🔴 레드 팀 (합계: {int(s2)}점)")
                    st.dataframe(pd.DataFrame(match['Team2']), hide_index=True, use_container_width=True)
                    
                st.info(f"⚖️ 양 팀 점수 차이: **{int(abs(s1 - s2))}점**")
            else:
                st.error("🚨 10명의 포지션 폭이 겹쳐서 팀을 구성할 수 없습니다. DB에서 포지션별 점수를 확인해 주세요.")
