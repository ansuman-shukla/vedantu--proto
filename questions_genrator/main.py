import streamlit as st
import json
import os
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class QuestionStructure(BaseModel):
    """Structured model for educational question generation"""
    question: str = Field(description="Generated educational question based on the user query")
    class_level: str = Field(description="Grade/Class level (e.g., Class 10, Grade 12, College)", alias="class")
    subject: str = Field(description="Subject name (e.g., Mathematics, Physics, Chemistry, Biology, English, History)")
    topic: str = Field(description="Specific topic within the subject")
    board: str = Field(description="Education board in India (e.g., CBSE, ICSE, State Board, IB, CAIE, NIOS)")
    difficulty: str = Field(description="Difficulty level: Easy, Medium, or Hard")
    concepts: List[str] = Field(description="List of key concepts that will be used to solve this question")
    prerequisites: List[str] = Field(description="List of prerequisite knowledge/concepts needed to understand and solve this question")
    learning_objective: str = Field(description="What students should learn from this question")
    keywords: List[str] = Field(description="List of relevant keywords for the question")

def create_question_generator():
    """Create and configure the question generation chain"""
    
    # Initialize the OpenAI LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create the Pydantic output parser
    parser = PydanticOutputParser(pydantic_object=QuestionStructure)
    
    # Create the prompt template with format instructions
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are an educational expert based in India who analyzes queries and generates structured educational content.

        Given a user query, you need to:
        1. Generate a relevant educational question based on the query
        2. Classify the question with appropriate metadata
        
        For the BOARD field, you MUST choose ONLY from these Indian education boards:
        
        **National Boards:**
        - CBSE (Central Board of Secondary Education)
        - ICSE (Indian Certificate of Secondary Education) 
        - ISC (Indian School Certificate)
        - NIOS (National Institute of Open Schooling)
        
        **International Boards (in India):**
        - IB (International Baccalaureate)
        - CAIE (Cambridge Assessment International Education)
        
        **State Boards:**
        - Maharashtra State Board
        - Karnataka State Board
        - Andhra Pradesh State Board
        - Uttar Pradesh State Board
        - West Bengal State Board
        - Gujarat State Board
        - Tamil Nadu State Board
        - Rajasthan State Board
        - Madhya Pradesh State Board
        - Bihar State Board
        - Assam State Board
        - Or any other specific state board (mention the state name + "State Board")
        
        Choose the most appropriate board based on the content level, subject, and typical curriculum alignment.
        
        Make sure to provide appropriate educational classifications based on the content and complexity of the query.
        
        {format_instructions}"""),
        ("human", "User Query: {query}")
    ])
    
    # Create the chain with structured output
    chain = prompt_template | llm | parser
    
    return chain

def display_structured_output(data: QuestionStructure):
    """Display the structured output in a visually appealing format"""
    
    # Main question display
    st.markdown("### 📚 Generated Question")
    st.markdown(f"**{data.question}**")
    
    # Create columns for metadata
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🎓 Academic Details")
        st.info(f"**Class:** {data.class_level}")
        st.info(f"**Subject:** {data.subject}")
        st.info(f"**Board:** {data.board}")
    
    with col2:
        st.markdown("#### 📖 Content Details")
        st.success(f"**Topic:** {data.topic}")
        st.warning(f"**Difficulty:** {data.difficulty}")
    
    with col3:
        st.markdown("#### 🎯 Learning Info")
        if data.keywords and len(data.keywords) > 0:
            keywords_str = ", ".join(data.keywords)
            st.success(f"**Keywords:** {keywords_str}")
        else:
            st.info("**Keywords:** No keywords specified")
    
    # Learning objective
    st.markdown("#### 💡 Learning Objective")
    st.markdown(f"*{data.learning_objective}*")
    
    # New sections for concepts and prerequisites
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🧠 Key Concepts")
        if data.concepts and len(data.concepts) > 0:
            for concept in data.concepts:
                st.markdown(f"• {concept}")
        else:
            st.info("No key concepts specified")
    
    with col2:
        st.markdown("#### 📋 Prerequisites")
        if data.prerequisites and len(data.prerequisites) > 0:
            for prerequisite in data.prerequisites:
                st.markdown(f"• {prerequisite}")
        else:
            st.info("No prerequisites specified")
    
    # Display raw data in expander
    with st.expander("📋 View Raw Data"):
        st.json(data.model_dump())

def main():
    # Page configuration
    st.set_page_config(
        page_title="Vedantu Question Generator",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Check if API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Title and description
    st.title("📚 Vedantu - Question Generator")
    st.markdown("---")
    st.markdown("Enter a query below and get a structured educational question with detailed classifications!")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key status
        if api_key:
            st.success("✅ OpenAI API Key loaded from environment")
        else:
            st.error("❌ OpenAI API Key not found in environment")
            st.info("💡 Please add OPENAI_API_KEY to your .env file")
        
        st.markdown("---")
        st.markdown("### 📝 How it works:")
        st.markdown("""
        1. Enter your educational query
        2. Click 'Generate Question'
        3. Get structured output with:
           - Generated question
           - Class/Grade level
           - Subject classification
           - Education board (CBSE, ICSE, State boards, etc.)
           - Topic identification
           - Difficulty assessment
           - Key concepts used to solve the question
           - Prerequisite knowledge required
           - Learning objectives
           - Relevant keywords
        """)
    
    # Main interface
    if api_key:
        # Query input
        st.markdown("### 🔍 Enter Your Query")
        query = st.text_area(
            "",
            placeholder="e.g., 'Explain photosynthesis process in plants' or 'Solve quadratic equations with examples'",
            height=100
        )
        
        # Generate button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            generate_btn = st.button("🚀 Generate Question", type="primary", use_container_width=True)
        
        # Process query
        if generate_btn and query.strip():
            try:
                with st.spinner("🔄 Generating structured question..."):
                    # Create question generator
                    question_chain = create_question_generator()
                    
                    # Create parser for format instructions
                    parser = PydanticOutputParser(pydantic_object=QuestionStructure)
                    
                    # Generate structured output
                    result = question_chain.invoke({
                        "query": query,
                        "format_instructions": parser.get_format_instructions()
                    })
                    
                    # Display results
                    st.markdown("---")

                    display_structured_output(result)
                    
                    # Save option
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Save to File"):
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"question_output_{timestamp}.json"
                            with open(filename, 'w') as f:
                                json.dump(result.model_dump(), f, indent=2)
                            st.success(f"✅ Saved as {filename}")
                    
                    with col2:
                        # Download button
                        json_str = json.dumps(result.model_dump(), indent=2)
                        st.download_button(
                            label="📥 Download JSON",
                            data=json_str,
                            file_name=f"question_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                        
            except Exception as e:
                st.error(f"❌ Error generating question: {str(e)}")
                st.info("💡 Please check your API key and try again")
        
        elif generate_btn and not query.strip():
            st.warning("⚠️ Please enter a query to generate a question!")
    
    else:
        st.info("� Please add your OpenAI API key to the .env file to get started")
        st.markdown("### 🔧 Setup Instructions:")
        st.markdown("""
        1. Create a `.env` file in your project directory
        2. Add your OpenAI API key: `OPENAI_API_KEY=your_api_key_here`
        3. Restart the application
        """)

if __name__ == "__main__":
    main()