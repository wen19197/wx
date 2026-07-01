"""
马来西亚数字能量市场调研 AI Agent
抓取马来西亚各大社交平台 → Claude 分析 → 输出痛点/原话/人物画像
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import time
import urllib.parse
import re
from datetime import datetime
from typing import List, Dict, Optional
import anthropic

# ─────────────────────────────────────────────
# 页面设置
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🔍 马来西亚市场调研 Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; padding: 16px; border-radius: 10px; margin: 6px 0;
}
.quote-card {
    background: #fff8f0; border-left: 4px solid #ff6b35;
    padding: 12px 16px; margin: 8px 0; border-radius: 6px;
    font-style: italic;
}
.pain-chip {
    display: inline-block; background: #fff3cd;
    border: 1px solid #ffc107; padding: 4px 12px;
    border-radius: 20px; margin: 4px; font-size: 14px;
}
.persona-box {
    background: #f0f7ff; border: 1px solid #b3d4f7;
    padding: 16px; border-radius: 10px; margin: 10px 0;
}
.source-badge {
    display: inline-block; background: #e8f5e9;
    border: 1px solid #81c784; padding: 2px 8px;
    border-radius: 12px; font-size: 12px; color: #2e7d32;
}
section[data-testid="stSidebar"] { background: #f8f9ff; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 马来西亚数字命理 关键词库
# ─────────────────────────────────────────────
SEED_KEYWORDS = {
    "中文": [
        "数字命理", "生命数字", "数字能量", "号码风水", "幸运数字",
        "手机号码风水", "车牌号码风水", "姓名数字", "财运数字",
        "数字算命", "生命灵数", "数字解析", "出生日期数字",
        "数字能量 马来西亚", "数字命理 吉隆坡",
    ],
    "英文/Manglish": [
        "numerology malaysia", "lucky number malaysia", "life path number",
        "numerology reading kl", "number feng shui", "lucky car plate malaysia",
        "phone number lucky malaysia", "numerology consultant malaysia",
    ],
    "马来文": [
        "nombor nasib", "numerologi malaysia", "nombor bertuah",
        "feng shui nombor", "nombor tuah", "ramalan nombor",
        "tarikh lahir nombor nasib",
    ],
}

# 痛点关键词（用于在抓取内容中识别相关内容）
PAIN_KEYWORDS = [
    "财运", "钱", "生意", "感情", "婚姻", "健康", "工作", "事业",
    "不顺", "难", "问题", "烦", "怎么办", "如何", "为什么",
    "rezeki", "duit", "masalah", "jodoh", "susah", "tak ada",
    "money", "business", "relationship", "problem", "bad luck",
    "how to", "why", "help",
]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ms;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ─────────────────────────────────────────────
# 数据采集模块
# ─────────────────────────────────────────────

def safe_get(url: str, headers: dict = BROWSER_HEADERS, timeout: int = 12) -> Optional[requests.Response]:
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp
    except Exception as e:
        return None


def scrape_google_suggestions(keywords: List[str]) -> List[Dict]:
    """Google 自动补全 → 了解用户真实搜索意图"""
    results = []
    for kw in keywords:
        url = (
            f"https://suggestqueries.google.com/complete/search"
            f"?client=chrome&q={urllib.parse.quote(kw)}&hl=zh-CN&gl=MY"
        )
        resp = safe_get(url, headers={"User-Agent": "Mozilla/5.0"})
        if resp:
            try:
                suggestions = json.loads(resp.text)[1]
                for s in suggestions:
                    results.append({
                        "source": "Google 搜索建议",
                        "type": "search_intent",
                        "seed": kw,
                        "text": s,
                        "url": f"https://www.google.com/search?q={urllib.parse.quote(s)}&gl=MY",
                    })
            except Exception:
                pass
        time.sleep(0.3)
    return results


def scrape_reddit_malaysia(keywords: List[str]) -> List[Dict]:
    """Reddit r/malaysia、r/boleh 社区讨论"""
    results = []
    subreddits = ["malaysia", "boleh", "MalaysiaForum"]
    reddit_headers = {"User-Agent": "MarketResearchBot/1.0 (research purposes)"}
    for sub in subreddits:
        for kw in keywords[:5]:  # 每个版限搜5个词，避免过多请求
            url = (
                f"https://www.reddit.com/r/{sub}/search.json"
                f"?q={urllib.parse.quote(kw)}&sort=top&limit=8&t=year"
            )
            resp = safe_get(url, headers=reddit_headers)
            if resp:
                try:
                    data = resp.json()
                    for post in data.get("data", {}).get("children", []):
                        p = post.get("data", {})
                        title = p.get("title", "")
                        body = p.get("selftext", "")
                        if not body and not title:
                            continue
                        results.append({
                            "source": f"Reddit r/{sub}",
                            "type": "forum_post",
                            "text": f"{title}\n{body}".strip()[:800],
                            "url": f"https://reddit.com{p.get('permalink', '')}",
                            "score": p.get("score", 0),
                            "keyword": kw,
                        })
                except Exception:
                    pass
            time.sleep(0.8)
    return results


def scrape_lowyat(keywords: List[str]) -> List[Dict]:
    """Lowyat.net 马来西亚华人科技论坛（含生活区）"""
    results = []
    for kw in keywords[:4]:
        url = f"https://forum.lowyat.net/search?q={urllib.parse.quote(kw)}"
        resp = safe_get(url)
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            # 搜索结果行
            for row in soup.select(".searchtable tr, .topic_title, h3.topic_title")[:10]:
                text = row.get_text(strip=True)
                if len(text) > 20:
                    results.append({
                        "source": "Lowyat.net 论坛",
                        "type": "forum_post",
                        "text": text[:500],
                        "keyword": kw,
                    })
        time.sleep(1)
    return results


def scrape_youtube_search(keywords: List[str]) -> List[Dict]:
    """YouTube 搜索结果 — 视频标题 + 描述（反映内容需求）"""
    results = []
    for kw in keywords[:4]:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(kw + ' malaysia')}"
        resp = safe_get(url)
        if resp:
            # YouTube 把数据存在 var ytInitialData JSON 里
            match = re.search(r"var ytInitialData = ({.*?});</script>", resp.text, re.S)
            if match:
                try:
                    yt_data = json.loads(match.group(1))
                    contents = (
                        yt_data.get("contents", {})
                        .get("twoColumnSearchResultsRenderer", {})
                        .get("primaryContents", {})
                        .get("sectionListRenderer", {})
                        .get("contents", [])
                    )
                    for section in contents:
                        items = (
                            section.get("itemSectionRenderer", {})
                            .get("contents", [])
                        )
                        for item in items:
                            vr = item.get("videoRenderer", {})
                            title_runs = vr.get("title", {}).get("runs", [])
                            desc_runs = (
                                vr.get("detailedMetadataSnippets", [{}])[0]
                                .get("snippetText", {})
                                .get("runs", [])
                                if vr.get("detailedMetadataSnippets") else []
                            )
                            title = "".join(r.get("text", "") for r in title_runs)
                            desc = "".join(r.get("text", "") for r in desc_runs)
                            if title:
                                results.append({
                                    "source": "YouTube 搜索",
                                    "type": "video_title",
                                    "text": f"{title}\n{desc}".strip()[:400],
                                    "keyword": kw,
                                })
                except Exception:
                    pass
        time.sleep(1.5)
    return results


def scrape_google_paa(keywords: List[str]) -> List[Dict]:
    """Google 的 People Also Ask（用户常问问题）"""
    results = []
    for kw in keywords[:3]:
        url = (
            "https://www.google.com/search"
            f"?q={urllib.parse.quote(kw)}&gl=MY&hl=zh-CN&num=10"
        )
        resp = safe_get(url)
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            # PAA 问题通常在 data-q 或 aria-label
            for q in soup.select("[data-q], .related-question-pair"):
                text = q.get("data-q") or q.get_text(strip=True)
                if text and len(text) > 10:
                    results.append({
                        "source": "Google PAA（相关问题）",
                        "type": "user_question",
                        "text": text[:300],
                        "keyword": kw,
                    })
            # 搜索结果摘要
            for snippet in soup.select(".VwiC3b, .s3v9rd, .IsZvec")[:8]:
                text = snippet.get_text(strip=True)
                if text and len(text) > 30:
                    results.append({
                        "source": "Google 搜索摘要",
                        "type": "search_snippet",
                        "text": text[:400],
                        "keyword": kw,
                    })
        time.sleep(2)
    return results


def scrape_facebook_ads_library(keywords: List[str]) -> List[Dict]:
    """Facebook 广告库 — 了解竞争对手文案"""
    results = []
    for kw in keywords[:3]:
        url = (
            "https://www.facebook.com/ads/library/"
            f"?active_status=all&ad_type=all&country=MY"
            f"&q={urllib.parse.quote(kw)}&search_type=keyword_unordered"
        )
        resp = safe_get(url)
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            # FB 广告库内容大多是 JS 渲染，这里提取静态部分
            for div in soup.select("[data-testid], .x1n2onr6")[:10]:
                text = div.get_text(strip=True)
                if 20 < len(text) < 600:
                    results.append({
                        "source": "Facebook 广告库",
                        "type": "competitor_ad",
                        "text": text,
                        "keyword": kw,
                        "url": url,
                    })
        time.sleep(2)
    return results


# ─────────────────────────────────────────────
# Claude AI 分析引擎
# ─────────────────────────────────────────────

ANALYSIS_PROMPT = """你是一位专注于马来西亚市场的市场调研专家，精通中文、英文、马来文和 Manglish。

## 研究主题
{topic}

## 原始数据（来自马来西亚各大社交平台/搜索引擎）
共 {count} 条数据：

{raw_data}

---

请根据以上数据，提供深度市场洞察报告。

## 输出格式（请严格按以下结构）

### 📣 一、原话金句 (Verbatim Quotes)
列出 8-12 句最能代表用户心声的原话，**保留原语言（中/英/马来文/Manglish）**，不要翻译。
格式：
> "原话内容" — [来源平台]

### 😩 二、核心痛点 TOP 10
用用户自己的语言来描述痛点（不是你帮他们翻译或优化）。
格式：
1. **痛点标题** — 具体表现（用户怎么说的）

### 👤 三、人物画像 (Personas)
描述 4-5 个不同的潜在客户画像：
**画像名称**（例如：担忧财运的阿明）
- 年龄/背景：
- 面对的问题：
- 情绪状态：
- 他们会搜索什么：
- 他们用什么语言表达：（给几个例句）
- 他们的决策触发点：

### 🔥 四、情绪触发点
什么情境让他们开始寻求数字能量/命理帮助？列出最强的 5 个触发场景。

### 💬 五、语言模式分析
**他们常用的句式/词汇：**
- 中文常用词：
- 英文/Manglish 常用词：
- 马来文常用词：
- 常见问句模式：（"为什么我的...?"、"如何改善...?"、"我的...号码好不好?" 等）

### 📊 六、问题类别占比（估算）
财运/钱/生意、感情/婚姻、健康、事业/工作、家庭/子女、性格/人际 — 各占多少百分比？

### ✍️ 七、文案方向建议
基于以上分析，提供 5 个具体的广告文案/内容方向，包括：
- **切入角度**：
- **示例文案**（用目标客户的语言）：
- **适合的平台**：

### 🏪 八、竞争格局观察
从收集到的数据中，观察到什么竞争态势？竞争对手在用什么角度？

请用简体/繁体中文回答（原话摘录保留原语言）。重点是真实感和实用性。"""


def run_claude_analysis(raw_data: List[Dict], topic: str, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)

    # 格式化原始数据
    formatted = []
    for i, item in enumerate(raw_data[:60], 1):
        source = item.get("source", "未知")
        text = item.get("text", "").strip()
        if text:
            formatted.append(f"[{i}] 【{source}】\n{text}")

    raw_text = "\n\n".join(formatted)

    prompt = ANALYSIS_PROMPT.format(
        topic=topic,
        count=len(formatted),
        raw_data=raw_text,
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=5000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def run_quick_persona(topic: str, api_key: str) -> str:
    """快速生成目标人物画像（不需要抓取数据）"""
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""你是马来西亚{topic}市场专家。

根据你对马来西亚市场的了解，直接描述潜在客户会用什么语言表达他们的痛点。

马来西亚是多元种族社会（马来人、华人、印度人），语言混杂（中文/英文/马来文/Manglish）。

请提供：
1. **华人客户** 会怎么表达他们的痛点（给10个真实例句）
2. **马来客户** 会怎么表达（给5个例句）
3. **年轻人（80、90后）** 的表达方式（Manglish/混合语）
4. **他们最关心的5大问题**（按优先级）
5. **最常搜索的关键词**（中/英/马来文各5个）

重要：请给出真实感强的例句，像真人在 WhatsApp 群发消息或在 Facebook 评论的那种语气。"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ─────────────────────────────────────────────
# Streamlit UI
# ─────────────────────────────────────────────

def render_sidebar():
    st.sidebar.title("⚙️ 调研设置")

    api_key = st.sidebar.text_input(
        "Anthropic API Key",
        type="password",
        help="在 console.anthropic.com 获取 API Key",
        placeholder="sk-ant-...",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("📡 数据源选择")

    sources = {
        "google_suggest": st.sidebar.checkbox("Google 搜索建议", value=True),
        "google_paa": st.sidebar.checkbox("Google 相关问题(PAA)", value=True),
        "reddit": st.sidebar.checkbox("Reddit 马来西亚社区", value=True),
        "youtube": st.sidebar.checkbox("YouTube 搜索结果", value=True),
        "lowyat": st.sidebar.checkbox("Lowyat.net 论坛", value=False),
        "fb_ads": st.sidebar.checkbox("Facebook 广告库（竞品）", value=False),
    }

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 关键词语言")
    lang_filter = st.sidebar.multiselect(
        "包含哪些语言的关键词？",
        ["中文", "英文/Manglish", "马来文"],
        default=["中文", "英文/Manglish"],
    )

    return api_key, sources, lang_filter


def collect_data(topic: str, sources: Dict, lang_filter: List[str]) -> List[Dict]:
    # 根据语言筛选关键词
    keywords = []
    for lang in lang_filter:
        keywords.extend(SEED_KEYWORDS.get(lang, []))

    # 加入用户自定义的 topic 作为关键词
    keywords = [topic] + keywords

    all_data = []
    progress = st.progress(0)
    status = st.empty()

    steps = []
    if sources.get("google_suggest"):
        steps.append(("Google 搜索建议", lambda: scrape_google_suggestions(keywords[:10])))
    if sources.get("google_paa"):
        steps.append(("Google PAA 问题", lambda: scrape_google_paa(keywords[:4])))
    if sources.get("reddit"):
        steps.append(("Reddit 马来西亚", lambda: scrape_reddit_malaysia(keywords[:6])))
    if sources.get("youtube"):
        steps.append(("YouTube 搜索", lambda: scrape_youtube_search(keywords[:4])))
    if sources.get("lowyat"):
        steps.append(("Lowyat 论坛", lambda: scrape_lowyat(keywords[:4])))
    if sources.get("fb_ads"):
        steps.append(("Facebook 广告库", lambda: scrape_facebook_ads_library(keywords[:3])))

    for i, (name, fn) in enumerate(steps):
        status.info(f"📡 正在抓取 {name}...")
        try:
            data = fn()
            all_data.extend(data)
            st.sidebar.success(f"✅ {name}: {len(data)} 条")
        except Exception as e:
            st.sidebar.warning(f"⚠️ {name} 出错: {str(e)[:50]}")
        progress.progress((i + 1) / len(steps))

    status.success(f"✅ 数据采集完成，共 {len(all_data)} 条原始数据")
    return all_data


def display_raw_data(data: List[Dict]):
    st.subheader(f"📦 原始数据预览（{len(data)} 条）")

    # 按来源分组
    by_source: Dict[str, List] = {}
    for item in data:
        src = item.get("source", "其他")
        by_source.setdefault(src, []).append(item)

    cols = st.columns(len(by_source) or 1)
    for i, (src, items) in enumerate(by_source.items()):
        with cols[i % len(cols)]:
            st.metric(src, f"{len(items)} 条")

    with st.expander("查看原始数据样本（前20条）"):
        for item in data[:20]:
            src = item.get("source", "")
            text = item.get("text", "")
            st.markdown(
                f'<div class="quote-card">'
                f'<span class="source-badge">{src}</span><br><br>'
                f"{text}</div>",
                unsafe_allow_html=True,
            )


def display_analysis(analysis_text: str):
    st.markdown("---")
    st.subheader("🧠 AI 深度分析报告")

    # 整体输出（带格式）
    st.markdown(analysis_text)

    # 导出按钮
    st.download_button(
        label="📥 下载完整报告（Markdown）",
        data=analysis_text,
        file_name=f"market_research_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
    )


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────

def main():
    st.title("🔍 马来西亚市场调研 AI Agent")
    st.caption("数字能量 / 命理 / 风水 — 挖掘真实市场痛点与用户原话")

    api_key, sources, lang_filter = render_sidebar()

    # ── 快速洞察（不需要抓取，直接 Claude 分析）
    st.header("⚡ 快速市场洞察")
    st.info(
        "**快速模式**：直接让 Claude 根据对马来西亚市场的了解，"
        "生成目标客户的原话和语言模式（无需等待数据抓取）"
    )

    topic_quick = st.text_input(
        "研究主题",
        value="数字能量 / 数字命理",
        help="例如：数字命理、生命数字、号码风水",
    )

    col1, col2 = st.columns(2)
    with col1:
        btn_quick = st.button("⚡ 快速生成语言洞察", type="primary", use_container_width=True)
    with col2:
        btn_full = st.button("🔬 完整调研（抓取+分析）", use_container_width=True)

    if btn_quick:
        if not api_key:
            st.error("请在左侧填入 Anthropic API Key")
            st.stop()
        with st.spinner("Claude 正在分析马来西亚市场..."):
            try:
                result = run_quick_persona(topic_quick, api_key)
                st.success("✅ 完成！")
                st.markdown("---")
                st.subheader("💬 目标客户语言洞察")
                st.markdown(result)
                st.download_button(
                    "📥 下载洞察报告",
                    data=result,
                    file_name=f"quick_insight_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown",
                )
            except anthropic.AuthenticationError:
                st.error("API Key 无效，请检查")
            except Exception as e:
                st.error(f"分析出错：{e}")

    if btn_full:
        if not api_key:
            st.error("请在左侧填入 Anthropic API Key")
            st.stop()

        st.markdown("---")
        st.header("📡 Step 1 — 多平台数据采集")
        with st.spinner("正在从各平台抓取数据..."):
            all_data = collect_data(topic_quick, sources, lang_filter)

        if not all_data:
            st.warning("没有抓取到数据，请检查网络或换一个关键词重试")
            st.stop()

        display_raw_data(all_data)

        st.markdown("---")
        st.header("🧠 Step 2 — Claude AI 深度分析")
        with st.spinner("Claude 正在分析原始数据，提取痛点与人物画像..."):
            try:
                analysis = run_claude_analysis(all_data, topic_quick, api_key)
                st.success("✅ 分析完成！")
                display_analysis(analysis)
            except anthropic.AuthenticationError:
                st.error("API Key 无效，请检查")
            except Exception as e:
                st.error(f"分析出错：{e}")

    # ── 使用说明
    with st.expander("📖 使用说明 & 数据源说明"):
        st.markdown("""
### 各数据源说明

| 数据源 | 内容 | 语言 |
|--------|------|------|
| Google 搜索建议 | 用户真实搜索词，反映搜索意图 | 中/英/马来文 |
| Google PAA | 用户最常问的问题 | 多语言 |
| Reddit r/malaysia | 马来西亚人的英文讨论 | 英文/Manglish |
| YouTube 搜索 | 热门视频标题（反映需求） | 多语言 |
| Lowyat.net | 马来西亚最大华人论坛 | 中/英文 |
| Facebook 广告库 | 竞争对手的广告文案 | 多语言 |

### ChatGPT 能不能研究？
ChatGPT 是封闭系统，无法直接抓取用户数据。但可以：
- 通过 **Google 搜索建议** 看人们在问什么
- 通过 **Reddit/论坛** 看他们的真实讨论
- 通过 **Facebook 广告库** 看竞争对手在投放什么

### 建议工作流
1. 先用 **⚡ 快速模式** 了解语言模式
2. 再用 **🔬 完整调研** 深挖真实市场数据
3. 把报告导入 Notion / Google Docs 持续维护
        """)


if __name__ == "__main__":
    main()
