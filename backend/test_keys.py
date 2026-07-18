import os
from dotenv import load_dotenv
load_dotenv(".env")

from langchain_groq import ChatGroq
from langchain_cohere import CohereEmbeddings

print("Testing Groq...")
try:
    llm = ChatGroq(api_key=os.environ.get("GROQ_API_KEY"), model_name="llama-3.3-70b-versatile")
    llm.invoke("Hi")
    print("Groq is OK")
except Exception as e:
    print(f"Groq Error: {type(e).__name__} - {e}")

print("Testing Cohere...")
try:
    embeddings = CohereEmbeddings(cohere_api_key=os.environ.get("COHERE_API_KEY"), model="embed-english-light-v3.0")
    embeddings.embed_query("Hi")
    print("Cohere is OK")
except Exception as e:
    print(f"Cohere Error: {type(e).__name__} - {e}")
