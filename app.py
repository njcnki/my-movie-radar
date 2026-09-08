import streamlit as st
import requests
import math

# ==================== 🛠️ 用户配置区 ====================
OMDB_API_KEY = "f22cac4f"  # 你的 8 位免费 Key
ALPHA = 0.7  # 电影算法：大众占比
BETA = 0.3   # 电影算法：专家占比
# =======================================================

# 设置网页标题、图标及高大上的宽屏排版
st.set_page_config(page_title="7:3 影视严选加权雷达", page_icon="🎬", layout="wide")

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
            
            # 提取影视海报网址，若无海报则用占位图
            poster_url = data.get("Poster", "N/A")
            if poster_url == "N/A" or not poster_url.startswith("http"):
                poster_url = "https://unsplash.com"
            
            # 丰富影视基础元数据
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

            # 判定门槛限制
            vote_threshold = 10000 if is_series else 25000
            if votes < vote_threshold:
                return {
                    "status": "intercepted", 
                    "msg": f"🛑 【强力拦截】 该影视未达到有效投票门槛 (当前投票数: {votes:,})",
                    **info_base
                }
            
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
                log_details = f"IMDb: {imdb_rating} ({votes:,} 票) | 总季数: {seasons}季 | 投票基数修正: {votes_modifier:+}"
            
            # 轨道二：标准电影 7:3 严格加权模型
            else:
                raw_metascore = data.get("Metascore", "N/A")
                metascore = 70.0 if raw_metascore == "N/A" else float(raw_metascore)
                cs_score = (ALPHA * (imdb_rating * 10)) + (BETA * metascore)
                log_details = f"IMDb: {imdb_rating} ({votes:,} 票) | Metascore: {raw_metascore}"

            # 统一判定四大梯队
            if cs_score >= 88.0: tier_label, color = "T1_神作", "🔴"
            elif 80.0 <= cs_score < 88.0: tier_label, color = "T2_黄金", "🟡"
            elif 75.0 <= cs_score < 80.0: tier_label, color = "T3_优质", "🟢"
            elif 70.0 <= cs_score < 75.0: tier_label, color = "T4_高爽", "🔵"
            else:
                return {
                    "status": "intercepted", 
                    "msg": f"🛑 【强力拦截】 该影视存在明显硬伤或海外热度不足，未达收藏及格线。 (最终得分: {cs_score:.1f}分)",
                    **info_base
                }
                
            return {
                "status": "success",
                "score": f"{cs_score:.1f}",
                "tier": f"{color} {tier_label}",
                "details": log_details,
                **info_base
            }
    except Exception as e:
        return {"status": "error", "msg": f"❌ 查询失败，网络发生异常: {str(e)}"}
    return {"status": "error", "msg": "❌ 线上未识别到该影片信息，请检查英文名称是否输入正确。"}

# 网页前端输入框
movie_input = st.text_input("请输入您要查询的电影或电视剧名字 (推荐英文名):", key="search_input")

if movie_input:
    with st.spinner("正在连接全网数据池，自适应执行双轨算法脱水..."):
        res = calculate_consensus_score(movie_input.strip())
        
    st.markdown("---")
    
    if res["status"] in ["success", "intercepted"]:
        # 左右分栏：左边海报，右边详细数据面板
        layout_col1, layout_col2 = st.columns([1, 2]) 
        
        with layout_col1:
            st.image(res["poster"], caption=f"《{res['title']}》官方海报", use_container_width=True)
            
        with layout_col2:
            if res["status"] == "success":
                # 顶部核心得分卡片
                card_col1, card_col2 = st.columns(2)
                with card_col1:
                    st.metric(label="📊 最终加权得分", value=f"{res['score']} 分")
                with card_col2:
                    st.metric(label="🏷️ 精准归类梯队", value=res["tier"])
                st.success(f"**影视诊断**：该片已成功通过 7:3 核心算法洗礼，并收入本地数字资产仓储库。")
            else:
                st.error(res["msg"])
            
            # 🎬 丰富影视深度元数据展示面板
            st.markdown("### 🎞️ 影视详细档案")
            
            meta_col1, meta_col2 = st.columns(2)
            with meta_col1:
                st.markdown(f"**🎬 影视中英文名**：{res['title']}")
                st.markdown(f"**📅 上映/首播年份**：{res['year']} ({res['released']})")
                st.markdown(f"**⏳ 影片类型/时长**：{res['genre']} / {res['runtime']}")
            with meta_col2:
                st.markdown(f"**🌍 出品国家/地区**：{res['country']}")
                st.markdown(f"**🎥 导演/主创**：{res['director']}")
                if res['type'] == "电影":
                    st.markdown(f"**💰 院线票房**：{res['boxoffice']}")
                else:
                    st.markdown(f"**📺 影视类别**：电视剧/剧集")
                    
            st.markdown(f"**🎭 核心演员阵容**：{res['actors']}")
            
            # 剧情简介面板
            st.markdown("#### 📝 剧情梗概")
            st.info(res["plot"])
            
            # 算法活数据审计审计
            if res["status"] == "success":
                st.caption(f"🔧 **底层数据链监控**：{res['details']}")
    else:
        st.error(res["msg"])
