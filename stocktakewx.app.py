import streamlit as st
import re
import json
from collections import Counter
from github import Github, InputFileContent

# —— Streamlit & GitHub Gist 配置 —— #
GITHUB_TOKEN_KEY = "github.token"
GITHUB_GIST_KEY  = "github.gist_id"
GIST_FILE        = "stock_data.json"

def get_github_client():
    token = st.secrets["github"]["token"]
    return Github(token)

def load_from_gist():
    """动态读取最新的 Gist ID 并加载数据"""
    gist_id = st.secrets["github"]["gist_id"]
    if not gist_id:
        return {}
    gh = get_github_client()
    try:
        gist = gh.get_gist(gist_id)
        content = gist.files[GIST_FILE].content
        return {name: Counter(cnt) for name, cnt in json.loads(content).items()}
    except Exception:
        return {}

def save_to_gist(all_lists):
    """
    动态读取最新 Gist ID；
    如果存在则更新，否则创建新私有 Gist 并提示用户回填；
    """
    gist_id = st.secrets["github"]["gist_id"]
    gh = get_github_client()
    data = json.dumps({n: dict(c) for n, c in all_lists.items()},
                      ensure_ascii=False, indent=2)

    # 如果已经填写了 Gist ID，就尝试更新
    if gist_id:
        try:
            gist = gh.get_gist(gist_id)
            gist.edit(files={GIST_FILE: InputFileContent(data)})
            return gist_id
        except Exception:
            # 如果更新失败（ID 不存在/权限问题），继续走创建流程
            pass

    # 创建新的私有 Gist
    gist = gh.get_user().create_gist(
        public=False,
        files={GIST_FILE: InputFileContent(data)},
        description="Streamlit 库存持久化 Gist"
    )
    new_id = gist.id
    st.success(
        f"🎉 已创建新私有 Gist：{new_id}\n"
        "请把它填入 `.streamlit/secrets.toml`（或 Cloud Secrets）的 "
        f"`{GITHUB_GIST_KEY}` 字段，然后重新启动应用。"
    )
    return new_id

# —— Streamlit 应用主体 —— #
st.set_page_config(page_title="Gist 持久化多列表库存", layout="centered")
st.title("📦 Gist 持久化多列表库存 AI 计算器")

# — 1. 初始化 state — #
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

# — 2. 列表管理 — #
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
    # 保存到 Gist（此时若无 Gist ID，将触发创建）
    new_id = save_to_gist(st.session_state.all_lists)

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

current = st.session_state.current_list
if current not in st.session_state.all_lists:
    st.info("请先新建或选择一个列表")
    st.stop()

counter = st.session_state.all_lists[current]
st.markdown(f"**当前列表：{current}**   共 {len(counter)} 条记录")
st.markdown("---")

# — 3. 核心操作 — #
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

# — 4. 查询与展示 — #
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