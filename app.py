import streamlit as st
import pandas as pd
import random

st.set_page_config(layout="wide", page_title="옵치 내전 메이커")

st.title("🎮 오버워치 5:5 내전 팀 밸런서")
st.write("10명의 플레이어 점수를 입력하세요. **플레이할 수 없는 포지션은 0점**으로 비워두시면 됩니다.")

# 1. 초기 데이터 셋업 (스트림릿 세션에 저장하여 날아가지 않게 유지)
if 'player_data' not in st.session_state:
    st.session_state.player_data = pd.DataFrame({
        '이름': [f"플레이어{i}" for i in range(1, 11)],
        '탱커': [2000] * 10,
        '메인딜러': [2000] * 10,
        '서브딜러': [2000] * 10,
        '힐러': [2000] * 10,
    })

# 웹에서 엑셀처럼 직접 수정 가능한 데이터 에디터
edited_df = st.data_editor(st.session_state.player_data, use_container_width=True, hide_index=True)

st.write("---")

if st.button("⚔️ 최적의 팀 나누기 시작!", type="primary"):
    if len(edited_df) != 10:
        st.error("플레이어는 정확히 10명이어야 합니다!")
        st.stop()
        
    players = edited_df.to_dict('records')
    
    # 10개의 슬롯 (0,2,4,6,8은 1팀 / 1,3,5,7,9는 2팀)
    roles = ['탱커', '탱커', '메인딜러', '메인딜러', '서브딜러', '서브딜러', '힐러', '힐러', '힐러', '힐러']
    
    best_diff = float('inf')
    best_match = None
    
    # 2만 번 섞어보며 최적의 밸런스를 찾음
    with st.spinner('알고리즘이 최적의 조합을 계산 중입니다...'):
        for _ in range(20000):
            random.shuffle(players) # 유저 순서를 무작위로 섞음
            
            is_valid = True
            t1_score = 0
            t2_score = 0
            match_result = {'Team1': [], 'Team2': []}
            
            for i in range(10):
                p = players[i]
                role = roles[i]
                score = p[role]
                
                # 점수가 0이거나 입력되지 않았다면 해당 포지션을 못하는 유저
                if pd.isna(score) or score <= 0:
                    is_valid = False
                    break
                    
                # 짝수 인덱스는 1팀, 홀수 인덱스는 2팀으로 배정
                if i % 2 == 0:
                    t1_score += score
                    match_result['Team1'].append({'포지션': role, '이름': p['이름'], '점수': score})
                else:
                    t2_score += score
                    match_result['Team2'].append({'포지션': role, '이름': p['이름'], '점수': score})
                    
            # 10명 모두 가능한 포지션에 배치된 유효한 조합인 경우
            if is_valid:
                diff = abs(t1_score - t2_score)
                # 이전 최고 기록보다 점수 차이가 적으면 갱신
                if diff < best_diff:
                    best_diff = diff
                    best_match = (match_result, t1_score, t2_score)
                    
                    # 양 팀 점수 차이가 20점 이하면 즉시 탐색 종료 (충분히 황금 밸런스)
                    if diff <= 20: 
                        break
                        
    # 결과 출력 UI
    if best_match is None:
        st.error("🚨 10명의 포지션 폭이 너무 좁아 팀을 구성할 수 없습니다. 점수(포지션)를 다시 확인해 주세요.")
    else:
        st.success("✨ 최적의 팀 밸런스를 찾았습니다!")
        match, s1, s2 = best_match
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"🔵 블루 팀 (총점: {s1}점)")
            st.dataframe(pd.DataFrame(match['Team1']), hide_index=True, use_container_width=True)
            
        with col2:
            st.subheader(f"🔴 레드 팀 (총점: {s2}점)")
            st.dataframe(pd.DataFrame(match['Team2']), hide_index=True, use_container_width=True)
            
        st.info(f"⚖️ 양 팀 점수 차이: **{abs(s1 - s2)}점**")
