import streamlit as st
import requests
import math

# ==================== 🛠️ 用户配置区 ====================
OMDB_API_KEY = "f22cac4f"  # 你的 8 位免费 Key
ALPHA = 0.7  # 电影加权：大众占比
BETA = 0.3   # 电影加权：专家占比
# =======================================================

st.set_page_config(page_title="7:3 智能影视严选雷达", page_icon="🎬", layout="wide")

st.title("🎬 智能影视评分 7:3 黄金加权严选雷达 (多版本进化版)")
st.markdown("请输入影视作品的英文名。系统将自动联网**搜出全网所有同名版本**供您挑选和严选跑分。")

def calculate_consensus_score_by_id(imdb_id):
    """
    通过唯一的 IMDb ID 进行精确且绝对不会撞车的 7:3 算法跑分
    """
    url = f"http://omdbapi.com{imdb_id}&apikey={OMDB_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("Response") == "True":
            imdb_rating = float(data.get("imdbRating", 0))
            votes = int(data.get("imdbVotes", "0").replace(",", ""))
            media_type = data.get("Type")
            is_series = (media_type == "series")
            
            poster_url = data.get("Poster", "N/A")
            if poster_url == "N/A" or not poster_url.startswith("http"):
                poster_url = "https://unsplash.com"

            info_base = {
                "title": data.get('Title'), "year": data.get('Year'),
                "type": "电视剧" if is_series else "电影", "poster": poster_url,
                "released": data.get("Released", "暂无数据"), "genre": data.get("Genre", "暂无数据"),
                "director": data.get("Director", "暂无数据"), "actors": data.get("Actors", "暂无数据"),
                "plot": data.get("Plot", "暂无数据"), "country": data.get("Country", "暂无数据"),
                "runtime": data.get("Runtime", "暂无数据"), "boxoffice": data.get("BoxOffice", "暂无数据") if not is_series else "N/A"
            }

            vote_threshold = 10000 if is_series else 25000
            if votes < vote_threshold:
                return {"status": "intercepted", "msg": f"🛑 【强力拦截】 该影视未达到有效投票门槛 (当前投票: {votes:,})", **info_base}
            
            if is_series:
                try: seasons = int(data.get("totalSeasons", "1"))
                except: seasons = 1
                base_score = imdb_rating * 10
                season_bonus = 2.0 * math.log(seasons) if seasons > 1 else 0.0
                votes_modifier = 1.5 if votes >= 100000 else (-3.0 if votes < 25000 else 0.0)
                cs_score = base_score + season_bonus + votes_modifier
                if cs_score > 100.0: cs_score = 100.0
                log_details = f"IMDb: {imdb_rating} ({votes:,} 票) | 总季数: {seasons}季 | 修正: {votes_modifier:+}"
            else:
                raw_metascore = data.get("Metascore", "N/A")
                metascore = 70.0 if raw_metascore == "N/A" else float(raw_metascore)
                cs_score = (ALPHA * (imdb_rating * 10)) + (BETA * metascore)
                log_details = f"IMDb: {imdb_rating} ({votes:,} 票) | Metascore: {raw_metascore}"

            if cs_score >= 88.0: tier, color = "T1_神作", "🔴"
            elif 80.0 <= cs_score < 88.0: tier, color = "T2_黄金", "🟡"
            elif 75.0 <= cs_score < 80.0: tier, color = "T3_优质", "🟢"
            elif 70.0 <= cs_score < 75.0: tier, color = "T4_高爽", "🔵"
            else:
                return {"status": "intercepted", "msg": f"🛑 【强力拦截】 该影视未达收藏及格线。 (最终得分: {cs_score:.1f}分)", **info_base}
                
            return {"status": "success", "score": f"{cs_score:.1f}", "tier": f"{color} {tier}", "details": log_details, **info_base}
    except:
        pass
    return {"status": "not_found"}

def get_movie_versions_list(title):
    """
    抓取全网所有同名、不同年份、不同版本的影视列表
    """
    url = f"http://omdbapi.com{requests.utils.quote(title)}&apikey={OMDB_API_KEY}"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("Response") == "True":
            return res.get("Search", [])[:8]  # 最多平铺展示前 8 个最相关的不同版本
    except:
        pass
    return []

# 🎛️ 前端唯一的全局核心输入框
movie_input = st.text_input("请输入您要查询的影视名字 (标准英文名)：", key="search_input")

if movie_input:
    raw_title = movie_input.strip()
    
    with st.spinner("正在检索全网同名资源版本库..."):
        versions = get_movie_versions_list(raw_title)
        
    if not versions:
        st.error("❌ 线上未识别到任何与该名称相关的影视信息，请检查拼写。")
    else:
        st.subheader(f"🗺️ 为您在全网侦测到「{raw_title}」的以下不同版本，请核对：")
        
        # 每行平铺 4 个版本卡片
        columns_per_row = 4
        for i in range(0, len(versions), columns_per_row):
            cols = st.columns(columns_per_row)
            for j in range(columns_per_row):
                if i + j < len(versions):
                    item = versions[i + j]
                    imdb_id = item.get("imdbID")
                    v_title = item.get("Title")
                    v_year = item.get("Year")
                    v_type = "🎬 电影" if item.get("Type") == "movie" else "📺 剧集"
                    
                    p_url = item.get("Poster", "N/A")
                    if p_url == "N/A" or not p_url.startswith("http"):
                        p_url = "https://unsplash.com"
                        
                    with cols[j]:
                        # 渲染版本小卡片
                        st.image(p_url, use_container_width=True)
                        st.markdown(f"**{v_title}**")
                        st.caption(f"📅 年份: {v_year} | 类别: {v_type}")
                        
                        # 🌟 核心点睛之笔：每个版本下面焊死一个独立的点击审计按钮
                        if st.button(f"🔍 审计此版本得分", key=f"btn_{imdb_id}"):
                            # 记录当前点击的 ID 到临时会话中
                            st.session_state["active_imdb_id"] = imdb_id
                            st.session_state["active_title"] = v_title
            st.markdown("---")

    # 💡 动态审计展示区：当你点击某一部版本的按钮时，下方一秒刷出 7:3 精确脱水报告！
    if "active_imdb_id" in st.session_state:
        st.markdown(f"## 📊 针对版本《{st.session_state['active_title']}》的严选审计报告")
        
        with st.spinner("正在穿透唯一ID数据锁，执行算法脱水..."):
            res = calculate_consensus_score_by_id(st.session_state["active_imdb_id"])
            
        if res["status"] in ["success", "intercepted"]:
            layout_col1, layout_col2 = st.columns(2) 
            
            with layout_col1:
                st.image(res["poster"], caption=f"《{res['title']}》官方海报", use_container_width=True)
                
            with layout_col2:
                if res["status"] == "success":
                    card_col1, card_col2 = st.columns(2)
                    with card_col1: st.metric(label="📊 最终加权得分", value=f"{res['score']} 分")
                    with card_col2: st.metric(label="🏷️ 精准归类梯队", value=res["tier"])
                    st.success(f"**影视诊断**：该版本已成功通过核心算法清洗！")
                else:
                    st.error(res["msg"])
                
                st.markdown("### 🎞️ 该版本详细档案")
                meta_col1, meta_col2 = st.columns(2)
                with meta_col1:
                    st.markdown(f"**🎬 影视原名**：{res['title']}")
                    st.markdown(f"**📅 年份/首播**：{res['year']} ({res['released']})")
                    st.markdown(f"**⏳ 类型/时长**：{res['genre']} / {res['runtime']}")
                with meta_col2:
                    st.markdown(f"**🌍 国家/地区**：{res['country']}")
                    st.markdown(f"**🎥 导演/主创**：{res['director']}")
                    if res['type'] == "电影": st.markdown(f"**💰 院线票房**：{res['boxoffice']}")
                    else: st.markdown(f"**📺 影视类别**：电视剧/剧集")
                        
                st.markdown(f"**🎭 核心演员阵容**：{res['actors']}")
                st.markdown("#### 📝 剧情梗概")
                st.info(res["plot"])
                
                if res["status"] == "success":
                    st.caption(f"🔧 **底层数据链监控**：{res['details']}")
