"""Simple chat interface for the Campus Knowledge Assistant."""

import streamlit as st

from src.ingest import ROOT
from src.rag import answer_question
from src.display import group_citations

st.set_page_config(page_title="Campus Knowledge Assistant", page_icon="🎓")
st.title("🎓 Campus Knowledge Assistant")
st.caption("Ask questions from your indexed campus PDFs. Answers are generated with Groq.")

if "messages" not in st.session_state:
    st.session_state.messages = []


def show_sources(citations, message_number):
    for item in group_citations(citations):
        filename = item["filename"]
        page = item["page"]
        numbers = ", ".join(f"[{n}]" for n in item["numbers"])
        with st.expander(f"{numbers} {filename} — PDF page {page}"):
            st.write(item["text"])
            pdf = ROOT / "data" / "raw" / filename
            if pdf.is_file():
                st.download_button(
                    "Download source PDF",
                    data=pdf.read_bytes(),
                    file_name=filename,
                    mime="application/pdf",
                    key=f"pdf-{message_number}-{filename}-{page}",
                )


for index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message.get("citations"):
            show_sources(message["citations"], index)

question = st.chat_input("Ask a question about placements or campus policies...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching PDFs and generating answer..."):
            try:
                answer, citations = answer_question(question)
                st.write(answer)
                if citations:
                    show_sources(citations, len(st.session_state.messages))
            except Exception as error:
                st.error(f"Could not generate an answer: {error}")
                st.stop()

    st.session_state.messages.append({
        "role": "assistant", "content": answer, "citations": citations,
    })
