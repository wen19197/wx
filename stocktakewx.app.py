import streamlit as st
import re
import json
from collections import Counter
from github import Github, InputFileContent

# —— GitHub Gist 配置 —— #
GITHUB_TOKEN = st.secrets["github"]["token"]
GIST_ID      = st.secrets["github"]["gist_id"]  # 初次留空，创建后手动回填
GIST_FILE    = "stock_data.json"

# 登录 GitHub
gh = Github(GITHUB_TOKEN)

def load_from_gist():
    """从 Gist 读取所有列表数据"""
    if not GIST_ID:
        return {}
    try:
        gist = gh.get_gist(GIST_ID)
        content = gist.files[GIST_FILE].content
        return {name: Counter(cnt) for name, cnt in json.loads(content).items()}
    except Exception:
        return {}

def save_to_gist(all_lists):
    """将所有列表数据写入（或创建）Gist"""
    global GIST_ID
    data = json.dumps({name: dict(cnt) for name, cnt in all_lists.items()}, 
                      ensure_ascii=False, indent=2)
    if GIST_ID:
        # 更新已有 Gist
        gist = gh.get_gist(GIST_ID)
        gist.edit(files={GIST_FILE: InputFileContent(data)})
    else:
        # 创建新私有 Gist
        user = gh.get_user()
        gist = user.create_gist(
            public=False,
            files={GIST_FILE: InputFileContent(data)},
            description="Streamlit 库存持久化 Gist"
        )
        GIST_ID = gist.id
        st.success(
            f"🎉 已创建私有 Gist：{GIST_ID}\n"
            "请把它填入 `.streamlit/secrets.toml` 的 gist_id 字段，"
            "然后重新启动应用。"
        )
    return GIST_ID

# —— Streamlit 应用配置 —— #
st.set_page_config(page_title="Gist 持久化多列表库存", layout="centered")
st.title("📦 Gist 持久化多列表库存 AI 计算器")

# —— 1. 初始化 state（从 Gist 加载） —— #
if 'all_lists' not in st.session_state:
    st.session_state.all_lists = load_from_gist()
if 'current_list' not in st.session_state:
    st.session_state.current_list = None
if 'history' not in st.session_state:
    st.session_state.history = []
if 'input_text' not in st.session_state:
    st.session_state.input_text = ""
if 'new_list_name' not in st.session_state:
    st.session_state.new_list_name = ""
if 'select_choice' not in st.session_state:
    st.session_state.select_choice = None
if 'search_code' not in st.session_state:
    st.session_state.search_code = ""

# —— 2. 列表管理 —— #
st.subheader("1️⃣ 选择、创建或删除列表")
def on_select_change():
    st.session_state.current_list = st.session_state.select_choice

options = ["— 新建列表 —"] + list(st.session_state.all_lists.keys())
st.selectbox("请选择列表", options, key="select_choice", on_change=on_select_change)

def create_new_list():
    name = st.session_state.new_list_name.strip()
    if not name:
        st.error("列表名称不能为空")
        return
    if name in st.session_state.all_lists:
        st.error("列表名已存在")
        return
    st.session_state.history.append({
        k: cnt.copy() for k, cnt in st.session_state.all_lists.items()
    })
    st.session_state.all_lists[name] = Counter()
    st.session_state.current_list = name
    st.session_state.select_choice = name
    save_to_gist(st.session_state.all_lists)

def delete_current_list():
    name = st.session_state.current_list
    if not name or name not in st.session_state.all_lists:
        st.warning("无效列表，无法删除")
        return
    st.session_state.history.append({
        k: cnt.copy() for k, cnt in st.session_state.all_lists.items()
    })
    st.session_state.all_lists.pop(name)
    st.session_state.current_list = None
    st.session_state.select_choice = None
    save_to_gist(st.session_state.all_lists)

if st.session_state.select_choice == "— 新建列表 —":
    st.text_input("新建列表名称", key="new_list_name")
    st.button("🆕 创建新列表", on_click=create_new_list)
else:
    if st.session_state.select_choice in st.session_state.all_lists:
        st.button("🗑️ 删除当前列表", on_click=delete_current_list)

# 校验并停止
current = st.session_state.current_list
if current not in st.session_state.all_lists:
    st.info("请先新建或选择一个列表")
    st.stop()

counter = st.session_state.all_lists[current]
st.markdown(f"**当前列表：{current}**   共 {len(counter)} 条记录")
st.markdown("---")

# —— 3. 核心操作 —— #
def record_history():
    st.session_state.history.append({
        k: cnt.copy() for k, cnt in st.session_state.all_lists.items()
    })

def add_to_total():
    text = st.session_state.input_text
    matches = re.findall(r"(\S+)\s*(-?[\d]+(?:\.[\d]+)?)", text)
    if not matches:
        st.warning("格式：<code> <数量>，支持负数")
        return
    record_history()
    for code, qty in matches:
        counter[code] += float(qty)
    st.session_state.input_text = ""
    save_to_gist(st.session_state.all_lists)
    st.success("已累计并保存到 Gist")

def clear_all():
    record_history()
    st.session_state.all_lists[current] = Counter()
    save_to_gist(st.session_state.all_lists)
    st.success("已清空并保存到 Gist")

def undo():
    if not st.session_state.history:
        st.warning("无可撤回操作")
        return
    st.session_state.all_lists = st.session_state.history.pop()
    save_to_gist(st.session_state.all_lists)
    st.success("已撤回并保存到 Gist")

st.text_area("📋 输入本轮库存", key="input_text", height=100)
c1, c2, c3 = st.columns(3)
with c1:
    st.button("✅ 添加到列表", on_click=add_to_total)
with c2:
    st.button("🗑️ 清空列表", on_click=clear_all)
with c3:
    st.button("⏪ 撤回操作", on_click=undo)

st.markdown("---")

# —— 4. 查询与展示 —— #
st.text_input("🔍 查询 code", key="search_code")
if st.session_state.search_code:
    code = st.session_state.search_code.strip()
    qty = counter.get(code, 0.0)
    display = int(qty) if qty == int(qty) else qty
    st.info(f"{code} 的数量：{display}")

def sort_key(item):
    code, _ = item
    return (0, float(code)) if re.fullmatch(r'[\d\.]+', code) else (1, code)

if counter:
    st.subheader("📈 库存总览（智能排序）")
    rows = []
    for code, qty in sorted(counter.items(), key=sort_key):
        v = int(qty) if qty == int(qty) else qty
        rows.append({"code": code, "quantity": v})
    st.table(rows)