import streamlit as st
import base64
import os
from PIL import Image
import io
from dotenv import load_dotenv
from mistralai import Mistral
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import PyPDF2
import json
import logging
import time
from datetime import datetime

# Load environment variables
load_dotenv()

# System prompt for question extraction
SYSTEM_PROMPT = """You are an expert AI assistant specialized in parsing educational content. Your task is to act as a highly accurate question extractor for OCR text from NCERT Class 12th Mathematics textbooks.

You will be given the OCR text for three consecutive pages in a "sliding window" format, along with a list of previously extracted questions and, for each page, a list of unique IDs for any images present on that page. Your primary goal is to identify and extract all complete mathematical questions **exclusively from the main_page**.

### Core Instructions & Rules

1.  **The Primacy of the `main_page`:**
    *   Your analysis and extraction MUST be centered on the content of the `main_page`.
    *   You will read and process the `main_page` to find questions.

2.  **Contextual Use of `front_page` and `back_page`:**
    *   The `front_page` and `back_page` are provided **for context ONLY**. They serve one single purpose: to help you complete a question that is fragmented on the `main_page`.
    *   **Scenario 1 (Question starts on Main, ends on Back):** If a question begins on the `main_page` but its text is cut off and continues onto the `back_page`, you MUST use the `back_page` to find the rest of the question's text and form a complete question.
    *   **Scenario 2 (Question starts on Front, ends on Main):** If a question ends on the `main_page` but its text clearly started on the `front_page`, you MUST use the `front_page` to find the beginning of the question's text and form a complete question.

3.  **CRITICAL RULE: Image Association:**
    *   The text for each page may be followed by a section listing the IDs of images on that page (e.g., `[Image ID: page_1_img_0]`).
    *   If a question's text refers to a figure, diagram, graph, or image (e.g., "See Fig. 7.1", "in the given figure", "using the graph shown..."), you MUST identify the corresponding image ID from the list provided for that page.
    *   Place this unique ID in the `image_id` field of your JSON output.
    *   If a question has no associated image, the `image_id` field should be `null`.

4.  **CRITICAL RULE: STRICT PROHIBITION ON SIDE-PAGE EXTRACTION:**
    *   **You MUST NOT extract any question that exists *entirely* on the `front_page` or `back_page`**.
    *   If you see a full, self-contained question on the `front_page` or `back_page`, you MUST ignore it. They are only reference material.

5.  **What to Extract (Types of Questions):**
    *   **ONLY** formally defined questions that fall into these categories:
        - **Exercise Questions**: Questions explicitly labeled as "Exercise [X.Y]" or part of an exercise section
        - **Example Questions**: Questions explicitly labeled as "Example [X.Y]" or "Solved Example"
        - **Miscellaneous Questions**: Questions explicitly labeled as "Miscellaneous Exercises" or "Miscellaneous Questions"
        - **Practice Questions**: Questions in sections clearly marked as "Practice Problems" or similar formal designations
    *   Extract only the question text, not the solution or answer.
    *   The question must be formally presented with clear demarcation (numbering, labeling, or section headers).

6.  **What to STRICTLY AVOID Extracting:**
    *   Small inline questions or rhetorical questions within explanatory text
    *   Questions that are part of definitions, theorems, or proofs
    *   Casual questions used for explanation (e.g., "What happens if...", "Can you find...", "How do we...")
    *   Questions embedded within paragraphs as teaching tools
    *   Answers, solutions, proofs, or explanations
    *   Question numbers, exercise numbers, or any other numbering
    *   Chapter titles, section headings, theorems, definitions, or general descriptive text
    *   Any question that is not formally structured as a standalone problem to be solved

7.  **Duplicate Prevention:**
    *   Review the provided list of previously extracted questions.
    *   **Do not include any question in your output that is already present in that list.**

8.  **Inferring Chapter and Topic:**
    *   From the context available on the `main_page`, infer the `chapter` name and the specific `topic`.

### Output Schema

You MUST format your output as a JSON list of objects. Each object represents a single extracted question and must follow this exact schema. If no new questions are found, return an empty list `[]`.

```json
[
  {
    "chapter": "The name of the chapter the question belongs to",
    "question": "The full, complete text of the extracted question.",
    "topic": "The specific mathematical topic the question is about.",
    "image_id": "The unique ID of the associated image (e.g., 'page_5_img_0'), or null if there is no image."
  }
]
```"""

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_question_extractor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Helper Functions ---

def encode_pdf(pdf_bytes):
    """Encode the pdf bytes to base64."""
    return base64.b64encode(pdf_bytes).decode('utf-8')

def decode_base64_image(base64_string):
    """Decode base64 string to PIL Image."""
    try:
        if base64_string.startswith('data:image'):
            base64_string = base64_string.split(',')[1]
        image_data = base64.b64decode(base64_string)
        return Image.open(io.BytesIO(image_data))
    except Exception as e:
        st.error(f"Error decoding image: {e}")
        return None

def display_first_page_preview(pdf_bytes):
    """Extracts and displays the first page of a PDF in the sidebar."""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        writer = PyPDF2.PdfWriter()
        writer.add_page(reader.pages[0])
        
        first_page_buffer = io.BytesIO()
        writer.write(first_page_buffer)
        first_page_buffer.seek(0)
        
        base64_pdf = base64.b64encode(first_page_buffer.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="400" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Could not generate first page preview: {e}")


def get_page_content_with_images(page_object):
    """Combines page markdown with a list of its image IDs for the LLM."""
    content = page_object.markdown if page_object.markdown else ""
    if page_object.images:
        content += "\n\n--- IMAGES ON THIS PAGE ---\n"
        for img in page_object.images:
            content += f"[Image ID: {img.id}]\n"
    return content

# --- Core Logic Functions ---

def process_ocr(pdf_bytes):
    """Process OCR using Mistral API and cache images."""
    start_time = time.time()
    pdf_size_mb = len(pdf_bytes) / (1024 * 1024)
    
    logger.info("=" * 50)
    logger.info("STARTING OCR PROCESSING")
    logger.info("=" * 50)
    logger.info(f"PDF size: {pdf_size_mb:.2f} MB")
    logger.info(f"OCR started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            logger.error("MISTRAL_API_KEY not found in environment variables")
            st.error("MISTRAL_API_KEY not found in environment variables")
            return None
            
        logger.debug("Initializing Mistral client")
        client = Mistral(api_key=api_key)
        
        logger.debug("Encoding PDF to base64")
        base64_pdf = encode_pdf(pdf_bytes)
        logger.debug(f"Base64 encoding complete, size: {len(base64_pdf)} characters")
        
        logger.info("Sending PDF to Mistral OCR API")
        ocr_start_time = time.time()
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "document_url", "document_url": f"data:application/pdf;base64,{base64_pdf}"},
            include_image_base64=True
        )
        ocr_duration = time.time() - ocr_start_time
        
        logger.info(f"OCR API response received in {ocr_duration:.2f} seconds")
        
        if ocr_response:
            logger.info(f"OCR successful! Processing {len(ocr_response.pages)} pages")
            
            # Cache images
            image_count = 0
            st.session_state.image_lookup = {}
            for page_idx, page in enumerate(ocr_response.pages):
                page_text_length = len(page.markdown) if page.markdown else 0
                page_image_count = len(page.images) if page.images else 0
                
                logger.debug(f"Page {page_idx + 1}: {page_text_length} text characters, {page_image_count} images")
                
                if page.images:
                    for img in page.images:
                        st.session_state.image_lookup[img.id] = img.image_base64
                        image_count += 1
            
            total_duration = time.time() - start_time
            logger.info(f"OCR processing complete! Cached {image_count} images")
            logger.info(f"Total OCR processing time: {total_duration:.2f} seconds")
            logger.info("=" * 50)
        else:
            logger.error("OCR response was empty or None")
        
        return ocr_response
    except Exception as e:
        total_duration = time.time() - start_time
        logger.error(f"Error processing OCR after {total_duration:.2f} seconds: {e}")
        st.error(f"Error processing OCR: {e}")
        return None

def extract_questions_for_window(main_page_text, front_page_text, back_page_text, prev_extracted_questions_json, page_number=None):
    """Generate questions for a single sliding window using Google Gemini."""
    start_time = time.time()
    page_info = f"Page {page_number}" if page_number else "Unknown page"
    
    logger.info(f"Starting question extraction for {page_info}")
    logger.debug(f"Main page text length: {len(main_page_text)} characters")
    logger.debug(f"Front page text length: {len(front_page_text)} characters")
    logger.debug(f"Back page text length: {len(back_page_text)} characters")
    logger.debug(f"Previous questions count: {len(json.loads(prev_extracted_questions_json)) if prev_extracted_questions_json != '[]' else 0}")
    
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GOOGLE_API_KEY not found in environment variables")
            st.error("GOOGLE_API_KEY not found in environment variables")
            return []
            
        logger.debug(f"Initializing ChatGoogleGenerativeAI for {page_info}")
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=api_key, temperature=0.1)
        
        logger.debug(f"Using embedded system prompt for {page_info}")
        system_message = SystemMessage(content=SYSTEM_PROMPT)

        human_message_content = f"""
Here is the data for the current window. Please analyze it according to the instructions and extract the questions from the main_page.
--- PREVIOUSLY EXTRACTED QUESTIONS (for duplicate checking) ---
{prev_extracted_questions_json}
--- FRONT PAGE (for context only) ---
{front_page_text}
--- MAIN PAGE (primary focus for extraction) ---
{main_page_text}
--- BACK PAGE (for context only) ---
{back_page_text}
"""
        human_message = HumanMessage(content=human_message_content)
        
        logger.info(f"Sending request to Gemini API for {page_info}")
        logger.debug(f"Total message content length: {len(human_message_content)} characters")
        
        messages = [system_message, human_message]
        llm_start_time = time.time()
        response = llm.invoke(messages)
        llm_duration = time.time() - llm_start_time
        
        logger.info(f"Gemini API response received for {page_info} in {llm_duration:.2f} seconds")
        
        content = response.content.strip()
        logger.debug(f"Raw response length: {len(content)} characters")
        
        if content.startswith('```json'): content = content[7:]
        if content.endswith('```'): content = content[:-3]
        content = content.strip()
        
        logger.debug(f"Cleaned response length: {len(content)} characters")
        
        try:
            if not content: 
                logger.warning(f"Empty response received for {page_info}")
                return []
            questions_json = json.loads(content)
            extracted_count = len(questions_json) if isinstance(questions_json, list) else 0
            total_duration = time.time() - start_time
            
            logger.info(f"Successfully extracted {extracted_count} questions from {page_info} in {total_duration:.2f} seconds")
            
            if extracted_count > 0:
                logger.debug(f"Questions extracted from {page_info}: {[q.get('question', 'No question text')[:100] + '...' if len(q.get('question', '')) > 100 else q.get('question', 'No question text') for q in questions_json]}")
            
            return questions_json if isinstance(questions_json, list) else []
            
        except json.JSONDecodeError as json_err:
            total_duration = time.time() - start_time
            logger.error(f"JSON parsing failed for {page_info} after {total_duration:.2f} seconds: {json_err}")
            logger.debug(f"Raw response content that failed to parse: {content}")
            st.warning(f"Failed to parse JSON response from LLM for {page_info}. Raw response: {content}")
            return []
            
    except Exception as e:
        total_duration = time.time() - start_time
        logger.error(f"Error generating questions for {page_info} after {total_duration:.2f} seconds: {e}")
        st.error(f"Error generating questions for {page_info}: {e}")
        return []

def process_pdf_with_sliding_window():
    """Iterates through the PDF with a sliding window and extracts questions."""
    start_time = time.time()
    ocr_pages = st.session_state.ocr_response.pages
    total_pages = len(ocr_pages)
    
    logger.info(f"Starting sliding window processing for PDF with {total_pages} pages")
    logger.info(f"Process started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if 'all_questions' not in st.session_state:
        st.session_state.all_questions = []
        logger.debug("Initialized empty questions list in session state")

    progress_bar = st.progress(0, text="Starting question generation...")
    
    # Statistics tracking
    total_questions_extracted = 0
    pages_with_questions = 0
    pages_without_questions = 0

    with st.status("Processing PDF with sliding window...", expanded=True) as status:
        for i in range(total_pages):
            page_start_time = time.time()
            page_num = i + 1
            
            logger.info(f"Processing sliding window for page {page_num}/{total_pages}")
            status.update(label=f"Processing Page {page_num}/{total_pages}...")
            
            # Get page content
            main_page_text = get_page_content_with_images(ocr_pages[i])
            front_page_text = get_page_content_with_images(ocr_pages[i-1]) if i > 0 else "This is the first page. There is no front page."
            back_page_text = get_page_content_with_images(ocr_pages[i+1]) if i < total_pages - 1 else "This is the last page. There is no back page."
            
            logger.debug(f"Page {page_num} - Main text length: {len(main_page_text)} chars")
            logger.debug(f"Page {page_num} - Front context length: {len(front_page_text)} chars")
            logger.debug(f"Page {page_num} - Back context length: {len(back_page_text)} chars")
            
            prev_questions_json = json.dumps(st.session_state.all_questions, indent=2)
            current_total = len(st.session_state.all_questions)
            
            logger.debug(f"Page {page_num} - Previous questions count: {current_total}")
            
            newly_extracted = extract_questions_for_window(
                main_page_text, front_page_text, back_page_text, prev_questions_json, page_num
            )
            
            page_duration = time.time() - page_start_time
            
            if newly_extracted:
                st.session_state.all_questions.extend(newly_extracted)
                pages_with_questions += 1
                total_questions_extracted += len(newly_extracted)
                
                logger.info(f"Page {page_num}: Successfully extracted {len(newly_extracted)} questions in {page_duration:.2f} seconds")
                for idx, question in enumerate(newly_extracted):
                    logger.debug(f"Page {page_num} Question {idx+1}: {question.get('question', 'No question text')[:100]}{'...' if len(question.get('question', '')) > 100 else ''}")
                
                st.write(f"✅ Page {page_num}: Found {len(newly_extracted)} new question(s).")
            else:
                pages_without_questions += 1
                logger.info(f"Page {page_num}: No questions extracted in {page_duration:.2f} seconds")
                st.write(f"☑️ Page {page_num}: No new questions found.")

            progress_bar.progress((i + 1) / total_pages, text=f"Processed Page {page_num}/{total_pages}")
            
            # Log cumulative statistics
            logger.debug(f"Cumulative stats after page {page_num}: {len(st.session_state.all_questions)} total questions")

        status.update(label="All pages processed!", state="complete")
    
    # Final processing summary
    total_duration = time.time() - start_time
    end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    logger.info("=" * 80)
    logger.info("SLIDING WINDOW PROCESSING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Process completed at: {end_time}")
    logger.info(f"Total processing time: {total_duration:.2f} seconds")
    logger.info(f"Average time per page: {total_duration/total_pages:.2f} seconds")
    logger.info(f"Total pages processed: {total_pages}")
    logger.info(f"Pages with questions: {pages_with_questions}")
    logger.info(f"Pages without questions: {pages_without_questions}")
    logger.info(f"Total questions extracted: {total_questions_extracted}")
    logger.info(f"Final question count: {len(st.session_state.all_questions)}")
    if total_questions_extracted > 0:
        logger.info(f"Average questions per productive page: {total_questions_extracted/pages_with_questions:.2f}")
    logger.info("=" * 80)

    st.success(f"Processing complete! Found a total of {len(st.session_state.all_questions)} questions.")
    st.rerun()

# --- Streamlit UI ---

def main():
    st.set_page_config(page_title="PDF Question Extractor", page_icon="📄", layout="wide")
    st.title("📄 PDF Question Extractor with Sliding Window")
    st.markdown("Upload a PDF, run OCR, and then generate questions with image association.")
    
    # Initialize session state keys
    for key in ['ocr_response', 'all_questions', 'image_lookup', 'uploaded_file_info']:
        if key not in st.session_state:
            st.session_state[key] = None

    with st.sidebar:
        st.header("Upload PDF")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", key="pdf_uploader")

        # --- CORRECTED STATE MANAGEMENT ---
        if uploaded_file is not None:
            # Use a tuple of (name, size) as a unique file identifier
            current_file_info = (uploaded_file.name, uploaded_file.size)
            
            # Check if a new file has been uploaded
            if st.session_state.uploaded_file_info != current_file_info:
                logger.info(f"New PDF uploaded: {current_file_info[0]} (Size: {current_file_info[1]} bytes)")
                st.session_state.uploaded_file_info = current_file_info
                st.session_state.uploaded_file_bytes = uploaded_file.getvalue()
                # Reset all derived data when a new file is uploaded
                st.session_state.ocr_response = None
                st.session_state.all_questions = None
                st.session_state.image_lookup = None
                logger.debug("Reset session state for new PDF upload")
                st.info("New PDF detected. Ready to process.")
                st.rerun() # Rerun to show the preview immediately

            # Display first page preview immediately
            display_first_page_preview(st.session_state.uploaded_file_bytes)

            # OCR processing button
            if st.button("🔍 Process OCR", type="primary", use_container_width=True):
                with st.spinner("Processing OCR... This may take a few moments."):
                    ocr_response = process_ocr(st.session_state.uploaded_file_bytes)
                    if ocr_response:
                        st.session_state.ocr_response = ocr_response
                        st.success("OCR processing complete!")
                    else:
                        st.error("Failed to process OCR.")
                st.rerun()

    # --- MAIN PANEL LOGIC ---
    if st.session_state.uploaded_file_info is None:
        st.info("Please upload a PDF file using the sidebar to get started.")
        return

    st.success(f"Currently working with: **{st.session_state.uploaded_file_info[0]}**")

    if st.session_state.ocr_response:
        st.header("🎯 Question Generation")
        
        if st.button("🤖 Generate Questions (Sliding Window)", use_container_width=True):
            logger.info("User initiated question generation with sliding window")
            logger.info(f"PDF: {st.session_state.uploaded_file_info[0]} ({st.session_state.uploaded_file_info[1]} bytes)")
            logger.info(f"Total pages available: {len(st.session_state.ocr_response.pages)}")
            st.session_state.all_questions = []
            process_pdf_with_sliding_window()

        if st.session_state.all_questions is not None:
            st.subheader(f"📚 Extracted Questions ({len(st.session_state.all_questions)} total)")
            
            if st.session_state.all_questions:
                for i, q in enumerate(st.session_state.all_questions):
                    with st.container(border=True):
                        st.markdown(f"**Question {i+1}**")
                        st.markdown(f"**Chapter:** {q.get('chapter', 'N/A')}")
                        st.markdown(f"**Topic:** {q.get('topic', 'N/A')}")
                        st.markdown(f"> {q.get('question', 'No question text found.')}")
                        
                        image_id = q.get("image_id")
                        if image_id and st.session_state.image_lookup:
                            image_base64 = st.session_state.image_lookup.get(image_id)
                            if image_base64:
                                st.markdown("**Associated Image:**")
                                decoded_image = decode_base64_image(image_base64)
                                if decoded_image:
                                    st.image(decoded_image, use_container_width=True)
                            else:
                                st.warning(f"Warning: Image ID '{image_id}' was found but could not be loaded from the OCR cache.")

                all_questions_json = json.dumps(st.session_state.all_questions, indent=2)
                st.download_button(
                    label="📥 Download All Questions (JSON)",
                    data=all_questions_json,
                    file_name="all_extracted_questions.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                st.info("No questions were extracted from the document.")

        with st.expander("Click to view detailed OCR output for each page"):
            for page_idx, page in enumerate(st.session_state.ocr_response.pages):
                st.subheader(f"Page {page_idx + 1}")
                st.markdown("**Extracted Text:**")
                st.markdown(page.markdown if page.markdown else "No text extracted.")
                st.divider()
    elif st.session_state.uploaded_file_info:
        st.info("PDF loaded. Please click 'Process OCR' in the sidebar to continue.")

if __name__ == "__main__":
    main()