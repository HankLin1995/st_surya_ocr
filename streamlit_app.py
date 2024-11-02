import streamlit as st
import pypdfium2 as pdfium
import os
import json
from groq import Groq
import subprocess

# 初始化一個 session_state 字典來儲存所有設定
if "settings" not in st.session_state:
    st.session_state["settings"] = {
        "groq_api_key": "",
        "postgresql_connection_string": "",
        "synology_c2_bucket_name": "",
        "synology_c2_endpoint_url": "",
        "synology_c2_aws_access_key_id": "",
        "synology_c2_aws_secret_access_key": ""
    }

def get_settings():
    # with st.sidebar.form("settings_form", clear_on_submit=False):
    with st.expander(":pushpin: 參數設定", expanded=False):
        # st.subheader(":loudspeaker: 大語言模型(LLM)")
        GROQ_API_KEY = st.text_input("Groq API Key:", type="password",value=st.session_state["settings"]["groq_api_key"])

        # st.subheader(":cd: 資料庫(SQL)")
        # SQL_CONNECTION_STRING = st.text_input("PostgreSQL 連線字串:", type="password",value=st.session_state["settings"]["postgresql_connection_string"])

        # st.subheader(":file_folder: 物件儲存(Synology C2 Object)")

        # BUCKET_NAME = st.text_input("儲存貯體",value=st.session_state["settings"]["synology_c2_bucket_name"])
        # ENDPOINT_URL = st.text_input("端點",   value=st.session_state["settings"]["synology_c2_endpoint_url"])
        # AWS_ACCESS_KEY_ID = st.text_input("存取金鑰ID", type="password",value=st.session_state["settings"]["synology_c2_aws_access_key_id"])
        # AWS_SECRET_ACCESS_KEY = st.text_input("私密金鑰", type="password",value=st.session_state["settings"]["synology_c2_aws_secret_access_key"])

        # submitted = st.form_submit_button("儲存設定")

        # if submitted:
            # 使用表單輸入值更新 session_state["settings"] 字典中的值
        st.session_state["settings"]["groq_api_key"] = GROQ_API_KEY
        # st.session_state["settings"]["postgresql_connection_string"] = SQL_CONNECTION_STRING
        # st.session_state["settings"]["synology_c2_bucket_name"] = BUCKET_NAME
        # st.session_state["settings"]["synology_c2_endpoint_url"] = ENDPOINT_URL
        # st.session_state["settings"]["synology_c2_aws_access_key_id"] = AWS_ACCESS_KEY_ID
        # st.session_state["settings"]["synology_c2_aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY

            # st.success("設定已儲存!")
# 文件上傳與儲存
def save_uploaded_file(uploaded_file, save_dir="uploaded_files"):
    """儲存上傳的 PDF 文件並返回儲存路徑"""
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# PDF 初始化
def initialize_pdf(file_path):
    """初始化 PDF 文件並返回頁數與圖像"""
    try:
        pdf = pdfium.PdfDocument(file_path)
        total_pages = len(pdf)
        pdf_images = {i: pdf[i].render(scale=2).to_pil() for i in range(total_pages)}
        return total_pages, pdf_images
    except Exception as e:
        st.error(f"Error initializing PDF: {e}")
        return None, None

# 顯示 PDF 頁面
def display_pdf_page(total_pages, pdf_images):
    """顯示當前 PDF 頁面及控制按鈕"""
    if "current_page" not in st.session_state:
        st.session_state.current_page = 0

    current_page = st.session_state.current_page
    if 0 <= current_page < total_pages:
        image_to_show = pdf_images[current_page]
        st.image(image_to_show, caption=f"Page {current_page + 1} of {total_pages}")

# 分頁控制
def pagination_controls(total_pages):
    """建立頁面翻頁的按鈕"""
    col0,col1, col2,col3 = st.columns([1,1, 1,1])
    with col1:
        if st.button(":arrow_up: 往前一頁") and st.session_state.current_page > 0:
            st.session_state.current_page -= 1
    with col2:
        if st.button(":arrow_down: 往後一頁") and st.session_state.current_page < total_pages - 1:
            st.session_state.current_page += 1

def get_text_lines(file_name):
    """Extracts text lines from OCR results."""
    results_file = f"./results/{file_name}/results.json"
    if os.path.exists(results_file):
        with open(results_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        text_lines = []
        for page in data.get(file_name, []):
            for item in page.get("text_lines", []):
                text_lines.append(item.get("text", ""))
        return  "\n".join(text_lines)

@st.cache_data
def get_keywords(combined_text):
    """Sends text to the Groq API and retrieves extracted information."""

    init_text="""
    請幫我將以下文字內容進行梳理，標點符號、文字校正也要做好，結果以繁體中文顯示，僅顯示校正後的內容
    ，不要添加額外的說明或解釋。
"""
    if combined_text!="":
        ai_content = (init_text + "\n" + combined_text)
        client = Groq(api_key=st.session_state["settings"]["groq_api_key"])

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": ai_content}],
            model="llama3-70b-8192",
        )
        return chat_completion.choices[0].message.content

@st.cache_data
def get_keywords2(combined_text):
    """Sends text to the Groq API and retrieves extracted information."""
    init_text = """
    請幫我根據以下文字先進行文字校正後並且擷取出我所需要的訊息並製作成JSON回復，結果需要以繁體中文顯示，不要添加額外的說明或解釋。
    ## 所需要的文字資訊
    * 來文機關
    * 發文日期(OOO年OO月OO日，去掉中華民國)
    * 發文字號
    * 主旨(主旨:~說明:之間的內容)
    ## 公文內容
    """
    if combined_text!="":
        ai_content = (init_text + "\n" + combined_text)
        client = Groq(api_key=st.session_state["settings"]["groq_api_key"])

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": ai_content}],
            model="llama3-70b-8192",
        )

        return chat_completion.choices[0].message.content

def run_ocr(file_path, langs, results_dir):
    """Runs the OCR command using Surya OCR."""
    command = ["surya_ocr", file_path, "--langs", langs, "--results_dir", results_dir]
    try:
        subprocess.run(command, check=True)
        st.sidebar.success("OCR 已執行完成。")
    except subprocess.CalledProcessError as e:
        st.sidebar.error(f"OCR 過程中發生錯誤: {e}")

# 介紹頁面

st.set_page_config(page_title="Surya OCR 公文管理系統", page_icon=":seedling:", layout="wide")

with st.sidebar:
    st.title(":seedling: Surya OCR 公文管理系統")
    st.info("作者: **Hank Lin**")
    st.link_button("Hank's Blog", "https://www.hanksvba.com/", icon="🔗")
    st.markdown("---")

    get_settings()
    
# 主程式流程


st.subheader(":file_folder: 上傳區域")

uploaded_file = st.file_uploader("公文檔案:", type=["pdf"])
langs = "zh"  # OCR 語言代碼，例如 'en', 'zh'

# create folder
if not os.path.exists("./uploaded_files"):
    os.makedirs("./uploaded_files")

file_path = "./uploaded_files/PDF_file.pdf"  # 固定檔名

if uploaded_file is not None:
    # 將上傳的檔案儲存到指定路徑，這會覆蓋舊檔案
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())
    

# OCR Button
if st.sidebar.button("OCR辨識"):
    if not uploaded_file:
        st.error("請上傳PDF檔案。")
    else:
        run_ocr(file_path, langs, "./results")

# st.subheader(":page_facing_up: 辨識區域")

col1,col2=st.columns(2)

with col2:
    st.subheader(":page_facing_up: PDF內容")
    if st.sidebar.button("重新辨識"):
        st.cache_data.clear()  # 清除所有緩存
    if uploaded_file:
        # 儲存檔案並重設頁碼
        file_path = save_uploaded_file(uploaded_file)
        total_pages, pdf_images = initialize_pdf(file_path)

        if total_pages and pdf_images:
            st.session_state.pdf_images = pdf_images
            with st.container(border=True):
                display_pdf_page(total_pages, pdf_images)
                pagination_controls(total_pages)

with col1:
    st.subheader(":old_key: 辨識區域")
    with st.container(border=True,height=920):

        tab1,tab2,tab3=st.tabs(["OCR辨識成果","AI校正後","AI關鍵字擷取"])

        with tab1:
            try:
                st.write(get_text_lines("PDF_file"))
            except:
                st.write("請先進行OCR辨識!")
        with tab2:
            try:
                st.write(get_keywords(get_text_lines("PDF_file")))
            except:
                st.write("請先填寫GroqAPI!")
        with tab3:
            try:
                st.write(get_keywords2(get_text_lines("PDF_file")))
            except:
                st.write("請先填寫GroqAPI!")

