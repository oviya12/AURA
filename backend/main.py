from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from dotenv import load_dotenv
import os
import shutil

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    question: str

# 1. Load Vector DB & Free HuggingFace Embeddings
persist_directory = "./db"
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
retriever = vector_db.as_retriever()

# 2. Setup Groq LLM (Free & Fast)
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY is missing. Add it to the .env file at the project root.")

llm = ChatGroq(
    groq_api_key=api_key,
    model_name="llama-3.3-70b-versatile",
    temperature=0
)

# 3. Conversational Memory Setup
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# 4. Modern Prompt Template with History
template = """You are AURA (Academic Unit Retrieval Assistant). 

Your goal is to help the user understand their notes and have a natural conversation.
1. If the user asks a follow-up question about something you just explained, use the Chat History to answer.
2. If the user asks a new question, search the Context (retrieved notes) for the answer.
3. If the information is not in the notes AND not in the chat history, then say you don't know.

Context:
{context}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", template),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])

# 5. The Chain Logic (Formatting docs + RAG)
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

base_chain = (
    {
        "context": (lambda x: x["question"]) | retriever | format_docs, 
        "question": lambda x: x["question"],
        "history": lambda x: x.get("history", []) # Add this line
    }
    | prompt
    | llm
    | StrOutputParser()
)

# 6. Final Stateful Chain
aura_with_history = RunnableWithMessageHistory(
    base_chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="history", # This must match variable_name="history" in prompt
)
# --- API Endpoints ---

@app.get("/")
def status():
    return {"status": "AURA System Online"}

@app.post("/chat")
async def chat_with_aura(query: Query):
    try:
        # We use a session_id to keep the chat history organized
        config = {"configurable": {"session_id": "default_user"}}
        response = aura_with_history.invoke(
            {"question": query.question},
            config=config
        )
        return {"answer": response}
    except Exception as e:
        return {"answer": f"AURA Error: {str(e)}"}

@app.post("/upload")
async def upload_notes(file: UploadFile = File(...)):
    try:
        os.makedirs("data", exist_ok=True)
        file_location = f"data/{file.filename}"
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Trigger the ingestion logic from your core folder
        from core.ingest import ingest_notes
        ingest_notes(file_location)
        
        return {"message": f"Successfully ingested {file.filename}"}
    except Exception as e:
        return {"message": f"Upload Failed: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)