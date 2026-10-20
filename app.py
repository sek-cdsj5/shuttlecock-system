import os
import pandas as pd
import streamlit as st

# 設定網頁版面
st.set_page_config(
    page_title="聖若瑟教區中學第五校 - 踢毽比賽系統",
    page_icon="🏆",
    layout="wide",
)

EXCEL_FILE = "26_27_小學_學生名單_0828.xlsx"
DB_FILE = "shuttlecock_records.csv"


# 1. 智慧讀取全校 32 個班別（完整支援常規班與 ESP 英語部名單）
@st.cache_data
def load_all_students(file_path):
  xls = pd.ExcelFile(file_path)
  students_dict = {}

  for sheet in xls.sheet_names:
    df = pd.read_excel(file_path, sheet_name=sheet)
    class_list = []

    if sheet.startswith("ESP"):
      # 處理 ESP 英語部表格格式
      header_row = None
      for idx, row in df.iterrows():
        if any(
            "No." in str(val) or "Chinese name" in str(val)
            for val in row.astype(str).values
        ):
          header_row = idx
          break
      if header_row is not None:
        df.columns = df.iloc[header_row]
        df_data = df.iloc[header_row + 1 :].copy()
        cols = list(df.columns)
        no_col = next(
            (c for c in cols if c and ("No" in str(c) or "座號" in str(c))), None
        )
        name_col = next(
            (
                c
                for c in cols
                if c and ("Chinese" in str(c) or "姓名" in str(c))
            ),
            None,
        )
        id_col = next(
            (
                c
                for c in cols
                if c
                and (
                    "STRN" in str(c)
                    or "ID" in str(c)
                    or "學生証" in str(c)
                )
            ),
            None,
        )

        if no_col and name_col:
          for _, row in df_data.iterrows():
            seat = str(row.get(no_col, "")).strip()
            name = str(row.get(name_col, "")).strip()
            sid = str(row.get(id_col, "")) if id_col else ""
            sid = sid.strip() if sid != "nan" else ""
            if seat and name and name != "nan" and seat.isdigit():
              class_list.append({"seat": seat, "id": sid, "name": name})
    else:
      # 處理常規班別格式 (1A-6D)
      header_row = None
      for idx, row in df.iterrows():
        if row.astype(str).str.contains("座號").any():
          header_row = idx
          break
      if header_row is not None:
        df.columns = df.iloc[header_row]
        df_data = df.iloc[header_row + 1 :].copy()
        df_data = df_data.dropna(subset=["姓名"])
        for _, row in df_data.iterrows():
          seat = str(row.get("座號", "")).strip()
          sid = str(row.get("學生証ID", "")).strip()
          name = str(row.get("姓名", "")).strip()
          if name and name != "nan":
            class_list.append({"seat": seat, "id": sid, "name": name})

    if class_list:
      students_dict[sheet] = class_list

  return students_dict


students_data = load_all_students(EXCEL_FILE)


# 2. 讀取或初始化成績資料庫
def load_records():
  if os.path.exists(DB_FILE):
    return pd.read_csv(DB_FILE, dtype=str)
  else:
    return pd.DataFrame(
        columns=["班別", "座號", "學生證ID", "姓名", "挑戰次數", "最高紀錄"]
    )


df_records = load_records()

# 3. 使用 query_params 記憶當前頁面模式，防止重新整理時跳頁
query_params = st.query_params
default_mode = query_params.get("mode", "teacher")

st.sidebar.title("🏆 踢毽比賽系統")
mode_selection = st.sidebar.radio(
    "選擇模式",
    ["📝 老師手機記錄後台", "🔥 大螢幕龍虎榜"],
    index=0 if default_mode == "teacher" else 1,
)

if "老師" in mode_selection:
  st.query_params["mode"] = "teacher"
  mode = "teacher"
else:
  st.query_params["mode"] = "leaderboard"
  mode = "leaderboard"

# ==================== 第一部分：老師記錄系統 ====================
if mode == "teacher":
  st.header("📝 體育老師即時記錄系統")
  st.markdown("請選擇班別與座號為學生登記踢毽成績：")

  col1, col2, col3 = st.columns(3)

  with col1:
    selected_class = st.selectbox(
        "選擇班別", [""] + list(students_data.keys())
    )

  selected_seat = ""
  student_info = None
  if selected_class:
    class_students = students_data[selected_class]
    seat_options = [
        f"座號 {s['seat']} - {s['name']}" for s in class_students
    ]
    with col2:
      selected_option = st.selectbox(
          "選擇學生座號", [""] + seat_options
      )
    if selected_option:
      seat_num = selected_option.split(" - ")[0].replace("座號 ", "")
      selected_seat = seat_num
      student_info = next(
          s for s in class_students if s["seat"] == selected_seat
      )

  if student_info:
    st.info(
        f"**學生姓名：** {student_info['name']}  |  **學號 ID：**"
        f" {student_info['id']}"
    )

    existing = df_records[
        (df_records["班別"] == selected_class)
        & (df_records["座號"] == selected_seat)
    ]
    current_attempts = (
        int(existing.iloc[0]["挑戰次數"]) if not existing.empty else 0
    )
    current_best = int(existing.iloc[0]["最高紀錄"]) if not existing.empty else 0

    st.write(
        f"📌 已挑戰次數：**{current_attempts}** 次 | 個人最高紀錄："
        f" **{current_best}** 下"
    )

    score_input = st.number_input(
        "請輸入本次踢毽次數", min_value=0, step=1, value=0
    )

    if st.button("✅ 提交成績", type="primary", use_container_width=True):
      score = int(score_input)
      new_attempts = current_attempts + 1
      new_best = max(current_best, score)

      if not existing.empty:
        df_records.loc[
            (df_records["班別"] == selected_class)
            & (df_records["座號"] == selected_seat),
            ["挑戰次數", "最高紀錄"],
        ] = [str(new_attempts), str(new_best)]
      else:
        new_row = pd.DataFrame([{
            "班別": selected_class,
            "座號": selected_seat,
            "學生證ID": student_info["id"],
            "姓名": student_info["name"],
            "挑戰次數": str(new_attempts),
            "最高紀錄": str(new_best),
        }])
        df_records = pd.concat([df_records, new_row], ignore_index=True)

      df_records.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
      st.success(
          f"成功儲存！{student_info['name']} 本次成績 {score} 下（最高紀錄："
          f" {new_best} 下）"
      )
      st.rerun()

  st.divider()
  st.subheader("📊 成績總覽")
  if not df_records.empty:
    df_sorted = df_records.copy()
    df_sorted["最高紀錄_int"] = df_sorted["最高紀錄"].astype(int)
    df_sorted = df_sorted.sort_values(by="最高紀錄_int", ascending=False).drop(
        columns=["最高紀錄_int"]
    )
    st.dataframe(df_sorted, use_container_width=True)

    csv = df_sorted.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 下載成績 Excel/CSV 檔案",
        data=csv,
        file_name="shuttlecock_scores.csv",
        mime="text/csv",
    )
  else:
    st.info("目前尚無成績紀錄。")


# ==================== 第二部分：大螢幕龍虎榜 ====================
else:
  st.title("🔥 全校踢毽龍虎榜")
  st.markdown("即時顯示全校踢毽高手排名")

  if not df_records.empty:
    df_lb = df_records.copy()
    df_lb["最高紀錄"] = df_lb["最高紀錄"].astype(int)
    df_lb = df_lb.sort_values(by="最高紀錄", ascending=False).reset_index(
        drop=True
    )

    cols = st.columns(3)
    for index, row in df_lb.iterrows():
      if index >= 15:
        break
      col_idx = index % 3
      with cols[col_idx]:
        medal = (
            "🥇"
            if index == 0
            else "🥈" if index == 1 else "🥉" if index == 2 else f"#{index+1}"
        )
        st.markdown(
            f"""
                <div style="background: linear-gradient(135deg, #4f46e5, #9333ea); padding: 20px; border-radius: 15px; color: white; margin-bottom: 15px; box-shadow: 0 10px 15px rgba(0,0,0,0.1);">
                    <h3 style="margin: 0; font-size: 24px;">{medal} {row['姓名']}</h3>
                    <p style="margin: 5px 0 0 0; opacity: 0.8; font-size: 14px;">{row['班別']}班 · 座號 {row['座號']}</p>
                    <div style="font-size: 36px; font-weight: 900; color: #fbbf24; text-align: right; margin-top: -20px;">{row['最高紀錄']} <span style="font-size: 14px; color: white;">下</span></div>
                </div>
            """,
            unsafe_allow_html=True,
        )
  else:
    st.info("等待比賽成績登錄中...")

  # 使用 Streamlit 內建的 st.fragment（或自動 rerun 保持在當前分頁），每 5 秒在背景抓取最新資料更新而不跳頁
  import time

  time.sleep(5)
  st.rerun()
