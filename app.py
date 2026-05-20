import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import io
import json
import zipfile
import google.generativeai as genai

# --- 1. 페이지 설정 및 디자인 (Warm Minimalism) ---
st.set_page_config(page_title="PTI-byFFKM", page_icon="📝", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #FFFFFF; color: #333333; }
    .title-text { font-family: 'Helvetica Neue', Arial, sans-serif; color: #333333; font-weight: 200; letter-spacing: -1px; }
    .subtitle-text { color: #8E8E8E; font-size: 1.1rem; margin-bottom: 2rem; }
    .stFileUploader { background-color: #FAF9F6; padding: 20px; border-radius: 10px; border: 1px dashed #E0DED7; }
    /* 문항 카드 스타일 */
    .crop-card { border: 1px solid #E0DED7; padding: 15px; border-radius: 8px; background-color: #FAF9F6; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 사이드바 구성 ---
with st.sidebar:
    st.markdown("<h2 class='title-text'>PTI-byFFKM</h2>", unsafe_allow_html=True)
    st.info("PDF TO IMAGE by Far Famed KM")
    st.divider()
    
    # AI 각개격파 가동을 위한 API Key 입력창
    api_key = st.text_input("Gemini API Key를 입력하세요", type="password")
    st.divider()
    
    layout_option = st.radio("레이아웃 선택", ["1단 구성", "2단 구성"], index=1)
    numbering_option = st.radio("문항 번호 체계", ["오름차순형", "페이지+번호 혼합형"])

# --- 3. 메인 화면 구성 ---
st.markdown("<h1 class='title-text'>PTI-byFFKM</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-text'>수학 학습 자료 자동화 커팅 시스템 (교재용 AI 좌우 각개격파 모드)</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type="pdf")

if uploaded_file is not None:
    pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    total_pages = len(pdf_document)
    st.success(f"총 {total_pages}페이지의 PDF가 성공적으로 로드되었습니다.")
    
    # 1페이지 렌더링 (대표 미리보기용)
    preview_page = pdf_document.load_page(0)
    preview_pix = preview_page.get_pixmap(matrix=fitz.Matrix(2, 2))
    preview_img_data = preview_pix.tobytes("png")
    base_img = Image.open(io.BytesIO(preview_img_data))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("원본 1페이지 미리보기")
        st.image(base_img, use_container_width=True)
        
    with col2:
        st.subheader("참고서 맞춤형 AI 자동 컷팅 및 다운로드")
        st.write(f"ℹ️ [각개격파 자르기] 버튼을 누르면 AI가 각 페이지의 좌/우 열을 분리하여 문항 수에 상관없이 정밀 추적합니다.")
        
        if not api_key:
            st.warning("👈 왼쪽 사이드바에 Gemini API Key를 입력하시면 초정밀 AI 각개격파 커팅을 시작할 수 있습니다.")
        else:
            if st.button("✂️ AI 좌우 각개격파 초정밀 분할 시작"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
                    
                    # 1단 세로 이미지 분석을 위한 정밀 최적화 프롬프트
                    prompt = """
                    이 이미지는 2단 구성 수학 교재에서 딱 하나의 열(Column)만 세로로 길쭉하게 잘라낸 이미지야.
                    위에서부터 아래로 배정된 개별 수학 문제(문항 번호, 본문 지문, 수식, 그래프 조건, 보기 1~5번 전체 포함)의 영역들을 순서대로 모두 찾아줘.
                    
                    [필수 주의사항]
                    수식의 분수식, 지수, 아래첨자나 보기가 단 1mm도 잘리지 않도록 사방 영역(특히 ymin과 ymax)을 아주 문맥상 넉넉하게 잡아야 해.
                    
                    반드시 아래와 같은 JSON 배열 형식으로만 응답해. 다른 텍스트는 절대 금지야.
                    [ {"box_2d": [ymin, xmin, ymax, xmax], "label": "문제 번호"} ]
                    좌표는 0에서 1000 사이로 정규화된 값이어야 해.
                    """
                    
                    all_cropped_images = []
                    global_question_count = 1
                    
                    # --- 🔄 비용 절감 및 테스트용 최대 5페이지 브레이크 장치 장착! ---
                    run_pages = min(5, total_pages)
                    
                    for page_idx in range(run_pages):
                        status_text.text(f"⏳ {page_idx + 1} / {run_pages} 페이지 AI 각개격파 분사 중...")
                        
                        page = pdf_document.load_page(page_idx)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        page_img = Image.open(io.BytesIO(pix.tobytes("png")))
                        width, height = page_img.size
                        
                        center_line = width // 2
                        
                        # 수학적으로 좌/우 단면을 깔끔하게 크롭
                        left_col_img = page_img.crop((0, 0, center_line, height))
                        right_col_img = page_img.crop((center_line, 0, width, height))
                        
                        columns_data = [
                            {"img": left_col_img, "type": "LEFT"},
                            {"img": right_col_img, "type": "RIGHT"}
                        ]
                        
                        # 쪼개진 단면을 AI에게 하나씩 던져서 순수 세로 정렬 분석
                        for col in columns_data:
                            try:
                                response = model.generate_content([prompt, col["img"]], generation_config={"response_mime_type": "application/json"})
                                result_json = json.loads(response.text)
                                
                                # 상단 정렬순으로 1차 정렬
                                result_json.sort(key=lambda x: x["box_2d"][0])
                                
                                for item in result_json:
                                    box = item["box_2d"]
                                    ymin, xmin, ymax, xmax = box[0], box[1], box[2], box[3]
                                    
                                    # 상대 좌표를 전체 원본 페이지 픽셀 좌표로 역환산
                                    if col["type"] == "LEFT":
                                        abs_ymin = int((ymin / 1000) * height)
                                        abs_xmin = int((xmin / 1000) * center_line)
                                        abs_ymax = int((ymax / 1000) * height)
                                        abs_xmax = int((xmax / 1000) * center_line)
                                    else:
                                        abs_ymin = int((ymin / 1000) * height)
                                        abs_xmin = int((xmin / 1000) * (width - center_line)) + center_line
                                        abs_ymax = int((ymax / 1000) * height)
                                        abs_xmax = int((xmax / 1000) * (width - center_line)) + center_line
                                    
                                    # 참고서용 안전 패딩 (여백 15픽셀 부여)
                                    padding = 15
                                    left = max(0, abs_xmin - padding)
                                    top = max(0, abs_ymin - padding)
                                    right = min(width, abs_xmax + padding)
                                    bottom = min(height, abs_ymax + padding)
                                    
                                    cropped_img = page_img.crop((left, top, right, bottom))
                                    all_cropped_images.append({
                                        "img": cropped_img,
                                        "label": f"Q_{global_question_count}",
                                        "page": page_idx + 1
                                    })
                                    global_question_count += 1
                                    
                            except Exception as col_err:
                                continue
                        
                        progress_bar.progress((page_idx + 1) / run_pages)
                    
                    status_text.text("📦 초정밀 크롭 완료! 고해상도 ZIP 압축파일 빌드 중...")
                    
                    # --- ZIP 파일 빌드 ---
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as q_zip:
                        for c_item in all_cropped_images:
                            img_buf = io.BytesIO()
                            c_item["img"].save(img_buf, format="PNG")
                            q_zip.writestr(f"{c_item['label']}.png", img_buf.getvalue())
                            
                    progress_bar.empty()
                    status_text.empty()
                    st.success(f"🎯 초정밀 각개격파 성공! 최대 {run_pages}페이지에서 {len(all_cropped_images)}개의 문항을 추출했습니다!")
                    
                    st.download_button(
                        label=f"📥 참고서 문항 전체 다운로드 (총 {len(all_cropped_images)}개 완성)",
                        data=zip_buffer.getvalue(),
                        file_name="KM_MATH_Handbook_Perfect_Cropped.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                    
                    st.divider()
                    st.write("### 🔍 AI 각개격파 추출 결과물 확인 (처음 8개 검증본)")
                    
                    preview_limit = min(8, len(all_cropped_images))
                    for i in range(preview_limit):
                        c_item = all_cropped_images[i]
                        with st.container():
                            st.markdown(f"<div class='crop-card'><strong>📝 [참고서 {c_item['page']}페이지] 파일명: {c_item['label']}.png</strong></div>", unsafe_allow_html=True)
                            st.image(c_item["img"], use_container_width=True)
                            
                    if len(all_cropped_images) > 8:
                        st.info(f"💡 전체 {len(all_cropped_images)}개 문항 중 처음 8개만 화면에 프리뷰를 표시했습니다.")
                        
                except Exception as e:
                    st.error(f"각개격파 가동 중 에러가 발생했습니다: {e}")
                    
    pdf_document.close()