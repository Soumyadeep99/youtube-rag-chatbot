import os
import time
import uuid

import numpy as np
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores.faiss import dependable_faiss_import
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


VECTOR_DB_DIR = "vector_db"

_vector_store_cache = {}


from langchain_huggingface import HuggingFaceEmbeddings

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )


def create_vector_store(transcript: str, video_id: str) -> FAISS:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=200
    )

    chunks = splitter.split_text(transcript)
    print(f"[VectorStore] Total chunks: {len(chunks)}")

    embeddings = get_embeddings()

    BATCH_SIZE = 5
    all_docs = [Document(page_content=chunk) for chunk in chunks]
    all_texts = [doc.page_content for doc in all_docs]

    all_embeddings = []
    total_batches = (len(all_texts) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(all_texts), BATCH_SIZE):
        batch = all_texts[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"[VectorStore] Embedding batch {batch_num}/{total_batches}")

        try:
            batch_embeddings = embeddings.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            print(f"[VectorStore] Batch error: {e}. Retrying after 30s...")
            time.sleep(30)
            batch_embeddings = embeddings.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)

        if i + BATCH_SIZE < len(all_texts):
            time.sleep(3)

    # Build FAISS index manually
    faiss = dependable_faiss_import()
    dimension = len(all_embeddings[0])
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(all_embeddings, dtype=np.float32))

    index_to_docstore_id = {i: str(uuid.uuid4()) for i in range(len(all_docs))}
    docstore = InMemoryDocstore({
        index_to_docstore_id[i]: all_docs[i]
        for i in range(len(all_docs))
    })

    vector_store = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id
    )

    save_path = os.path.join(VECTOR_DB_DIR, video_id)
    os.makedirs(save_path, exist_ok=True)
    vector_store.save_local(save_path)

    _vector_store_cache[video_id] = vector_store
    return vector_store


def load_vector_store(video_id: str) -> FAISS | None:
    if video_id in _vector_store_cache:
        return _vector_store_cache[video_id]

    save_path = os.path.join(VECTOR_DB_DIR, video_id)
    if not os.path.exists(save_path):
        return None

    embeddings = get_embeddings()
    vector_store = FAISS.load_local(
        save_path,
        embeddings,
        allow_dangerous_deserialization=True
    )

    _vector_store_cache[video_id] = vector_store
    return vector_store