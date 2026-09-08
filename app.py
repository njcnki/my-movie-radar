import streamlit as st
import requests
import math

# ==================== 🛠️ 用户配置区 ====================
OMDB_API_KEY = "f22cac4f"  # 你的 8 位免费 Key
ALPHA = 0.7  # 电影算法：大众占比
BETA = 0.3   # 电影算法：专家占比
# =======================================================

st.set_page_config(page_title="7:3 智能影视严选雷达", page_icon="🎬", layout="wide")

st.title("🎬 影视评分 7:3 黄金加权严选雷达 (中文自愈强化版)")
st.markdown("支持**直接输入中文/英文/模糊词**。系统会自动完成翻译、多季长线去噪及模糊海报墙推荐。")

def translate_to_english(text):
    """
    自愈式智能中转：多备选机制将中文片名翻译为英文
    """
    # 检查是否包含中文
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        try:
            # 采用全新的独立请求头，防止被谷歌接口判定为爬虫而拦截
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            url = f"https://googleapis.com{requests.utils.quote(text)}"
            res = requests.get(url, headers=headers, timeout=4).json()
            translated = res
            if translated and translated.strip():
                return translated.strip()
        except:
            pass
    return text

def search_movie_list(title):
    """
    模糊搜索探测器：当精准匹配失败时，抓取前5部最相关的影视列表供用户核对
    """
    base_url = "http://www.omdbapi.com/"
    url = f"{base_url}?s={requests.utils.quote(title)}&apikey={OMDB_API_KEY}"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("Response") == "True":
            return res.get("Search",)[:] # 只取最相关的 5 部
    except:
        pass
    return

def calculate_consensus_score(title, search_type):
    base_url = "http://www.omdbapi.com/"
    param_t = "?t=" + requests.utils.quote(title)
    param_key = "&apikey=" + OMDB_API_KEY
    
    param_type = ""
    if search_type == "只查电影": param_type = "&type=movie"
    elif search_type == "只查剧集": param_type = "&type=series"
        
    url = base_url + param_t + param_type + param_key
    
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
                "title": data.get('Title'),
                "year": data.get('Year'),
                "type": "电视剧" if is_series else "电影",
                "poster": poster_url,
                "released": data.get("Released", "暂无数据"),
                "genre": data.get("Genre", "暂无数据"),
                "director": data.get("Director", "暂无数据"),
                "actors": data.get("Actors", "暂无数据"),
                "plot": data.get("Plot", "暂无数据"),
                "country": data.get("Country", "暂无数据"),
                "runtime": data.get("Runtime", "暂无数据"),
                "boxoffice": data.get("BoxOffice", "暂无数据") if not is_series else "N/A"
            }

            vote_threshold = 10000 if is_series else 25000
            if votes < vote_threshold:
                return {"status": "intercepted", "msg": f"🛑 【强力拦截】 该影视未达到有效投票门槛 (当前投票数: {votes:,})", **info_base}
            
            if is_series:
                try: seasons = int(data.get("totalSeasons", "1"))
                except: seasons = 1
                base_score = imdb_rating * 10
                season_bonus = 2.0 * math.log(seasons) if seasons > 1 else 0.0
                votes_modifier = 1.5 if votes >= 100000 else (-3.0 if votes < 25000 else 0.0)
                cs_score = base_score + season_bonus + votes_modifier
                if cs_score > 100.0: cs_score = 100.0
                log_details = f"IMDb: {imdb_rating} ({votes:,} 票) | 总季数: {seasons}季 | 投票基数修正: {votes_modifier:+}"
            else:
                raw_metascore = data.get("Metascore", "N/A")
                metascore = 70.0 if raw_metascore == "N/A" else float(raw_metascore)
                cs_score = (ALPHA * (imdb_rating * 10)) + (BETA * metascore)
                log_details = f"IMDb: {imdb_rating} ({votes:,} 票) | Metascore: {raw_metascore}"

            if cs_score >= 88.0: tier_label, color = "T1_神作", "🔴"
            elif 80.0 <= cs_score < 88.0: tier_label, color = "T2_黄金", "🟡"
            elif 75.0 <= cs_score < 80.0: tier_label, color = "T3_优质", "🟢"
            elif 70.0 <= cs_score < 75.0: tier_label, color = "T4_高爽", "🔵"
            else:
                return {"status": "intercepted", "msg": f"🛑 【强力拦截】 该影视未达收藏及格线。 (最终得分: {cs_score:.1f}分)", **info_base}
                
            return {"status": "success", "score": f"{cs_score:.1f}", "tier": f"{color} {tier_label}", "details": log_details, **info_base}
    except:
        pass
    return {"status": "not_found"}

# 前端交互组件
search_type = st.radio(
    "🧭 影视类型定位器 (遇到同名冲突时手动切换):",
    ["自动识别", "只查电影", "只查剧集"], horizontal=True
)

movie_input = st.text_input("请输入电影或电视剧名字 (直接写中文、英文或模糊词均可):", key="search_input")

if movie_input:
    raw_input = movie_input.strip()
    
    with st.spinner("正在启动智能中转与算法脱水..."):
        # 1. 自动执行中文翻译
        eng_title = translate_to_english(raw_input)
        if eng_title != raw_input:
            st.caption(f"🤖 智能翻译中转：已自动将「{raw_input}」转化为英文关键词「{eng_title}」进行匹配...")
            
        # 2. 尝试精准跑分
        res = calculate_consensus_score(eng_title, search_type)
        
    st.markdown("---")
    
    # 情况 A：精准匹配成功（过关或拦截）
    if res["status"] in ["success", "intercepted"]:
        # 🛠️ 彻底修复：传入 黄金视觉比例参数，解决云端部署报错塌方
        layout_col1, layout_col2 = st.columns() 
        with layout_col1:
            st.image(res["poster"], caption=f"《{res['title']}》海报", use_container_width=True)
        with layout_col2:
            if res["status"] == "success":
                card_col1, card_col2 = st.columns(2)
                with card_col1: st.metric(label="📊 最终加权得分", value=f"{res['score']} 分")
                with card_col2: st.metric(label="🏷️ 精准归类梯队", value=res["tier"])
                st.success(f"**影视诊断**：已成功收入本地数字资产仓储库。")
            else:
                st.error(res["msg"])
            
            st.markdown("### 🎞️ 影视详细档案")
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
            st.markdown(f"**🎭 核心演员**：{res['actors']}")
            st.markdown("#### 📝 剧情梗概")
            st.info(res["plot"])
            if res["status"] == "success": st.caption(f"🔧 **活数据监控**：{res['details']}")
            
    # 情况 B：精准匹配失败，开启海报墙选片模式
    else:
        st.warning(f"🔍 未能直接精确匹配到「{eng_title}」。已自动为您启动【模糊搜索海报墙探测器】...")
        fuzzy_list = search_movie_list(eng_title)
        
        if fuzzy_list:
            st.markdown("### 🗺️ 帮您找到以下最相关的影视，请比对海报和年份：")
            cols = st.columns(len(fuzzy_list))
            for idx, item in enumerate(fuzzy_list):
                with cols[idx]:
                    p_url = item.get("Poster", "N/A")
                    if p_url == "N/A" or not p_url.startswith("http"):
                        p_url = "https://unsplash.com"
                    
                    st.image(p_url, use_container_width=True)
                    st.markdown(f"**🎬 {item.get('Title')}**")
                    st.caption(f"📅 年份: {item.get('Year')} | 类别: {item.get('Type')}")
                    st.code(item.get('Title'), language="text") 
            st.info("💡 **使用窍门**：如果您在上方海报墙中看到了您想找的电影，可以直接**复制它下方的英文框内容**，重新输入上方输入框查询，即可瞬间吐出精确跑分！")
        else:
            st.error("❌ 抱歉，全网数据库中实在找不到与该关键词相关的任何影视，请尝试精简或更换关键词。")
