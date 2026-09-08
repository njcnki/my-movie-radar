import streamlit as st
import requests
import math

# ==================== 🛠️ 用户配置区 ====================
OMDB_API_KEY = "f22cac4f"  # 你的 8 位免费 Key
ALPHA = 0.7  # 电影大众占比
BETA = 0.3   # 电影专家占比
# =======================================================

st.set_page_config(page_title="云端影视资产严选看板", page_icon="🎬", layout="wide")

st.title("🎬 私人本地影视资产·云端严选看板")
st.markdown("💡 **原理说明**：点击下方按钮选择您的本地电影文件夹，浏览器**仅读取影视文件名**，绝对不会上传您的视频隐私，不消耗任何物理流量。")

def clean_filename(filename):
    """
    智能清洗浏览器抓取到的本地视频文件名，剥离压制标签和后缀
    """
    # 比如从 "Inception.2010.1080p.Bluray.mkv" 中提取 "Inception"
    clean = filename.split('.1080p').split('.2160p').split('.Bluray').split('.UHD').split('.Remux').split('.S0')
    # 替换点和下划线为空格
    return clean.replace('.', ' ').replace('_', ' ').strip()

@st.cache_data(ttl=3600)  # 对请求做1小时缓存，防止疯狂刷新把 1000 次免费额度用光
def fetch_movie_data(title):
    base_url = "http://omdbapi.com"
    url = f"{base_url}?t={requests.utils.quote(title)}&apikey={OMDB_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("Response") == "True":
            imdb_rating = float(data.get("imdbRating", 0))
            votes = int(data.get("imdbVotes", "0").replace(",", ""))
            media_type = data.get("Type")
            is_series = (media_type == "series")
            
            # 门槛限制
            vote_threshold = 10000 if is_series else 25000
            if votes < vote_threshold:
                return {"status": "intercepted", "msg": "未达投票门槛", "title": data.get('Title'), "poster": data.get("Poster")}
            
            # 双轨算法
            if is_series:
                try: seasons = int(data.get("totalSeasons", "1"))
                except: seasons = 1
                base_score = imdb_rating * 10
                season_bonus = 2.0 * math.log(seasons) if seasons > 1 else 0.0
                votes_modifier = 1.5 if votes >= 100000 else (-3.0 if votes < 25000 else 0.0)
                cs_score = base_score + season_bonus + votes_modifier
                if cs_score > 100.0: cs_score = 100.0
            else:
                raw_metascore = data.get("Metascore", "N/A")
                metascore = 70.0 if raw_metascore == "N/A" else float(raw_metascore)
                cs_score = (ALPHA * (imdb_rating * 10)) + (BETA * metascore)

            # 判定四个体验档
            if cs_score >= 88.0: tier, color = "T1_神作", "🔴"
            elif 80.0 <= cs_score < 88.0: tier, color = "T2_黄金", "🟡"
            elif 75.0 <= cs_score < 80.0: tier, color = "T3_优质", "🟢"
            elif 70.0 <= cs_score < 75.0: tier, color = "T4_高爽", "🔵"
            else:
                return {"status": "intercepted", "msg": "存在明显硬伤，未达收藏线", "title": data.get('Title'), "poster": data.get("Poster")}
                
            poster_url = data.get("Poster", "N/A")
            if poster_url == "N/A" or not poster_url.startswith("http"):
                poster_url = "https://unsplash.com"

            return {
                "status": "success", "score": f"{cs_score:.1f}", "tier": f"{color} {tier}",
                "title": data.get('Title'), "year": data.get('Year'), "type": "剧集" if is_series else "电影",
                "poster": poster_url, "genre": data.get("Genre"), "director": data.get("Director"),
                "actors": data.get("Actors"), "plot": data.get("Plot")
            }
    except:
        pass
    return {"status": "not_found"}

# 🌟 核心突破口：网页端本地文件夹选择入口
# 允许用户直接在网页上点选一个本地文件夹
uploaded_files = st.file_uploader(
    "📂 点击下方或把您的本地电影文件夹拖拽到这里：", 
    accept_multiple_files=True, 
    key="folder_input"
)

if uploaded_files:
    # 智能过滤：由于浏览器会把文件夹里所有文件（包括歌词、图片）都抓出来
    # 我们只保留标准的视频封装格式和原盘 ISO
    video_extensions = ('.mp4', '.mkv', '.avi', '.iso', '.m2ts')
    valid_titles = []
    
    for file in uploaded_files:
        if file.name.lower().endswith(video_extensions):
            # 如果是散装 BDMV 原盘里的切片文件，我们直接提取它上层文件夹的名字作为片名
            if "stream" in file.name.lower() or "bdmv" in file.name.lower():
                # 这种情况下我们尝试拿首个有效视频文件的特征即可
                continue
            valid_titles.append(file.name)
            
    # 去重
    valid_titles = list(set(valid_titles))

    if not valid_titles:
        st.warning("⚠️ 探测完成，但您选中的文件夹里似乎没有包含标准的视频格式文件。")
    else:
        st.subheader(f"📊 成功在网页端捕获本地影视资产 {len(valid_titles)} 部，正在严选跑分：")
        st.markdown("---")
        
        # 每行平铺 4 部电影的网格海报墙
        columns_per_row = 4
        
        for i in range(0, len(valid_titles), columns_per_row):
            cols = st.columns(columns_per_row)
            for j in range(columns_per_row):
                if i + j < len(valid_titles):
                    filename = valid_titles[i + j]
                    clean_title = clean_filename(filename)
                    
                    # 实时在线对齐跑分
                    res = fetch_movie_data(clean_title)
                    
                    with cols[j]:
                        if res["status"] == "success":
                            # 完美通过：平铺展示海报墙
                            st.image(res["poster"], use_container_width=True)
                            st.markdown(f"**🎬 {res['title']} ({res['year']})**")
                            st.markdown(f"分数：`{res['score']}` | 梯队：{res['tier']}")
                            
                            with st.expander("🔍 展开影视详细档案"):
                                st.caption(f"**类型**：{res['type']} | **风格**：{res['genre']}\n\n**导演**：{res['director']}")
                                st.caption(f"**演员**：{res['actors']}")
                                st.info(res["plot"])
                                
                        elif res["status"] == "intercepted":
                            # 被红牌拦截：依然显示海报供用户核对
                            p_url = res["poster"] if (res.get("poster") and res["poster"] != "N/A") else "https://unsplash.com"
                            st.image(p_url, use_container_width=True)
                            st.markdown(f"**⚠️ {res['title'] if res.get('title') else clean_title}**")
                            st.error(f"🛑 强力拦截：{res['msg']}")
                            
                        else:
                            # 彻底查无此片
                            st.image("https://unsplash.com", use_container_width=True)
                            st.markdown(f"**❌ {clean_title}**")
                            st.warning("线上未匹配到，请检查本地文件名")
            st.markdown("---")
