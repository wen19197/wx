import streamlit as st
import re
import json
import os
from collections import Counter

# 存储文件名
STORE_PATH = "stock_data.json"

# —— 持久化工具 —— #
def load_store():
    if os.path.exists(STORE_PATH):
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {name: Counter(cnt) for name, cnt in raw.items()}
    return {}

def save_store(all_lists):
    serial = {name: dict(cnt) for name, cnt in all_lists.items()}
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(serial, f, ensure_ascii=False, indent=2)

# 页面配置
st.set_page_config(page_title="持久化多列表库存 AI 计算器", layout="centered")

# —— 初始化 state —— #
if 'all_lists' not in st.session_state:
    st.session_state.all_lists = load_store()
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

st.title("📦 持久化多列表库存 AI 计算器")

# —— 1. 列表管理 —— #
st.subheader("1️⃣ 选择、创建或删除列表")

def on_select_change():
    st.session_state.current_list = st.session_state.select_choice

options = ["— 新建列表 —"] + list(st.session_state.all_lists.keys())
st.selectbox(
    "请选择要操作的列表",
    options,
    key="select_choice",
    on_change=on_select_change
)

def create_new_list():
    name = st.session_state.new_list_name.strip()
    if not name:
        st.error("❗ 列表名称不能为空")
        return
    if name in st.session_state.all_lists:
        st.error("❗ 列表名已存在")
        return
    st.session_state.history.append({k: cnt.copy() for k,cnt in st.session_state.all_lists.items()})
    st.session_state.all_lists[name] = Counter()
    st.session_state.current_list = name
    st.session_state.select_choice = name
    save_store(st.session_state.all_lists)
    st.success(f"✅ 已创建并切换到列表：{name}")

def delete_current_list():
    name = st.session_state.current_list
    if not name or name not in st.session_state.all_lists:
        st.warning("⚠️ 无效的列表，无法删除")
        return
    st.session_state.history.append({k: cnt.copy() for k,cnt in st.session_state.all_lists.items()})
    st.session_state.all_lists.pop(name)
    save_store(st.session_state.all_lists)
    st.session_state.current_list = None
    st.session_state.select_choice = None
    st.success(f"🗑️ 已删除列表：{name}")

if st.session_state.select_choice == "— 新建列表 —":
    st.text_input("输入新列表名称", key="new_list_name", placeholder="比如 列表1")
    st.button("🆕 创建新列表", on_click=create_new_list)
else:
    # 当选中已有列表时，提供“删除”按钮
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

# —— 2. 核心操作 —— #
def record_history():
    st.session_state.history.append({k: cnt.copy() for k,cnt in st.session_state.all_lists.items()})

def add_to_total():
    text = st.session_state.input_text
    matches = re.findall(r"(\S+)\s*(-?[\d]+(?:\.[\d]+)?)", text)
    if not matches:
        st.warning("❗ 未检测到 code+数量，请检查格式")
        return
    record_history()
    for code, qty in matches:
        counter[code] += float(qty)
    st.session_state.input_text = ""
    save_store(st.session_state.all_lists)
    st.success("✅ 本轮数据已累计")

def clear_all():
    record_history()
    st.session_state.all_lists[current] = Counter()
    save_store(st.session_state.all_lists)
    st.success("🗑️ 已清空当前列表")

def undo():
    if not st.session_state.history:
        st.warning("⚠️ 无可撤回操作")
        return
    st.session_state.all_lists = st.session_state.history.pop()
    save_store(st.session_state.all_lists)
    st.success("⏪ 已撤回上一步")

st.text_area("📋 输入本轮库存列表", key="input_text", height=120,
             placeholder="<code> <数量>，如：ABC-1 3")
c1, c2, c3 = st.columns(3)
with c1:
    st.button("✅ 添加到列表", on_click=add_to_total)
with c2:
    st.button("🗑️ 清空列表", on_click=clear_all)
with c3:
    st.button("⏪ 撤回操作", on_click=undo)

st.markdown("---")

# —— 3. 查询和展示 —— #
st.text_input("🔍 查询 code 数量", key="search_code", placeholder="输入 code")
if st.session_state.search_code:
    code = st.session_state.search_code.strip()
    qty = counter.get(code, 0.0)
    display_q = int(qty) if qty == int(qty) else qty
    st.info(f"Code **{code}** 数量：**{display_q}**")

def sort_key(item):
    code, _ = item
    if re.fullmatch(r'[\d\.]+', code):
        return (0, float(code))
    return (1, code)

if counter:
    st.subheader("📈 列表库存总览")
    rows = []
    for code, qty in sorted(counter.items(), key=sort_key):
        v = int(qty) if qty == int(qty) else qty
        rows.append({"code": code, "quantity": v})
    st.table(rows)
