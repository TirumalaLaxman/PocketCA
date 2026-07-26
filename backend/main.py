import os
from pathlib import Path
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from prompts import SYSTEM_PROMPT

# Load .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GOOGLE_API_KEY")

print("API Loaded:", api_key is not None)

app = FastAPI(title="PocketCA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=api_key,
    temperature=0.3,
)

memory = ConversationBufferMemory(
    return_messages=True
)

conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=False
)
class ChatRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {"status": "PocketCA Running"}


@app.post("/chat")
@app.post("/chat")
def chat(data: ChatRequest):

    answer = conversation.predict(
        input=data.question
    )

    return {
        "answer": answer
    }