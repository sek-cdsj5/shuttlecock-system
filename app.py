import os
import pandas as pd
import streamlit as st

# 設定網頁版面為寬螢幕模式
st.set_page_config(
    page_title="聖若瑟教區中學第五校 - 踢毽比賽系統",
    page_icon="🏆",
    layout="wide",
)

EXCEL_FILE = "26_27_小學_學生名單_0828.xlsx"
DB_FILE = "shuttlecock_records.csv"


# 1. 智慧讀取全校 32 個班別（支援常規班與 ESP 英語部名單）
@st.cache_data
def load_all_students(file_path):
  xls = pd.ExcelFile(file_path)
  students_dict = {}

  for sheet in xls.sheet_names:
    df = pd.read_excel(file_path, sheet_name=sheet)
    class_list = []

    if sheet.startswith("ESP"):
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


# 輔助函數：將班別（如 1A, ESP1A）對應到年級名稱
def get_grade_group(class_name):
  c = str(class_name).upper()
  if "1" in c:
    return "小一"
  elif "2" in c:
    return "小二"
  elif "3" in c:
    return "小三"
  elif "4" in c:
    return "小四"
  elif "5" in c:
    return "小五"
  elif "6" in c:
    return "小六"
  else:
    return "其他"


# 2. 讀取或初始化成績資料庫
def load_records():
  if os.path.exists(DB_FILE):
    return pd.read_csv(DB_FILE, dtype=str)
  else:
    return pd.DataFrame(
        columns=["班別", "座號", "學生證ID", "姓名", "挑戰次數", "最高紀錄"]
    )


df_records = load_records()

# 3. 使用 query_params 記憶當前分頁模式
query_params = st.query_params
default_mode = query_params.get("mode", "teacher")

st.sidebar.title("🏆 踢毽比賽系統")
mode_selection = st.sidebar.radio(
    "選擇模式",
    ["📝 老師手機記錄後台", "🔥 大螢幕全年級龍虎榜"],
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

  col1, col2 = st.columns(2)

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
          "選擇學生座號",
          [""] + seat_options,
          key="selected_student_option",
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

    reset_counter_key = f"reset_cnt_{selected_class}_{selected_seat}"
    if reset_counter_key not in st.session_state:
      st.session_state[reset_counter_key] = 0

    input_key = f"score_input_{selected_class}_{selected_seat}_{st.session_state[reset_counter_key]}"

    score_input = st.number_input(
        "請輸入本次踢毽次數",
        min_value=0,
        step=1,
        value=None,
        placeholder="請輸入數字...",
        key=input_key,
    )

    if st.button("✅ 提交成績", type="primary", use_container_width=True):
      if score_input is None:
        st.warning("⚠️ 請先輸入踢毽次數再提交！")
      else:
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

        st.session_state[reset_counter_key] += 1
        st.rerun()

  st.divider()

  col_title, col_btn1, col_btn2 = st.columns([2, 1, 1])
  with col_title:
    st.subheader("📊 成績總覽與管理")

  if not df_records.empty:
    df_sorted = df_records.copy()
    df_sorted["最高紀錄_int"] = df_sorted["最高紀錄"].astype(int)
    df_sorted = df_sorted.sort_values(by="最高紀錄_int", ascending=False).drop(
        columns=["最高紀錄_int"]
    )

    with col_btn1:
      csv = df_sorted.to_csv(index=False).encode("utf-8-sig")
      st.download_button(
          label="📥 下載 Excel",
          data=csv,
          file_name="shuttlecock_scores.csv",
          mime="text/csv",
          use_container_width=True,
      )

    with col_btn2:
      if "confirm_reset" not in st.session_state:
        st.session_state.confirm_reset = False

      if not st.session_state.confirm_reset:
        if st.button(
            "🗑️ 清除所有記錄", type="secondary", use_container_width=True
        ):
          st.session_state.confirm_reset = True
          st.rerun()
      else:
        st.warning("確定要清空所有成績嗎？")
        c_yes, c_no = st.columns(2)
        with c_yes:
          if st.button("確認清空", type="primary", use_container_width=True):
            if os.path.exists(DB_FILE):
              os.remove(DB_FILE)
            st.session_state.confirm_reset = False
            st.success("已成功清空所有記錄！")
            st.rerun()
        with c_no:
          if st.button("取消", use_container_width=True):
            st.session_state.confirm_reset = False
            st.rerun()

    st.dataframe(df_sorted, use_container_width=True)
  else:
    st.info("目前尚無成績紀錄。")


# ==================== 第二部分：大螢幕全年級同畫面龍虎榜（支援並列同名次） ====================
else:
  st.markdown(
      "<h1 style='text-align: center; color: #4F46E5; font-size: 38px; font-weight:"
      " 900;'>🔥 全校各年級踢毽龍虎榜</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #6B7280; font-size: 16px;' font-weight:"
      " 600;>即時同步展現各年級前三名高手（中文部與英語部合併）</p>",
      unsafe_allow_html=True,
  )

  grades = ["小一", "小二", "小三", "小四", "小五", "小六"]

  if not df_records.empty:
    df_lb = df_records.copy()
    df_lb["最高紀錄"] = df_lb["最高紀錄"].astype(int)
    df_lb["年級組別"] = df_lb["班別"].apply(get_grade_group)

    cols = st.columns(6)

    for i, grade in enumerate(grades):
      with cols[i]:
        st.markdown(
            f"""
                    <div style="background-color: #3730A3; color: #FBBF24; padding: 10px; border-radius: 10px; text-align: center; font-weight: 900; font-size: 20px; margin-bottom: 12px; border: 2px solid #FBBF24;">
                        {grade}組
                    </div>
                """,
            unsafe_allow_html=True,
        )

        df_grade = (
            df_lb[df_lb["年級組別"] == grade]
            .sort_values(by="最高紀錄", ascending=False)
            .reset_index(drop=True)
        )

        if df_grade.empty:
          st.markdown(
              "<div style='text-align:center; color:#9CA3AF;"
              " font-size:14px; padding: 20px 0;'>尚無成績</div>",
              unsafe_allow_html=True,
          )
        else:
          # 計算同分並列名次 (method='min' 讓相同分數獲得相同最小名次)
          df_grade["名次"] = (
              df_grade["最高紀錄"]
              .rank(method="min", ascending=False)
              .astype(int)
          )

          # 只取前 5 個卡片名額展示
          count = 0
          for _, row in df_grade.iterrows():
            if count >= 5:
              break

            rank_num = row["名次"]

            # 根據實際名次給予金、銀、銅卡片樣式
            if rank_num == 1:
              medal = "🥇"
              bg = "linear-gradient(135deg, #F59E0B, #D97706)"  # 金牌背景
            elif rank_num == 2:
              medal = "🥈"
              bg = "linear-gradient(135deg, #9CA3AF, #4B5563)"  # 銀牌背景
            elif rank_num == 3:
              medal = "🥉"
              bg = "linear-gradient(135deg, #D97706, #78350F)"  # 銅牌背景
            else:
              medal = f"{rank_num}."
              bg = "#1F2937"  # 其他名次深色背景

            st.markdown(
                f"""
                        <div style="background: {bg}; padding: 10px 12px; border-radius: 10px; color: white; margin-bottom: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            <div style="font-weight: 800; font-size: 16px;">{medal} {row['姓名']}</div>
                            <div style="font-size: 12px; opacity: 0.85;">{row['班別']}班 ({row['座號']}號)</div>
                            <div style="font-size: 22px; font-weight: 900; color: #FDE047; text-align: right; margin-top: -10px;">
                                {row['最高紀錄']} <span style="font-size: 12px; color: white;">下</span>
                            </div>
                        </div>
                    """,
                unsafe_allow_html=True,
            )
            count += 1
  else:
    st.info("等待比賽成績登錄中...")

  import time

  time.sleep(5)
  st.rerun()
