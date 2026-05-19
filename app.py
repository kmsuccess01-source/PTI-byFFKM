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
    
    api_key = st.text_input("Gemini API Key를 입력하세요", type="password")
    st.divider()
    
    layout_option = st.radio("레이아웃 선택", ["1단 구성", "2단 구성"])
    numbering_option = st.radio("문항 번호 체계", ["오름차순형", "페이지+번호 혼합형"])

# --- 3. 메인 화면 구성 ---
st.markdown("<h1 class='title-text'>PTI-byFFKM</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle-text'>수학 학습 자료 자동화 커팅 시스템 (무료 고속 Flash 모드)</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type="pdf")

if uploaded_file is not None:
    pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    total_pages = len(pdf_document)
    st.success(f"총 {total_pages}페이지의 PDF가 성공적으로 로드되었습니다.")
    
    # 1페이지 렌더링 (2배 확대하여 선명도 유지)
    page = pdf_document.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img_data = pix.tobytes("png")
    base_img = Image.open(io.BytesIO(img_data))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("원본 1페이지 미리보기")
        st.image(base_img, use_container_width=True)
        
    with col2:
        st.subheader("AI 문항 자동 분할 및 다운로드")
        
        if not api_key:
            st.warning("왼쪽 사이드바에 Gemini API Key를 입력하시면 자동 커팅을 시작할 수 있습니다.")
        else:
            if st.button("✂️ 고속 자동 자르기 시작"):
                with st.spinner("무료 고속 Flash 엔진이 수학 문제를 분석 중입니다..."):
                    try:
                        genai.configure(api_key=api_key)
                        
                        # 무료 플랜 한도가 넉넉한 gemini-2.5-flash 모델로 세팅
                        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
                        
                        # Flash 모델이 헷갈리지 않도록 좌표 지시 프롬프트를 극한으로 구체화
                        prompt = """
                        이 이미지는 좌우 2단(중앙 세로 구분선 존재)으로 구성된 시험지야.
                        각 수학 문제(문항 번호, 본문 수식, 보기 전체)의 영역을 검출해줘.
                        
                        [핵심 지시사항]
                        1. 오른쪽 단에 있는 문제들의 왼쪽 시작점(xmin)을 너무 오른쪽 여백으로 잡지 말고, 
                           세로 구분선 바로 우측의 문항 번호가 시작되는 지점부터 타이트하게 잡아줘.
                        2. 문항 번호 가 잘리지 않게 상단 영역(ymin)도 여유있게 위로 올려서 잡아줘.
                        
                        반드시 아래와 같은 JSON 배열 형식으로만 응답해.
                        [ {"box_2d": [ymin, xmin, ymax, xmax], "label": "문제 번호"} ]
                        좌표는 0에서 1000 사이의 정규화 값이어야 해.
                        """
                        
                        response = model.generate_content([prompt, base_img], generation_config={"response_mime_type": "application/json"})
                        result_json = json.loads(response.text)
                        
                        width, height = base_img.size
                        cropped_images = []
                        
                        # 검증용 도화지
                        draw_img = base_img.copy()
                        draw = ImageDraw.Draw(draw_img)
                        
                        # --- ✂️ 정밀 크롭 및 여백 대폭 확장(Padding 25) ---
                        for idx, item in enumerate(result_json):
                            box = item["box_2d"]
                            label = item.get("label", f"{idx+1}")
                            clean_label = "".join(filter(str.isdigit, label))
                            if not clean_label:
                                clean_label = str(idx + 1)
                            
                            ymin, xmin, ymax, xmax = box[0], box[1], box[2], box[3]
                            
                            abs_ymin = int((ymin / 1000) * height)
                            abs_xmin = int((xmin / 1000) * width)
                            abs_ymax = int((ymax / 1000) * height)
                            abs_xmax = int((xmax / 1000) * width)
                            
                            # Flash의 미세한 오차를 커버하기 위해 사방 여백을 25픽셀로 듬뿍 제공!
                            padding = 25
                            left = max(0, abs_xmin - padding)
                            top = max(0, abs_ymin - padding)
                            right = min(width, abs_xmax + padding)
                            bottom = min(height, abs_ymax + padding)
                            
                            # 1. 검증용 빨간 박스 그리기
                            draw.rectangle([left, top, right, bottom], outline="red", width=4)
                            draw.text((left + 5, top + 5), f"Q_{clean_label}", fill="red")
                            
                            # 2. 이미지 크롭
                            cropped_img = base_img.crop((left, top, right, bottom))
                            cropped_images.append({"img": cropped_img, "label": f"Q_{clean_label}"})
                        
                        cropped_images.sort(key=lambda x: x["label"])
                        st.success(f"🎯 총 {len(cropped_images)}개의 문항 분리 완료! (무료 한도 모드)")
                        
                        # --- 📦 ZIP 압축파일 빌드 ---
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w") as q_zip:
                            for c_item in cropped_images:
                                img_buf = io.BytesIO()
                                c_item["img"].save(img_buf, format="PNG")
                                q_zip.writestr(f"{c_item['label']}.png", img_buf.getvalue())
                        
                        # 다운로드 버튼
                        st.download_button(
                            label="📥 잘려진 문항 다운로드 (ZIP 파일 받기)",
                            data=zip_buffer.getvalue(),
                            file_name="KM_MATH_PTI_Flash_Version.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                        
                        # 결과 시각화
                        st.divider()
                        st.write("### 📊 AI 탐지 영역 검증 (Flash 보정 버전)")
                        st.image(draw_img, use_container_width=True)
                        
                        st.write("### 🔍 분할된 문항 개별 이미지 확인")
                        for c_item in cropped_images:
                            with st.container():
                                st.markdown(f"<div class='crop-card'><strong>📝 문항 파일명: {c_item['label']}.png</strong></div>", unsafe_allow_html=True)
                                st.image(c_item["img"], use_container_width=True)
                                
                    except Exception as e:
                        st.error(f"자동 컷팅 중 에러가 발생했습니다: {e}")
                        
    pdf_document.close()