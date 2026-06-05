import warnings
warnings.filterwarnings("ignore")
import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from auth.auth import register_user, verify_otp_code, login_user
from rag.transcript import extract_video_id, get_transcript, get_video_title
from rag.vectorstore import create_vector_store, load_vector_store
from rag.chains import create_rag_chain
from db.database import (
    create_tables,
    create_chat,
    save_message,
    get_user_chats,
    get_chat_messages,
    update_chat_title,
    delete_chat
)

create_tables()

st.set_page_config(
    page_title="YouTube RAG Chatbot",
    page_icon="🎥",
    layout="wide"
)


def init_session():
    defaults = {
        "user": None,
        "page": "login",
        "reg_email": None,
        "chat_id": None,
        "video_id": None,
        "chain": None,
        "messages": [],
        "editing_title": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()


def logout():
    for key in ["user", "chat_id", "video_id", "chain", "messages", "editing_title"]:
        st.session_state[key] = None
    st.session_state.messages = []
    st.session_state.page = "login"


def page_login():
    st.title("🎥 YouTube RAG Chatbot")
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", use_container_width=True):
        if not email or not password:
            st.warning("Please fill in all fields.")
        else:
            result = login_user(email, password)
            if result["success"]:
                st.session_state.user = result["user"]
                st.session_state.page = "chat"
                st.rerun()
            else:
                st.error(result["message"])

    st.divider()
    st.write("Don't have an account?")
    if st.button("Register", use_container_width=True):
        st.session_state.page = "register"
        st.rerun()


def page_register():
    st.title("🎥 YouTube RAG Chatbot")
    st.subheader("Create Account")
    email = st.text_input("Email", key="reg_email_input")
    password = st.text_input("Password", type="password", key="reg_password")
    confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")

    if st.button("Register", use_container_width=True):
        if not email or not password or not confirm:
            st.warning("Please fill in all fields.")
        elif password != confirm:
            st.error("Passwords do not match.")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            result = register_user(email, password)
            if result["success"]:
                st.session_state.reg_email = email
                st.session_state.page = "verify_otp"
                st.success(result["message"])
                st.rerun()
            else:
                st.error(result["message"])

    st.divider()
    st.write("Already have an account?")
    if st.button("Back to Login", use_container_width=True):
        st.session_state.page = "login"
        st.rerun()


def page_verify_otp():
    st.title("🎥 YouTube RAG Chatbot")
    st.subheader("Verify Your Email")
    email = st.session_state.reg_email
    st.info(f"A 6-digit OTP was sent to **{email}**")
    otp_input = st.text_input("Enter OTP", max_chars=6, placeholder="e.g. 482910", key="otp_input")

    if st.button("Verify OTP", use_container_width=True):
        if not otp_input:
            st.warning("Please enter the OTP.")
        else:
            result = verify_otp_code(email, otp_input)
            if result["success"]:
                st.success(result["message"])
                st.session_state.page = "login"
                st.rerun()
            else:
                st.error(result["message"])

    st.divider()
    if st.button("Back to Register", use_container_width=True):
        st.session_state.page = "register"
        st.rerun()


def page_chat():
    user = st.session_state.user

    with st.sidebar:
        st.markdown(f"👤 **{user['email']}**")
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()

        st.divider()
        st.title("💬 Your Chats")

        chats = get_user_chats(user["id"])

        for chat in chats:
            chat_id, video_id, title, created_at = chat
            col1, col2, col3 = st.columns([6, 1, 1])

            if st.session_state.editing_title == chat_id:
                new_title = st.text_input(
                    "Rename", value=title,
                    key=f"rename_{chat_id}",
                    label_visibility="collapsed"
                )
                if st.button("✅", key=f"save_{chat_id}"):
                    if new_title.strip():
                        update_chat_title(chat_id, new_title.strip())
                    st.session_state.editing_title = None
                    st.rerun()
            else:
                with col1:
                    if st.button(title, key=f"chat_{chat_id}", use_container_width=True):
                        st.session_state.chat_id = chat_id
                        st.session_state.video_id = video_id
                        messages = get_chat_messages(chat_id)
                        st.session_state.messages = [
                            {"role": role, "content": content}
                            for role, content in messages
                        ]
                        vector_store = load_vector_store(video_id)
                        if vector_store is None:
                            st.warning("Vector store not found. Please reprocess the video.")
                            st.session_state.chain = None
                        else:
                            retriever = vector_store.as_retriever(
                                search_type="similarity",
                                search_kwargs={"k": 4}
                            )
                            st.session_state.chain = create_rag_chain(retriever)
                        st.rerun()

                with col2:
                    if st.button("✏️", key=f"edit_{chat_id}"):
                        st.session_state.editing_title = chat_id
                        st.rerun()

                with col3:
                    if st.button("🗑️", key=f"del_{chat_id}"):
                        delete_chat(chat_id)
                        if st.session_state.chat_id == chat_id:
                            st.session_state.chat_id = None
                            st.session_state.video_id = None
                            st.session_state.chain = None
                            st.session_state.messages = []
                        st.rerun()

        st.divider()

    st.title("🎥 YouTube RAG Chatbot")
    youtube_url = st.text_input("Enter YouTube URL")

    if st.button("Process Video"):
        if not youtube_url:
            st.warning("Please enter a YouTube URL.")
        else:
            with st.spinner("Processing video..."):
                video_id = extract_video_id(youtube_url)
                if not video_id:
                    st.error("Invalid YouTube URL.")
                    st.stop()

                transcript = get_transcript(video_id)
                if transcript is None:
                    st.error("Could not retrieve or generate a transcript for this video.")
                    st.stop()

                vector_store = load_vector_store(video_id)
                if vector_store is None:
                    vector_store = create_vector_store(transcript, video_id)

                retriever = vector_store.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 4}
                )
                chain = create_rag_chain(retriever)

            with st.spinner("Fetching video title..."):
                title = get_video_title(video_id)

            chat_id = create_chat(user["id"], video_id, title)
            st.session_state.chat_id = chat_id
            st.session_state.video_id = video_id
            st.session_state.chain = chain
            st.session_state.messages = []
            st.success(f"✅ Video processed: **{title}**")
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question about the video..."):
        if st.session_state.chain is None:
            st.warning("Process a video first.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        save_message(st.session_state.chat_id, "user", prompt)

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = st.session_state.chain.invoke({
                    "question": prompt,
                    "chat_history": st.session_state.messages[:-1]
                })
                st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        save_message(st.session_state.chat_id, "assistant", response)


page = st.session_state.page

if page == "login":
    page_login()
elif page == "register":
    page_register()
elif page == "verify_otp":
    page_verify_otp()
elif page == "chat":
    if st.session_state.user is None:
        st.session_state.page = "login"
        st.rerun()
    else:
        page_chat()