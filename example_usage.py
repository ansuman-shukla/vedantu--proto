"""
Example usage of the PDF Question Extractor with Incremental Saving
"""

from questions_ingestion_pipeline.main import PDFQuestionExtractor
import os

def run_example():
    """
    Example of how to use the PDFQuestionExtractor with incremental saving
    """
    
    # Initialize the extractor
    # Make sure you have set up your .env file with GOOGLE_API_KEY
    extractor = PDFQuestionExtractor()
    
    # Path to your PDF file
    pdf_path = "maths_example.pdf"  # Replace with your actual PDF path
    output_file = "output.json"
    
    # Check if PDF exists
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        print("Please update the pdf_path variable with the correct path to your PDF file")
        return
    
    try:
        print("🚀 Starting PDF processing with incremental saving...")
        print(f"📄 PDF: {pdf_path}")
        print(f"💾 Output: {output_file}")
        print(f"⏰ You can monitor progress in real-time by checking {output_file}")
        print("💡 Tip: Run 'python monitor_progress.py' in another terminal to see live progress!")
        print("-" * 60)
        
        # Process the PDF with sliding window approach and incremental saving
        results = extractor.process_pdf(
            pdf_path=pdf_path,
            window_size=3,  # 3-page sliding window
            output_path=output_file
        )
        
        # Display final summary (results are already saved incrementally)
        print("\n" + "="*60)
        print("🎉 EXTRACTION COMPLETE!")
        print("="*60)
        print(f"📄 PDF Processed: {os.path.basename(pdf_path)}")
        print(f"📊 Total Pages: {results['total_pages']}")
        print(f"🪟 Windows Created: {results['total_windows']}")
        print(f"✅ Windows Completed: {results['windows_completed']}")
        print(f"❓ Questions Found: {results['summary_stats']['total_questions_found']}")
        print(f"🚀 Status: {results.get('processing_status', 'unknown').upper()}")
        
        if results['summary_stats']['questions_by_type']:
            print("\n📝 Question Types:")
            for q_type, count in results['summary_stats']['questions_by_type'].items():
                print(f"   • {q_type}: {count}")
        
        if results['summary_stats']['questions_by_difficulty']:
            print("\n📈 Difficulty Levels:")
            for difficulty, count in results['summary_stats']['questions_by_difficulty'].items():
                print(f"   • {difficulty}: {count}")
        
        print(f"\n💾 Complete results available in: {output_file}")
        
        # Show sample questions from first window
        if results['windows_results'] and results['windows_results'][0].get('questions'):
            print(f"\n🔍 Sample questions from first window:")
            for i, question in enumerate(results['windows_results'][0]['questions'][:3], 1):
                print(f"   {i}. {question.get('question_text', 'N/A')[:100]}...")
        
        # Show timing information
        if results.get('processing_started'):
            print(f"\n⏰ Started: {results['processing_started']}")
        if results.get('processing_completed'):
            print(f"🏁 Completed: {results['processing_completed']}")
        
    except Exception as e:
        print(f"❌ Error processing PDF: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Your .env file contains a valid GOOGLE_API_KEY")
        print("2. All required packages are installed (run: pip install -r requirements.txt)")
        print("3. The PDF file path is correct and accessible")
        print(f"4. Check {output_file} for any partial results")

def run_with_monitoring():
    """
    Example showing how to run processing with live monitoring
    """
    import threading
    import time
    
    # Start monitoring in a separate thread
    def monitor():
        time.sleep(2)  # Give processing a moment to start
        from monitor_progress import monitor_progress
        monitor_progress("output.json", refresh_interval=1)
    
    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    
    # Run the main processing
    run_example()

if __name__ == "__main__":
    print("Choose processing mode:")
    print("1. Standard processing")
    print("2. Processing with live monitoring")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        print("🔍 Starting processing with live monitoring...")
        run_with_monitoring()
    else:
        print("🚀 Starting standard processing...")
        run_example()
        print("\n💡 Next time, try option 2 for live monitoring!")
