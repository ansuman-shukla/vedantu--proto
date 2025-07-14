# 📚 Vedantu RAG Pipeline - Question Generator

A simple Streamlit application that takes user queries and generates structured educational questions with detailed classifications using LangChain and OpenAI.

## ✨ Features

- **Query Input**: Enter any educational query or topic
- **AI-Powered Question Generation**: Uses OpenAI GPT to create relevant questions
- **Structured Output**: Automatically classifies questions with:
  - Class/Grade level
  - Subject identification
  - Topic classification
  - Difficulty assessment
  - Learning objectives
  - Relevant keywords
- **Visual Display**: Beautiful, organized interface to view results
- **Export Options**: Save and download results as JSON files

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- OpenAI API key

### Installation

1. **Clone/Download the repository**
   ```bash
   cd Vedantu-RAG-Pipeline
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your OpenAI API key**
   - Copy `.env.example` to `.env`
   ```bash
   cp .env.example .env
   ```
   - Open the `.env` file and replace `your_openai_api_key_here` with your actual OpenAI API key
   - Save the file

4. **Run the application**
   ```bash
   streamlit run main.py
   ```

5. **Open in browser**
   - The app will automatically open in your default browser
   - Usually runs on `http://localhost:8501`

## 🎯 How to Use

1. **Enter API Key**: In the sidebar, enter your OpenAI API key
2. **Input Query**: Type your educational query in the text area
3. **Generate**: Click the "Generate Question" button
4. **View Results**: See the structured output with all classifications
5. **Save/Download**: Optionally save results to a file

### Example Queries

- "Explain photosynthesis process in plants"
- "Solve quadratic equations with examples"
- "What is the French Revolution?"
- "Basics of molecular biology"
- "Introduction to calculus derivatives"

## 📊 Output Structure

The application generates structured output in the following format:

```json
{
  "question": "Generated educational question",
  "class": "Grade/Class level",
  "subject": "Subject name",
  "topic": "Specific topic",
  "difficulty": "Easy/Medium/Hard",
  "learning_objective": "What students should learn",
  "keywords": "Relevant keywords"
}
```

## 🛠️ Technical Stack

- **Frontend**: Streamlit
- **AI/ML**: LangChain + OpenAI GPT-3.5-turbo
- **Language**: Python 3.8+
- **Data Format**: JSON

## 📋 Dependencies

- `streamlit`: Web application framework
- `langchain`: LLM application framework
- `langchain-openai`: OpenAI integration for LangChain
- `openai`: OpenAI API client
- `python-dotenv`: Environment variable management

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:
```
OPENAI_API_KEY=your_api_key_here
```

### Customization

You can modify the prompt template in `main.py` to:
- Change the output format
- Add more classification fields
- Adjust the AI model behavior
- Modify difficulty levels

## 🚨 Troubleshooting

### Common Issues

1. **API Key Error**: Make sure your OpenAI API key is valid and has credits
2. **Import Errors**: Ensure all dependencies are installed: `pip install -r requirements.txt`
3. **Port Issues**: If port 8501 is busy, Streamlit will use the next available port

### Error Messages

- **"Please enter your OpenAI API key"**: Add your API key in the sidebar
- **"Please enter a query"**: The input field cannot be empty
- **"Error generating question"**: Check your API key and internet connection

## 📈 Future Enhancements

- [ ] Support for multiple AI models
- [ ] Question difficulty prediction
- [ ] Batch processing of queries
- [ ] Integration with educational databases
- [ ] Multi-language support
- [ ] Question bank storage

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve this application!

---

**Made with ❤️ for educational technology**