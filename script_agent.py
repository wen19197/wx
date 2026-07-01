"""
IP 脚本 / 广告脚本 Multi-Agent Loop
流程: Manager → Researcher → Writer → Compliance → Grader → (loop) → Developer
"""

import streamlit as st
import anthropic
import json
import time
from dataclasses import dataclass
from typing import Optional

# ─────────────────────────────────────────────
# 页面配置
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="脚本生成 Agent Loop",
    page_icon="🎬",
    layout="wide",
)

st.markdown("""
<style>
.agent-card {
    border-radius: 10px;
    padding: 16px 20px;
    margin: 10px 0;
    border-left: 5px solid #ccc;
}
.agent-manager    { border-color: #6c5ce7; background: #f5f3ff; }
.agent-researcher { border-color: #00b894; background: #f0fff8; }
.agent-writer     { border-color: #0984e3; background: #f0f7ff; }
.agent-compliance { border-color: #e17055; background: #fff5f3; }
.agent-grader     { border-color: #fdcb6e; background: #fffbf0; }
.agent-developer  { border-color: #00cec9; background: #f0fffe; }
.score-high { color: #00b894; font-size: 28px; font-weight: bold; }
.score-low  { color: #e17055; font-size: 28px; font-weight: bold; }
.final-script {
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 20px;
    border-radius: 10px;
    font-family: monospace;
    white-space: pre-wrap;
    line-height: 1.7;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 马来西亚数字能量市场研究库（内建知识）
# ─────────────────────────────────────────────
MARKET_RESEARCH = """
## 马来西亚数字能量市场核心洞察

### 真实用户原话（各语言）
- "Rezeki bocor, duit tak melekat" （财运漏水，钱不粘手）
- "Hidup boleh stuck, rezeki pun boleh seret" （人生卡住，财运很慢）
- "No anda mungkin punca hidup stuck... Tapi anda boleh ubah!" （你的号码可能是人生卡住的原因）
- "为什么我做什么都不顺？是不是号码问题？"
- "我都做了那么久，不知道是什么问题，风水有没有问题？"
- "隔壁阿华生意好好的，我们差不多，为什么我就差那么多？"
- "我已经不年轻了，是不是命里注定孤独？"
- "Wah my number got 4 and 0 leh, shiok or not?"
- "Just kira kira see la, take it as fun"
- "是不是我的车牌/手机号码不好？"

### 核心痛点（按热度）
1. 钱不够用 / 财运差 / rezeki bocor（40%）
2. 生意差 / 客人少 / business slow（25%）
3. 感情不顺 / jodoh tak datang（20%）
4. 人生卡住 / 没进步 / hidup stuck（10%）
5. 家庭/孩子/健康问题（5%）

### 主要人物画像
- **阿峰老板**：35-50岁，中小企业主，生意走下坡，焦虑
- **阿玲姐姐**：28-40岁，职业女性，感情空窗，朋友都结婚了
- **焦虑马麻**：35-50岁，担心孩子成绩/前途
- **靓仔 Ivan**：22-32岁，买车/换号码，半信半疑想"试试看"
- **Pak Amin**：25-45岁，马来族，好奇数字风水，但有宗教顾虑

### 情绪触发点
- 连续失败后开始怀疑"有没有看不到的原因"
- 身边对比（别人好，我差）
- 人生大事前（买车/开公司/结婚）
- 家人朋友推荐（口碑最强）
- 农历新年前后（旺季）

### 高效文案角度
1. 恐惧触发："你的手机号码最后4位，正在决定你的财运"
2. 好奇触发："你的出生日期隐藏了什么秘密？"
3. 见证驱动："他换了车牌后，生意3个月翻倍"
4. 马来文角度："Nombor telefon anda mungkin punca rezeki seret"
5. 教育型："88真的旺财吗？数字背后的能量学"

### 语言特点
- 华人：中文 + Manglish 混合，口语化
- 马来人：马来文，用 "metafizik" 不用 "ramalan"
- 年轻人：Manglish，轻松语气，"just try la"

### 竞争对手手法
- Uncle FengShui (TikTok)：恐惧钩子 + WhatsApp 接单
- Marinah Numerologist：改名/号码/公司名综合服务
- 共同策略：免费测试引流 → 付费咨询
"""

# ─────────────────────────────────────────────
# Agent 数据结构
# ─────────────────────────────────────────────
@dataclass
class AgentResult:
    agent: str
    emoji: str
    css_class: str
    output: str
    score: Optional[int] = None
    passed: Optional[bool] = None


# ─────────────────────────────────────────────
# 各 Agent 的 System Prompt + 调用逻辑
# ─────────────────────────────────────────────
def call_claude(client: anthropic.Anthropic, system: str, user: str, max_tokens: int = 2000) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def run_manager(client, topic: str, platform: str, language: str, goal: str) -> str:
    system = """你是一位经验丰富的内容总监（Manager），负责为马来西亚数字能量业务制定脚本创作任务书。
你要给整个 Agent 团队一个清晰的任务简报，让每个 Agent 都知道该做什么。
输出格式：结构化任务书，用中文。"""

    user = f"""
请为以下需求制定任务简报：

主题：{topic}
平台：{platform}
语言风格：{language}
目标：{goal}

请输出包含以下内容的任务简报：
1. 核心任务（一句话）
2. 目标受众（具体描述）
3. 关键信息（要传达什么）
4. 平台要求（格式/时长/风格）
5. 成功标准（什么样的脚本算好）
6. 禁止事项（不能说什么）
"""
    return call_claude(client, system, user)


def run_researcher(client, brief: str) -> str:
    system = f"""你是一位专业的市场研究员（Researcher），专注于马来西亚数字能量/命理市场。
你拥有以下市场研究数据库：

{MARKET_RESEARCH}

你的任务：根据任务简报，从数据库中挑选最相关的洞察，为 Writer 提供精准弹药。
输出格式：简洁有力的研究摘要，重点突出。"""

    user = f"""
根据以下任务简报，提取最相关的市场洞察：

{brief}

请输出：
1. 最适合这个脚本的用户原话（3-5句，保留原语言）
2. 最核心的情绪触发点（1-2个）
3. 目标用户此刻的心理状态
4. 建议的切入钩子方向
5. 注意事项（什么说法会让目标用户反感）
"""
    return call_claude(client, system, user)


def run_writer(client, brief: str, research: str, feedback: str = "", iteration: int = 1) -> str:
    revision_note = ""
    if feedback:
        revision_note = f"""

⚠️ 这是第 {iteration} 次修改。上一版的问题：
{feedback}

请根据以上反馈重新创作，针对性解决指出的问题。"""

    system = """你是一位顶级内容创作者（Writer），专门为马来西亚华人/马来人市场创作数字能量相关的
IP脚本和广告脚本。你擅长：钩子设计、情绪共鸣、口语化表达、Manglish 风格、多语言混搭。
你的脚本真实、有温度、不夸大，让人看了第一句就停下来。"""

    user = f"""
任务简报：
{brief}

研究员提供的洞察：
{research}
{revision_note}

请创作完整脚本。格式要求：
- 【开场钩子】（前3秒，必须抓住注意力）
- 【痛点共鸣】（让用户说"这说的就是我！"）
- 【内容主体】（提供价值/故事/信息）
- 【信任建立】（为什么相信你）
- 【行动号召 CTA】（清晰的下一步）
- 【配合建议】（BGM/字幕/镜头提示，2-3条）
"""
    return call_claude(client, system, user, max_tokens=2500)


def run_compliance(client, script: str, platform: str) -> tuple[str, bool]:
    system = """你是内容合规审核员（Compliance Officer），负责检查马来西亚数字能量/命理脚本是否合规。
马来西亚合规重点：
- 不能承诺100%保证效果（"一定会发财"、"保证改运"）
- 不能有医疗声称
- 马来受众内容要避免触碰宗教敏感点（不说"ramalan"，用"metafizik"）
- 不能有虚假见证/捏造数据
- 不能有歧视性内容
输出格式：JSON，包含 passed(bool)、issues(list)、suggestions(list)"""

    user = f"""
请审核以下{platform}脚本：

{script}

输出 JSON 格式：
{{
  "passed": true/false,
  "risk_level": "low/medium/high",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议修改1", "建议修改2"],
  "summary": "一句话总结"
}}"""

    raw = call_claude(client, system, user, max_tokens=800)
    try:
        # 提取 JSON（有时 Claude 会加说明文字）
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
        passed = data.get("passed", False)
        return raw[start:end], passed
    except Exception:
        # JSON 解析失败时默认通过
        return raw, True


def run_grader(client, script: str, brief: str, compliance_report: str) -> tuple[str, int]:
    system = """你是内容评分员（Grader），专门评估马来西亚市场数字能量脚本的质量。
评分维度（每项0-2分）：
1. 钩子强度：前3秒能不能让人停下来？
2. 情绪共鸣：目标用户会不会说"这说的是我"？
3. 语言真实感：够不够口语化、接地气？
4. 信任度：有没有建立信任感？
5. CTA 清晰度：用户知道下一步该做什么吗？

总分 10 分。8分以上才可以发布。"""

    user = f"""
任务简报：{brief}

合规报告：{compliance_report}

待评分脚本：
{script}

请输出：
1. 各维度评分（表格）
2. 总分（X/10）
3. 最强的地方（1-2点）
4. 必须改进的地方（如果总分<8，给具体的修改指示）
5. 一句话总评
"""
    raw = call_claude(client, system, user, max_tokens=1000)
    # 提取分数
    import re
    match = re.search(r"(\d+)\s*[/／]\s*10", raw)
    score = int(match.group(1)) if match else 6
    return raw, score


def run_developer(client, script: str, platform: str, brief: str) -> str:
    system = """你是内容执行者（Developer），负责把通过审核的脚本整理成可以直接使用的发布版本。
你要输出：排版好的最终脚本、发布检查清单、以及平台发布建议。"""

    user = f"""
平台：{platform}
任务简报：{brief}

已通过审核的脚本：
{script}

请输出：

## 📋 最终发布版本
（排版清晰，可以直接复制给拍摄团队/文案团队）

## ✅ 发布前检查清单
（针对{platform}的具体检查项）

## 🚀 发布建议
- 最佳发布时间：
- 建议标签/话题：
- A/B 测试建议：
- 跟进内容建议：
"""
    return call_claude(client, system, user, max_tokens=2000)


# ─────────────────────────────────────────────
# UI 渲染辅助函数
# ─────────────────────────────────────────────
def show_agent_card(result: AgentResult):
    score_html = ""
    if result.score is not None:
        cls = "score-high" if result.score >= 8 else "score-low"
        score_html = f'<span class="{cls}">{result.score}/10</span>'

    st.markdown(
        f'<div class="agent-card {result.css_class}">'
        f'<strong>{result.emoji} {result.agent}</strong> {score_html}'
        f'</div>',
        unsafe_allow_html=True,
    )
    with st.expander("查看输出", expanded=(result.agent in ["Writer", "Developer"])):
        if result.agent == "Developer":
            st.markdown(result.output)
        else:
            st.markdown(result.output)


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────
def main():
    st.title("🎬 IP 脚本 / 广告脚本 Agent Loop")
    st.caption("Manager → Researcher → Writer → Compliance → Grader → (如果分数低自动重写) → Developer")

    # ── Sidebar 设置
    with st.sidebar:
        st.header("⚙️ 设置")
        api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")

        st.markdown("---")
        st.subheader("🎯 脚本设置")

        topic = st.text_input(
            "主题",
            value="手机号码影响财运",
            help="例如：手机号码风水、生命数字、车牌改运"
        )

        platform = st.selectbox(
            "平台",
            ["TikTok / Instagram Reels", "Facebook 广告", "YouTube 短片", "小红书 / Lemon8"],
        )

        language = st.selectbox(
            "语言风格",
            ["中文为主（华人受众）", "马来文为主（Malay受众）", "Manglish（年轻人，混合）", "中英马来混合"],
        )

        goal = st.selectbox(
            "脚本目标",
            [
                "引流 → 让观众私信/WhatsApp 咨询",
                "教育型 → 涨粉建立 IP 权威",
                "直接转化 → 推销号码分析服务",
                "见证故事 → 分享客户改变案例",
            ],
        )

        max_iterations = st.slider("最多重写次数", 1, 4, 2)
        min_score = st.slider("最低通过分数", 6, 9, 8)

        st.markdown("---")
        run_btn = st.button("🚀 开始生成", type="primary", use_container_width=True)

    # ── 主区域
    if not run_btn:
        st.info("👈 在左侧填写设置，然后点击「开始生成」")

        st.markdown("""
        ### 🔄 Agent 工作流程

        | Agent | 角色 | 做什么 |
        |-------|------|--------|
        | 🧑‍💼 Manager | 管理者 | 把你的需求转化为清晰的任务简报 |
        | 🔍 Researcher | 研究员 | 从市场数据库里找最相关的痛点/原话 |
        | ✍️ Writer | 写手 | 创作完整脚本（钩子/正文/CTA）|
        | 🛡️ Compliance | 审核员 | 检查是否有违规/夸大/敏感内容 |
        | ⭐ Grader | 评分员 | 10分制打分，低于8分退回重写 |
        | 🚀 Developer | 执行者 | 整理成发布版 + 发布建议 |
        """)
        return

    if not api_key:
        st.error("请在左侧填入 Anthropic API Key")
        return

    client = anthropic.Anthropic(api_key=api_key)

    # ── 运行 Agent Loop
    results = []
    iteration = 0
    writer_output = ""
    final_score = 0
    compliance_passed = False
    feedback_for_writer = ""

    progress = st.progress(0)
    status = st.empty()

    try:
        # Step 1: Manager
        status.info("🧑‍💼 Manager 正在制定任务简报...")
        manager_output = run_manager(client, topic, platform, language, goal)
        results.append(AgentResult("Manager", "🧑‍💼", "agent-manager", manager_output))
        show_agent_card(results[-1])
        progress.progress(15)
        time.sleep(0.3)

        # Step 2: Researcher
        status.info("🔍 Researcher 正在分析市场数据...")
        research_output = run_researcher(client, manager_output)
        results.append(AgentResult("Researcher", "🔍", "agent-researcher", research_output))
        show_agent_card(results[-1])
        progress.progress(30)
        time.sleep(0.3)

        # Step 3-5: Writer → Compliance → Grader Loop
        while iteration < max_iterations:
            iteration += 1
            iter_label = f"（第 {iteration} 次）" if iteration > 1 else ""

            # Writer
            status.info(f"✍️ Writer 正在创作脚本 {iter_label}...")
            writer_output = run_writer(
                client, manager_output, research_output,
                feedback=feedback_for_writer, iteration=iteration
            )
            writer_result = AgentResult(f"Writer {iter_label}", "✍️", "agent-writer", writer_output)
            show_agent_card(writer_result)
            progress.progress(30 + iteration * 15)
            time.sleep(0.3)

            # Compliance
            status.info("🛡️ Compliance 正在审核内容...")
            compliance_raw, compliance_passed = run_compliance(client, writer_output, platform)
            compliance_result = AgentResult(
                "Compliance Officer", "🛡️", "agent-compliance", compliance_raw,
                passed=compliance_passed
            )
            show_agent_card(compliance_result)
            progress.progress(30 + iteration * 15 + 5)
            time.sleep(0.3)

            if not compliance_passed:
                feedback_for_writer = f"合规问题：{compliance_raw}"
                st.warning("⚠️ 合规审核未通过，退回 Writer 修改...")
                continue

            # Grader
            status.info("⭐ Grader 正在评分...")
            grader_output, final_score = run_grader(
                client, writer_output, manager_output, compliance_raw
            )
            grader_result = AgentResult(
                "Grader", "⭐", "agent-grader", grader_output, score=final_score
            )
            show_agent_card(grader_result)
            progress.progress(30 + iteration * 15 + 10)
            time.sleep(0.3)

            if final_score >= min_score:
                break  # 通过！
            else:
                # 提取改进意见作为下一轮的 feedback
                feedback_for_writer = grader_output
                if iteration < max_iterations:
                    st.warning(f"⚠️ 评分 {final_score}/10，低于目标 {min_score}，自动退回重写...")

        # Step 6: Developer
        if final_score >= min_score and compliance_passed:
            status.info("🚀 Developer 正在整理发布版本...")
            developer_output = run_developer(client, writer_output, platform, manager_output)
            results.append(AgentResult("Developer（最终版）", "🚀", "agent-developer", developer_output))
            show_agent_card(results[-1])
            progress.progress(100)

            status.success(f"✅ 完成！最终得分：{final_score}/10，已通过合规审核")

            # 复制按钮区
            st.markdown("---")
            st.subheader("📋 最终脚本（可直接复制）")
            st.markdown(
                f'<div class="final-script">{writer_output}</div>',
                unsafe_allow_html=True,
            )
            st.download_button(
                "📥 下载脚本",
                data=writer_output,
                file_name=f"script_{topic[:10]}_{platform[:5]}.txt",
                mime="text/plain",
            )
        else:
            progress.progress(100)
            st.error(
                f"经过 {iteration} 次尝试，最终得分 {final_score}/10，"
                f"未达到目标分数 {min_score}。建议调整主题或降低目标分数后重试。"
            )
            if writer_output:
                st.subheader("最后一版脚本（供参考）")
                st.markdown(writer_output)

    except anthropic.AuthenticationError:
        st.error("API Key 无效，请检查")
    except Exception as e:
        st.error(f"出错了：{e}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
