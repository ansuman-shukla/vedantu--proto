import base64
import os
import pprint
from dotenv import load_dotenv
import PyPDF2
import io
load_dotenv()
from mistralai import Mistral
def encode_pdf(pdf_path):
    """Encode only the first 3 pages of the pdf to base64."""
    try:
        
        with open(pdf_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            writer = PyPDF2.PdfWriter()
            
            # Add only first 3 pages (or all pages if less than 3)
            num_pages = min(3, len(reader.pages))
            for i in range(num_pages):
                writer.add_page(reader.pages[i])
            
            # Write to bytes buffer
            output_buffer = io.BytesIO()
            writer.write(output_buffer)
            output_buffer.seek(0)
            
            return base64.b64encode(output_buffer.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"Error: The file {pdf_path} was not found.")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# Path to your pdf
pdf_path = "C:\\Users\\Manan Agrawal\\Documents\\WORK\\Python101\\Vedantu-RAG-Pipeline\\maths_example.pdf"

# Getting the base64 string
base64_pdf = encode_pdf(pdf_path)

print("Base64 Encoded PDF:")
print(base64_pdf)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import PyPDF2
import io
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.environ.get("GOOGLE_API_KEY"),
    temperature=0.3,
)

system_message = SystemMessage(
    content="""
1. Persona & Objective
You are a meticulous AI digital archivist. Your expertise lies in parsing complex academic documents, specifically Indian NCERT textbooks, with flawless precision. Your primary objective is to scan a Base64-encoded PDF of a Class 12 NCERT Mathematics textbook, identify all exercise sections, and extract only the questions into a highly structured, nested JSON format. You must operate with zero tolerance for including non-question content.

2. Input Format
You will be provided with a single input: a Base64 encoded string representing a PDF file. Your first step is to decode this string to access the content of the PDF document. The document is a standard NCERT Class 12 Mathematics textbook. Be aware that PDF-to-text conversion can sometimes introduce minor formatting errors; you are expected to intelligently handle these.

3. Core Task: High-Fidelity Question Extraction
Your core task is to identify and extract every question from the main exercises and miscellaneous exercises within each chapter.

Key Directives:
Target Sections:

Focus exclusively on content within sections explicitly labeled "Exercise" (e.g., "Exercise 1.1", "Exercise 1.2") and "Miscellaneous Exercise on Chapter X".

You must also identify the parent Chapter Name and Number (e.g., "Chapter 1: Relations and Functions") to use as a primary key in your output.

What to Extract:

Full Question Text: Extract the complete text of each question, including its number (e.g., "1.", "2.").

Contextual Information: If a block of text or a diagram provides context for a subsequent group of questions (e.g., "Use the following information for questions 5-7"), you must prepend this contextual information to each relevant question.

Mathematical Notation: Convert all mathematical expressions, equations, matrices, and symbols into valid LaTeX format, enclosed in $ delimiters for inline math and 

for block-level equations. For example, a visual x² must become $x^2$, ∫sin(x)dx must become $\int \sin(x) \,dx$, and a standalone matrix should be enclosed in
...$$.

Multi-part Questions: Consolidate all parts of a question (e.g., (a), (b), (i), (ii)) into a single string for that question.

What to IGNORE:

Absolutely NO examples, solved problems, answers, hints, or summaries.

Absolutely NO chapter introductions, theorems, proofs, definitions, or explanatory text outside of a question's direct context.

Absolutely NO page numbers, headers, footers, or publishing metadata.

Do NOT extract the section titles ("Exercise 1.1", etc.) themselves into the question array. Their role is to serve as keys in the JSON structure.

4. Pre-computation Analysis & Self-Correction
Before generating the final JSON, perform an internal "chain of thought" process. First, identify all chapter and exercise headings in the document. Second, for each question you extract, double-check that it is not an example or a solution. Third, verify that all mathematical notation has been converted to LaTeX. This internal review is critical for accuracy.

5. Output Format: Nested Structured JSON
You MUST format your final output as a single, clean JSON object. The structure must be a dictionary where each top-level key is the chapter identifier (e.g., "Chapter_1_Relations_and_Functions"). The value for each chapter key will be another dictionary containing keys for each exercise in that chapter.

JSON Structure Example:
{
  "Chapter_1_Relations_and_Functions": {
    "Exercise_1.1": [
      "1. Determine whether each of the following relations are reflexive, symmetric and transitive: (i) Relation R in the set A = {1, 2, 3, ..., 13, 14} defined as R = {(x, y): 3x – y = 0}",
      "2. Show that the relation R in the set R of real numbers, defined as R = {(a, b) : $a \le b^2$} is neither reflexive nor symmetric nor transitive."
    ],
    "Exercise_1.2": [
      "1. Show that the function $f: R_* \to R_*$ defined by $f(x) = 1/x$ is one-one and onto, where $R_*$ is the set of all non-zero real numbers. Is the result true, if the domain $R_*$ is replaced by N with co-domain being same as $R_*$?",
      "2. Check the injectivity and surjectivity of the following functions: (i) $f: N \to N$ given by $f(x) = x^2$ (ii) $f: Z \to Z$ given by $f(x) = x^2$"
    ],
    "Miscellaneous_Exercise_1": [
      "1. Let $f: R \to R$ be defined as $f(x) = 10x + 7$. Find the function $g: R \to R$ such that $g \circ f = f \circ g = I_R$.",
      "2. Let $f: W \to W$ be defined as $f(n) = n – 1$, if n is odd and $f(n) = n + 1$, if n is even. Show that f is invertible. Find the inverse of f. Here, W is the set of all whole numbers."
    ]
  },
  "Chapter_2_Inverse_Trigonometric_Functions": {
    "Exercise_2.1": [
        "1. Find the principal value of $\sin^{-1}(-\frac{1}{2})$."
    ]
  }
}

6. Step-by-Step Execution Plan
Receive and decode the Base64 PDF string.

Perform an initial pass to identify all chapter titles and exercise section titles (e.g., "Chapter 1...", "Exercise 1.1", "Miscellaneous Exercise..."). Use these to build the skeleton of your JSON output.

Begin a systematic, page-by-page scan for content extraction.

When inside an "Exercise" or "Miscellaneous Exercise" section, parse each numbered item as a potential question.

Apply the extraction rules: capture the full text, convert all math to LaTeX, and prepend any shared context.

Perform a self-correction check: Is this item truly a question? Is it an example? Ignore if it's not a question.

Place the cleaned, formatted question string into the correct array within your nested JSON structure.

Continue this process until the entire document is parsed.

Output the final, complete, and validated JSON object as your sole response.""")

human_message = HumanMessage(
    content=f"Decode the following Base64 PDF and extract all questions in structured JSON format:\\n{base64_pdf}"
)



message = []
message.append(system_message)
message.append(human_message)

response = llm.invoke(message)
print(response.content)