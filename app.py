import streamlit as st
import requests
import math
import re
import os

# ==================== 🛠️ 用户配置区 ====================
OMDB_API_KEY = "f22cac4f"  # 你的 8 位免费 Key
ALPHA = 0.7  # 电影加权：大众占比
BETA = 0.3   # 电影加权：专家占比
# =======================================================

st.set_page_config(page_title="7:3 智能影视资产雷达", page_icon="🎬", layout="wide")

st.title("🎬 智能影视评分 7:3 黄金加权严选雷达")
st.markdown("已完美融合 **手动搜索框** 与 **本地多格式/硬核PT命名文件海报墙盲刷引擎**。")

@st.cache_data(ttl=3600)
def fetch_movie_data(title, search_type="自动识别"):
    base_url = "http://omdbapi.com"
    param_t = "?t=" + requests.utils.quote(title)
    
    param_type = ""
    if search_type == "只查电影": param_type = "&type=movie"
    elif search_type == "只查剧集": param_type = "&type=series"
        
    url = base_url + param_t + param_type + "&apikey=" + OMDB_API_KEY
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
                return {"status": "intercepted", "msg": f"🛑 未达有效投票门槛 (当前投票: {votes:,})", **info_base}
            
            if is_series:
                try: seasons = int(data.get("totalSeasons", "1"))
                except: seasons = 1
                base_score = imdb_rating * 10
                season_bonus = 2.0 * math.log(seasons) if seasons > 1 else 0.0
                votes_modifier = 1.5 if votes >= 100000 else (-3.0 if votes < 25000 else 0.0)
                cs_score = base_score + season_bonus + votes_modifier
                if cs_score > 100.0: cs_score = 100.0
                log_details = f"IMDb: {imdb_rating} | {seasons}季 | 修正: {votes_modifier:+}"
            else:
                raw_metascore = data.get("Metascore", "N/A")
                metascore = 70.0 if raw_metascore == "N/A" else float(raw_metascore)
                cs_score = (ALPHA * (imdb_rating * 10)) + (BETA * metascore)
                log_details = f"IMDb: {imdb_rating} | Metascore: {raw_metascore}"

            if cs_score >= 88.0: tier, color = "T1_神作", "🔴"
            elif 80.0 <= cs_score < 88.0: tier, color = "T2_黄金", "🟡"
            elif 75.0 <= cs_score < 80.0: tier, color = "T3_优质", "🟢"
            elif 70.0 <= cs_score < 75.0: tier, color = "T4_高爽", "🔵"
            else:
                return {"status": "intercepted", "msg": f"🛑 未达及格线 (评分: {cs_score:.1f}分)", **info_base}
                
            return {"status": "success", "score": f"{cs_score:.1f}", "tier": f"{color} {tier}", "details": log_details, **info_base}
    except:
        pass
    return {"status": "not_found"}

def clean_filename_hardcore(filename):
    """
    🎛️ 终极自适应：专门剥离多层虚拟路径，精准斩断 PT 压制组复杂后缀
    """
    clean_name = filename.replace("\\", "/").split("/")[-1]
    clean_name, _ = os.path.splitext(clean_name)
    clean_name = clean_name.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    
    for ext in ['mkv', 'mp4', 'avi', 'iso', 'm2ts']:
        if clean_name.lower().endswith(ext):
            clean_name = clean_name[:-len(ext)].strip()

    keywords = [
        r'\b\d{4}\b', r'\be\d+\b', r'\bs\d+\b', r'\b\d+p\b', r'\b\d+k\b',
        r'\bbluray\b', r'\bremux\b', r'\bdts\b', r'\bhdma\b', r'\batmos\b', 
        r'\bx264\b', r'\bx265\b', r'\bhevc\b', r'\bavc\b', r'\bchd\b', r'\bwiki\b'
    ]
    
    pattern = re.compile('|'.join(keywords), re.IGNORECASE)
    match = pattern.search(clean_name)
    
    if match:
        clean_name = clean_name[:match.start()]
        
    return clean_name.strip()

def render_movie_ui_block(res, clean_title):
    if res["status"] in ["success", "intercepted"]:
        layout_col1, layout_col2 = st.columns([1, 2]) 
        with layout_col1:
            st.image(res["poster"], caption=f"《{res['title']}》海报", use_container_width=True)
        with layout_col2:
            if res["status"] == "success":
                card_col1, card_col2 = st.columns(2)
                with card_col1: st.metric(label="📊 最终加权得分", value=f"{res['score']} 分")
                with card_col2: st.metric(label="🏷️ 精准归类梯队", value=res["tier"])
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
    else:
        st.error(f"❌ 线上未匹配到与「{clean_title}」相关的影视信息，请检查英文名命名结构。")

# ==================== 🎛️ 前端控制中心 ====================
search_mode = st.sidebar.radio("⚙️ 请选择操作模式：", ["🔍 单部精确搜索", "📂 批量扫描本地文件夹"])

# ----------------- 引擎一：手动精确搜索框 -----------------
if search_mode == "🔍 单部精确搜索":
    search_type = st.radio("🧭 影视类型定位器：", ["自动识别", "只查电影", "只查剧集"], horizontal=True)
    movie_input = st.text_input("请输入您要查询的电影或电视剧名字 (英文名)：", key="single_search")
    
    if movie_input:
        with st.spinner("正在连接全网数据池..."):
            res = fetch_movie_data(movie_input.strip(), search_type)
        st.markdown("---")
        render_movie_ui_block(res, movie_input)

# ----------------- 引擎二：本地文件夹批量刷盘 -----------------
else:
    st.subheader("📂 本地影视资产海报墙")
    uploaded_files = st.file_uploader(
        "选择或拖拽您的 NAS / 本地电影文件夹到这里：", 
        accept_multiple_files=True, 
        key="folder_loader"
    )
    
    if uploaded_files:
        video_extensions = ('.mp4', '.mkv', '.avi', '.iso', '.m2ts')
        valid_movie_names = []
        
        for file in uploaded_files:
            path_parts = file.name.replace("\\", "/").split("/")
            filename = path_parts[-1]
            
            if filename.lower().endswith(video_extensions) or "bdmv" in file.name.lower() or "certificate" in file.name.lower():
                if "bdmv" in file.name.lower() or "certificate" in file.name.lower():
                    if len(path_parts) >= 3:
                        valid_movie_names.append(path_parts[-3])
                    continue
                valid_movie_names.append(file.name)
                
        valid_movie_names = list(set(valid_movie_names))
        
        if not valid_movie_names:
            st.warning("⚠️ 探测完成，但选中的文件里似乎没有包含标准的视频格式或蓝光原盘。")
        else:
            st.subheader(f"📊 成功捕获本地影视资源 {len(valid_movie_names)} 部：")
            st.markdown("---")
            
            columns_per_row = 4
            for i in range(0, len(valid_movie_names), columns_per_row):
                cols = st.columns(columns_per_row)
                for j in range(columns_per_row):
                    if i + j < len(valid_movie_names):
                        raw_name = valid_movie_names[i + j]
                        clean_title = clean_filename_hardcore(raw_name)
                        res = fetch_movie_data(clean_title)
                        
                        with cols[j]:
                            if res["status"] == "success":
                                st.image(res["poster"], use_container_width=True)
                                st.markdown(f"**🎬 {res['title']} ({res['year']})**")
                                st.markdown(f"分：`{res['score']}` | 档：{res['tier']}")
                                with st.expander("🔍 展开影视详细档案"):
                                    st.caption(f"**类型**：{res['type']} | **风格**：{res['genre']}\n\n**导演**：{res['director']}")
                                    st.info(res["plot"])
                            elif res["status"] == "intercepted":
                                p_url = res["poster"] if (res.get("poster") and res["poster"] != "N/A") else "https://unsplash.com"
                                st.image(p_url, use_container_width=True)
                                st.markdown(f"**⚠️ {res['title'] if res.get('title') else clean_title}**")
                                st.error(f"🛑 强力拦截：{res['msg']}")
                            else:
                                st.image("https://unsplash.com", use_container_width=True)
                                st.markdown(f"**❌ {clean_title}**")
                                st.warning("未匹配到，请检查英文名")
                st.markdown("---")
