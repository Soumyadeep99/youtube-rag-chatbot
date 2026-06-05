import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from rag.prompts import rag_prompt


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def format_chat_history(messages: list[dict]) -> str:
    """
    Converts last 10 messages into a readable string for the prompt.
    """
    recent = messages[-10:] if len(messages) > 10 else messages

    if not recent:
        return "No previous conversation."

    lines = []
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")

    return "\n".join(lines)


def get_llm():
    """
    Uses Groq LLaMA if GROQ_API_KEY is set (fast + free).
    Falls back to Gemini 2.0 Flash otherwise.
    """
    groq_key = os.getenv("GROQ_API_KEY")

    if groq_key:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            api_key=groq_key
        )

    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.2
    )


def create_rag_chain(retriever):
    llm = get_llm()

    chain = (
        {
            "context": RunnableLambda(lambda x: x["question"]) | retriever | RunnableLambda(format_docs),
            "question": RunnableLambda(lambda x: x["question"]),
            "chat_history": RunnableLambda(lambda x: format_chat_history(x["chat_history"]))
        }
        | rag_prompt
        | llm
        | StrOutputParser()
    )

    return chain