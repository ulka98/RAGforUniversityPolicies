# University Policy RAG System

A simple Retrieval-Augmented Generation (RAG) system for querying university policies and getting AI-generated answers based on the content of policy documents.

## Overview

This system helps users find information from university policy documents without having to manually search through them. It uses vector embeddings to match questions with relevant policy sections, then generates human-readable answers using AI.

## Features

- Loads university policy documents from JSON files
- Creates vector embeddings for semantic search
- Retrieves the most relevant policy sections based on user queries
- Generates comprehensive answers from the relevant policies
- Provides source citations for verification

## Requirements

- Python 3.7+
- Required Python packages:
  - transformers
  - torch
  - sentence-transformers
  - faiss-cpu
  - numpy
  - vertexai
  - Google Cloud access for Vertex AI

## Installation

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Ensure you have proper Google Cloud credentials set up for Vertex AI

## Usage

1. Add your university policy JSON files to the `manuals` folder (the system will create this folder if it doesn't exist)
2. Each JSON file should contain policy documents in the following format:
   ```json
   [
     {
       "title": "Policy Title",
       "content": "Full text of the policy...",
       "url": "https://university.edu/policies/policy-page"
     },
     ...
   ]
   ```
3. Run the main script:
   ```
   python university_policy_rag.py
   ```
4. The system will automatically:
   - Load policy documents
   - Create embeddings
   - Answer example questions
   
5. To use in your own code:
   ```python
   # Import necessary functions
   from university_policy_rag import load_and_prepare_rag, answer_question
   
   # Initialize the RAG system
   folder_path = "manuals"
   chunks, model, embeddings, faiss_index = load_and_prepare_rag(folder_path)
   
   # Ask a question
   question = "What is the policy on protests and demonstrations?"
   answer, sources = answer_question(question, chunks, model, faiss_index)
   
   # Print the answer
   print(answer)
   
   # Print the sources
   for source in sources:
       print(f"- {source['title']} ({source['url']})")
   ```

## How It Works

1. **Loading Data**: The system loads JSON files containing university policies.
2. **Creating Embeddings**: It uses sentence-transformers to create vector embeddings for each policy chunk.
3. **Semantic Search**: When a question is asked, the system finds the most semantically similar policy sections.
4. **Answer Generation**: It uses Vertex AI's Gemini model to generate an answer based on the relevant policy sections.
5. **Source Citation**: The system provides the sources of the information for verification.

## Example Questions

The system comes with some example questions:
- "What is the policy on protests and demonstrations?"
- "Can I post flyers anonymously on campus?"
- "What happens if I don't follow a staff member's instructions?"

## Customization

- Adjust the `top_k` parameter in `answer_question()` to retrieve more or fewer relevant policy sections
- Modify the `generate_answer()` function to use different prompt templates or generation parameters
- Add your own example questions in the main section of the script

## License

[Add your preferred license here]

## Acknowledgments

This project uses the following open-source libraries:
- sentence-transformers for embeddings
- FAISS for efficient similarity search
- Vertex AI for text generation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
