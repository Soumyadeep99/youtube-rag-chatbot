from langchain_core.prompts import ChatPromptTemplate

rag_prompt = ChatPromptTemplate.from_template(
    """
You are a helpful YouTube video assistant.

Use the chat history and transcript context below to answer the user's question.
If the answer cannot be found in either, say:
"I don't know based on the video transcript."

Chat History:
{chat_history}

Transcript Context:
{context}

Question:
{question}

Answer:
"""
)