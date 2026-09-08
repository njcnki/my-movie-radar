import streamlit as st
import requests
import math

# ==================== 🛠️ 用户配置区 ====================
OMDB_API_KEY = "f22cac4f"  # 已填入你专属的 8 位免费 Key
ALPHA = 0.7  # 电影算法：大众占比
BETA = 0.3   # 电影算法：专家占比
# =======================================================

# 设置网页标题和图标
st.set_page_config(page_title="7:3 影视严选加权雷达", page_icon="🎬", layout="centered")

st.title("🎬 影视评分 7:3 黄金加权严选雷达")
st.markdown("每次查询将实时联网同步全网活数据池，自动执行自适应双轨加权脱水算法。")
st.caption("电影门槛: 25,000 票 | 剧集门槛: 10,000 票 (完全平铺四个体验梯队)")

def calculate_consensus_score(title):
    base_url = "http://omdbapi.com"
    param_t = "?t=" + requests.utils.quote(title)
    param_key = "&apikey=" + OMDB_API_KEY
    url = base_url + param_t + param_key
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("Response") == "True":
            imdb_rating = float(data.get("imdbRating", 0))
            votes = int(data.get("imdbVotes", "0").replace(",", ""))
            
            media_type = data.get("Type")
            is_series = (media_type == "series")
            
            vote_threshold = 10000 if is_series else 25000
            if votes < vote_threshold:
                return {"status": "error", "msg": f"🛑 【强力拦截】 该影视未达到有效投票门槛 (当前投票数: {votes:,})"}
            
            # 轨道一：剧集专用长线生存率模型
            if is_series:
                total_seasons_str = data.get("totalSeasons", "1")
                try: seasons = int(total_seasons_str)
                except: seasons = 1
                
                base_score = imdb_rating * 10
                season_bonus = 2.0 * math.log(seasons) if seasons > 1 else 0.0
                votes_modifier = 1.5 if votes >= 100000 else (-3.0 if votes < 25000 else 0.0)
                
                cs_score = base_score + season_bonus + votes_modifier
                if cs_score > 100.0: cs_score = 100.0
                log_details = f"IMDb: {imdb_rating} | 总季数: {seasons}季 | 投票基数修正: {votes_modifier:+}"
            
            # 轨道二：标准电影 7:3 严格加权模型
            else:
                raw_metascore = data.get("Metascore", "N/A")
                metascore = 70.0 if raw_metascore == "N/A" else float(raw_metascore)
                cs_score = (ALPHA * (imdb_rating * 10)) + (BETA * metascore)
                log_details = f"IMDb: {imdb_rating} | Metascore: {raw_metascore}"

            # 统一判定四大梯队
            if cs_score >= 88.0: tier_label, color = "T1_神作", "🔴"
            elif 80.0 <= cs_score < 88.0: tier_label, color = "T2_黄金", "🟡"
            elif 75.0 <= cs_score < 80.0: tier_label, color = "T3_优质", "🟢"
            elif 70.0 <= cs_score < 75.0: tier_label, color = "T4_高爽", "🔵"
            else:
                return {"status": "error", "msg": f"🛑 【强力拦截】 该影视存在明显硬伤或海外热度不足，未达收藏及格线。 (最终得分: {cs_score:.1f}分)"}
                
            return {
                "status": "success",
                "title": data.get('Title'),
                "year": data.get('Year'),
                "type": "电视剧" if is_series else "电影",
                "score": f"{cs_score:.1f}",
                "tier": f"{color} {tier_label}",
                "details": log_details
            }
    except Exception as e:
        return {"status": "error", "msg": f"❌ 查询失败，网络发生异常: {str(e)}"}
    return {"status": "error", "msg": "❌ 线上未识别到该影片信息，请检查英文名称是否输入正确。"}

# 网页前端交互组件
movie_input = st.text_input("请输入您要查询的电影或电视剧名字 (推荐英文名):", key="search_input")

if movie_input:
    with st.spinner("正在连接全网数据池，自适应执行双轨算法脱水..."):
        res = calculate_consensus_score(movie_input.strip())
        
    st.markdown("---")
    if res["status"] == "success":
        # 用漂亮的网页卡片和彩色高亮显示结果
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="📊 最终加权得分", value=f"{res['score']} 分")
        with col2:
            st.metric(label="🏷️ 精准归类梯队", value=res["tier"])
            
        st.success(f"**影视信息**：{res['title']} ({res['year']}) | **类别**：{res['type']}")
        st.info(f"**底层活数据审计**：{res['details']}")
    else:
        st.error(res["msg"])
