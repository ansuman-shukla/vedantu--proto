# PDF Question Extraction Pipeline

A sophisticated Python application that processes PDF documents using a sliding window approach to extract questions with the help of Google's Gemini AI model via LangChain.

## Features

- **Sliding Window Processing**: Processes PDF with 3-page sliding windows to maintain context
- **AI-Powered Question Extraction**: Uses Google Gemini to intelligently identify questions
- **Comprehensive Analysis**: Extracts question types, difficulty levels, and topics
- **Structured Output**: Results saved in JSON format with detailed metadata
- **Context Preservation**: Adjacent pages provide context for better question identification

## Architecture

```
PDF Document → Page Extraction → Sliding Windows → Gemini API → Question Analysis → JSON Output
```

### Sliding Window Approach

For a PDF with pages 1, 2, 3, 4, 5:
- Window 1: Pages 1-3 (focus on page 1)
- Window 2: Pages 1-4 (focus on page 2) 
- Window 3: Pages 2-5 (focus on page 3)
- Window 4: Pages 3-5 (focus on page 4)
- Window 5: Pages 4-5 (focus on page 5)

This ensures each page is analyzed with context from adjacent pages.

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Vedantu-RAG-Pipeline
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and add your Google API key
   GOOGLE_API_KEY=your_actual_api_key_here
   ```

4. **Get Google API Key**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Add it to your `.env` file

## Usage

### Basic Usage

```python
from questions_ingestion_pipeline.main import PDFQuestionExtractor

# Initialize the extractor
extractor = PDFQuestionExtractor()

# Process a PDF
results = extractor.process_pdf("path/to/your/document.pdf", window_size=3)

# Save results
extractor.save_results(results, "output.json")
```

### Command Line Usage

```bash
# Run the example
python example_usage.py
```

### Advanced Usage

```python
from questions_ingestion_pipeline.main import PDFQuestionExtractor

# Initialize with custom API key
extractor = PDFQuestionExtractor(api_key="your_api_key")

# Process with custom window size
results = extractor.process_pdf(
    pdf_path="document.pdf",
    window_size=5  # Use 5-page windows instead of 3
)

# Access specific window results
for window_result in results['windows_results']:
    print(f"Window {window_result['window_id']}: {window_result['total_questions_found']} questions")
    for question in window_result['questions']:
        print(f"  - {question['question_text']}")
```

## Output Format

The system generates a comprehensive JSON output with the following structure:

```json
{
  "pdf_path": "path/to/document.pdf",
  "total_pages": 10,
  "window_size": 3,
  "total_windows": 10,
  "windows_results": [
    {
      "window_id": 1,
      "focus_page": 1,
      "page_range": "1-3",
      "total_pages_in_window": 3,
      "questions": [
        {
          "question_text": "What is the capital of France?",
          "question_type": "factual",
          "subject_topic": "geography",
          "difficulty_level": "beginner",
          "context": "European capitals section"
        }
      ],
      "summary": "Content summary for this window",
      "total_questions_found": 5
    }
  ],
  "summary_stats": {
    "total_questions_found": 47,
    "questions_by_type": {
      "multiple choice": 15,
      "short answer": 12,
      "essay": 8,
      "problem-solving": 12
    },
    "questions_by_difficulty": {
      "beginner": 18,
      "intermediate": 20,
      "advanced": 9
    }
  }
}
```

## Configuration

### Environment Variables

- `GOOGLE_API_KEY`: Required. Your Google API key for Gemini
- `LOG_LEVEL`: Optional. Logging level (INFO, DEBUG, WARNING, ERROR)

### Parameters

- `window_size`: Number of pages in each sliding window (default: 3)
- `temperature`: AI model temperature for response generation (default: 0.3)

## Error Handling

The system includes comprehensive error handling for:
- Missing API keys
- Invalid PDF files
- API rate limits
- Network connectivity issues
- Malformed responses

## Logging

The application provides detailed logging:
- Page extraction progress
- Window creation details
- API call status
- Question extraction results
- Error messages with context

## Dependencies

- `langchain-google-genai`: Google Gemini integration
- `PyPDF2`: PDF text extraction
- `python-dotenv`: Environment variable management
- `typing-extensions`: Type hint support

## Troubleshooting

### Common Issues

1. **API Key Error**
   ```
   Error: Google API key is required
   ```
   **Solution**: Add your Google API key to the `.env` file

2. **Import Errors**
   ```
   Import "langchain_google_genai" could not be resolved
   ```
   **Solution**: Install requirements: `pip install -r requirements.txt`

3. **PDF Reading Error**
   ```
   Error extracting text from PDF
   ```
   **Solution**: Ensure PDF is not password protected and is readable

4. **Rate Limiting**
   ```
   API rate limit exceeded
   ```
   **Solution**: Add delays between requests or reduce window size

### Performance Tips

- Use smaller window sizes for faster processing
- Process PDFs in batches for large documents
- Monitor API usage to stay within quotas
- Cache results to avoid reprocessing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or issues:
1. Check the troubleshooting section
2. Review the logs for error details
3. Create an issue on GitHub with detailed information
