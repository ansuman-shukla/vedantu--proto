import os
import PyPDF2
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import json
import logging
import time
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for structured output
class Question(BaseModel):
    """Model for a single question"""
    question_text: str = Field(description="The exact text of the question")
    question_type: str = Field(description="Type of question (multiple choice, short answer, essay, problem-solving, etc.)")
    subject_topic: str = Field(description="Subject or topic area of the question")
    difficulty_level: str = Field(description="Difficulty level (beginner, intermediate, advanced)")
    context: str = Field(description="Brief context or surrounding information where the question appears")

class QuestionExtractionResult(BaseModel):
    """Model for the complete question extraction result"""
    questions: List[Question] = Field(description="List of extracted questions")
    summary: str = Field(description="Brief summary of the content analyzed")
    total_questions_found: int = Field(description="Total number of questions found")

class PDFQuestionExtractor:
    """
    A class to extract questions from PDF using sliding window approach with Gemini API
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the PDF Question Extractor
        
        Args:
            api_key (str): Google API key for Gemini. If None, will look for GOOGLE_API_KEY env variable
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable or pass api_key parameter.")
        
        # Initialize Gemini model
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.api_key,
            temperature=0.0
        )
        
        # Initialize structured output parser
        self.output_parser = PydanticOutputParser(pydantic_object=QuestionExtractionResult)
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[str]:
        """
        Extract text from each page of the PDF
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            List[str]: List of text content from each page
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pages_text = []
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    pages_text.append(text.strip())
                    logger.info(f"Extracted text from page {page_num + 1}")
                
                return pages_text
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
    
    def create_sliding_windows(self, pages_text: List[str], window_size: int = 3) -> List[Dict[str, Any]]:
        """
        Create sliding windows of pages
        
        Args:
            pages_text (List[str]): List of text from each page
            window_size (int): Size of the sliding window (default: 3)
            
        Returns:
            List[Dict[str, Any]]: List of windows with metadata
        """
        windows = []
        
        for i in range(len(pages_text)):
            # Determine the window boundaries
            start_page = max(0, i - 1) if i > 0 else 0
            end_page = min(len(pages_text), i + window_size - 1) if i == 0 else min(len(pages_text), i + 2)
            
            # Extract pages for current window
            window_pages = pages_text[start_page:end_page]
            
            # Combine text from all pages in the window
            combined_text = "\n\n=== PAGE BREAK ===\n\n".join(window_pages)
            
            window_info = {
                "window_id": i + 1,
                "focus_page": i + 1,
                "page_range": f"{start_page + 1}-{end_page}",
                "total_pages_in_window": len(window_pages),
                "combined_text": combined_text
            }
            
            windows.append(window_info)
            logger.info(f"Created window {i + 1}: pages {start_page + 1}-{end_page}")
        
        return windows
    
    def extract_questions_from_window(self, window_text: str, window_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract questions from a window of pages using Gemini API with structured output
        
        Args:
            window_text (str): Combined text from the window
            window_info (Dict[str, Any]): Window metadata
            
        Returns:
            Dict[str, Any]: Extracted questions and metadata
        """
        # Get format instructions from the parser
        format_instructions = self.output_parser.get_format_instructions()
        
        prompt = f"""
        You are an expert educational content analyzer. Analyze the following text from pages {window_info['page_range']} of a document and extract all questions present in the content.

        Instructions:
        1. Identify all explicit questions (sentences ending with '?')
        2. Identify implicit questions (statements that are clearly meant to be answered)
        3. Identify practice problems, exercises, or assessment items
        4. For each question, provide:
           - The exact question text
           - The type of question (multiple choice, short answer, essay, problem-solving, etc.)
           - The subject/topic area if identifiable
           - The difficulty level (beginner, intermediate, advanced) if assessable
           - The page context where it appears

        Text to analyze:
        {window_text}

        {format_instructions}
        """
        
        try:
            # Make API call to Gemini
            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            
            # Parse the response using structured output parser
            try:
                parsed_response = self.output_parser.parse(response.content)
                
                # Convert Pydantic model to dictionary
                result_dict = {
                    "questions": [q.model_dump() for q in parsed_response.questions],
                    "summary": parsed_response.summary,
                    "total_questions_found": parsed_response.total_questions_found
                }
                
            except Exception as parse_error:
                logger.warning(f"Failed to parse structured response for window {window_info['window_id']}: {str(parse_error)}")
                
                # Fallback: try to extract basic information from raw response
                response_text = response.content
                result_dict = {
                    "questions": [],
                    "summary": response_text[:500] + "..." if len(response_text) > 500 else response_text,
                    "total_questions_found": 0,
                    "raw_response": response_text,
                    "parse_error": str(parse_error)
                }
            
            # Add window metadata
            result_dict.update({
                "window_id": window_info["window_id"],
                "focus_page": window_info["focus_page"],
                "page_range": window_info["page_range"],
                "total_pages_in_window": window_info["total_pages_in_window"]
            })
            
            logger.info(f"Extracted {result_dict.get('total_questions_found', 0)} questions from window {window_info['window_id']}")
            
            return result_dict
            
        except Exception as e:
            logger.error(f"Error extracting questions from window {window_info['window_id']}: {str(e)}")
            return {
                "window_id": window_info["window_id"],
                "focus_page": window_info["focus_page"],
                "page_range": window_info["page_range"],
                "questions": [],
                "summary": f"Error processing window: {str(e)}",
                "total_questions_found": 0,
                "error": str(e)
            }
    
    def process_pdf(self, pdf_path: str, window_size: int = 3, output_path: str = "output.json") -> Dict[str, Any]:
        """
        Process entire PDF with sliding window approach and incremental saving
        
        Args:
            pdf_path (str): Path to the PDF file
            window_size (int): Size of the sliding window (default: 3)
            output_path (str): Path to save incremental results (default: "output.json")
            
        Returns:
            Dict[str, Any]: Complete results from all windows
        """
        logger.info(f"Starting PDF processing: {pdf_path}")
        
        # Extract text from PDF
        pages_text = self.extract_text_from_pdf(pdf_path)
        logger.info(f"Extracted text from {len(pages_text)} pages")
        
        # Create sliding windows
        windows = self.create_sliding_windows(pages_text, window_size)
        logger.info(f"Created {len(windows)} sliding windows")
        
        # Initialize the output file
        self.initialize_output_file(
            output_path=output_path,
            pdf_path=pdf_path,
            total_pages=len(pages_text),
            window_size=window_size,
            total_windows=len(windows)
        )
        
        # Process each window with incremental saving
        for window_idx, window in enumerate(windows, 1):
            logger.info(f"Processing window {window_idx}/{len(windows)}: pages {window['page_range']}")
            
            try:
                # Extract questions from current window
                window_result = self.extract_questions_from_window(
                    window["combined_text"], 
                    window
                )
                
                # Immediately save the window result
                self.update_output_file_with_window(output_path, window_result)
                
                logger.info(f"✅ Window {window_idx} completed and saved. "
                           f"Found {window_result.get('total_questions_found', 0)} questions.")
                
            except Exception as e:
                logger.error(f"❌ Error processing window {window_idx}: {str(e)}")
                # Save error result for this window
                error_result = {
                    "window_id": window["window_id"],
                    "focus_page": window["focus_page"],
                    "page_range": window["page_range"],
                    "questions": [],
                    "summary": f"Error processing window: {str(e)}",
                    "total_questions_found": 0,
                    "error": str(e)
                }
                self.update_output_file_with_window(output_path, error_result)
        
        # Read final results from the output file
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                final_results = json.load(f)
            
            logger.info(f"🎉 PDF processing completed! Found {final_results['summary_stats']['total_questions_found']} total questions")
            logger.info(f"📁 Incremental results saved to: {output_path}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error reading final results: {str(e)}")
            raise
    
    def initialize_output_file(self, output_path: str, pdf_path: str, total_pages: int, window_size: int, total_windows: int):
        """
        Initialize the output file with basic metadata
        
        Args:
            output_path (str): Path to the output JSON file
            pdf_path (str): Path to the PDF being processed
            total_pages (int): Total number of pages in PDF
            window_size (int): Size of sliding window
            total_windows (int): Total number of windows to process
        """
        initial_structure = {
            "pdf_path": pdf_path,
            "total_pages": total_pages,
            "window_size": window_size,
            "total_windows": total_windows,
            "processing_status": "in_progress",
            "windows_completed": 0,
            "windows_results": [],
            "summary_stats": {
                "total_questions_found": 0,
                "questions_by_type": {},
                "questions_by_difficulty": {}
            },
            "processing_started": datetime.now().isoformat()
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(initial_structure, f, indent=2, ensure_ascii=False)
            logger.info(f"Initialized output file: {output_path}")
        except Exception as e:
            logger.error(f"Error initializing output file: {str(e)}")
            raise
    
    def update_output_file_with_window(self, output_path: str, window_result: Dict[str, Any]):
        """
        Update the output file with results from a completed window
        
        Args:
            output_path (str): Path to the output JSON file
            window_result (Dict[str, Any]): Results from the completed window
        """
        try:
            # Read current state
            with open(output_path, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
            
            # Add the new window result
            current_data["windows_results"].append(window_result)
            current_data["windows_completed"] += 1
            
            # Update summary statistics
            questions_found = window_result.get("total_questions_found", 0)
            current_data["summary_stats"]["total_questions_found"] += questions_found
            
            # Aggregate question types and difficulties
            for question in window_result.get("questions", []):
                q_type = question.get("question_type", "unknown")
                q_difficulty = question.get("difficulty_level", "unknown")
                
                current_data["summary_stats"]["questions_by_type"][q_type] = (
                    current_data["summary_stats"]["questions_by_type"].get(q_type, 0) + 1
                )
                current_data["summary_stats"]["questions_by_difficulty"][q_difficulty] = (
                    current_data["summary_stats"]["questions_by_difficulty"].get(q_difficulty, 0) + 1
                )
            
            # Update processing status
            if current_data["windows_completed"] >= current_data["total_windows"]:
                current_data["processing_status"] = "completed"
                current_data["processing_completed"] = datetime.now().isoformat()
            
            # Save updated data
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Updated output file with window {window_result['window_id']} results. "
                       f"Progress: {current_data['windows_completed']}/{current_data['total_windows']}")
            
        except Exception as e:
            logger.error(f"Error updating output file with window {window_result.get('window_id', 'unknown')}: {str(e)}")
            raise
    
    def save_results(self, results: Dict[str, Any], output_path: str):
        """
        Save complete results to JSON file (for backward compatibility)
        
        Args:
            results (Dict[str, Any]): Results from PDF processing
            output_path (str): Path to save the JSON file
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
            raise

def main():
    """
    Main function to demonstrate usage with incremental saving
    """
    # Example usage
    pdf_path = "sample.pdf"  # Replace with your PDF path
    output_path = "output.json"
    
    try:
        # Initialize extractor
        extractor = PDFQuestionExtractor()
        
        # Process PDF with incremental saving
        print(f"🚀 Starting PDF processing with incremental saving...")
        print(f"📄 PDF: {pdf_path}")
        print(f"💾 Output: {output_path}")
        print(f"⏰ Check {output_path} to see real-time progress!")
        
        results = extractor.process_pdf(
            pdf_path=pdf_path, 
            window_size=3,
            output_path=output_path
        )
        
        # Print summary
        print("\n" + "="*60)
        print("🎉 PDF QUESTION EXTRACTION COMPLETED!")
        print("="*60)
        print(f"📄 PDF: {results['pdf_path']}")
        print(f"📊 Total Pages: {results['total_pages']}")
        print(f"🪟 Total Windows: {results['total_windows']}")
        print(f"✅ Windows Completed: {results['windows_completed']}")
        print(f"❓ Total Questions Found: {results['summary_stats']['total_questions_found']}")
        
        if results['summary_stats']['questions_by_type']:
            print("\n📝 Questions by Type:")
            for q_type, count in results['summary_stats']['questions_by_type'].items():
                print(f"   • {q_type}: {count}")
        
        if results['summary_stats']['questions_by_difficulty']:
            print("\n📈 Questions by Difficulty:")
            for difficulty, count in results['summary_stats']['questions_by_difficulty'].items():
                print(f"   • {difficulty}: {count}")
        
        print(f"\n💾 Complete results available in: {output_path}")
        print(f"🕐 Processing Status: {results.get('processing_status', 'unknown')}")
        
        if results.get('processing_started'):
            print(f"⏰ Started: {results['processing_started']}")
        if results.get('processing_completed'):
            print(f"🏁 Completed: {results['processing_completed']}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        print(f"❌ Error: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure your PDF file exists and is readable")
        print("2. Check that your GOOGLE_API_KEY is set in .env file")
        print("3. Verify all dependencies are installed")
        print(f"4. Check {output_path} for any partial results")

if __name__ == "__main__":
    main()