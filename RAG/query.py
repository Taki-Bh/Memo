 import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

COLLECTION_NAME = "rag_collection"
QDRANT_PATH = "./qdrant_db"

def query_rag(question: str):
    if not os.path.exists(QDRANT_PATH):
        print("Qdrant vector store not found. Please run ingest.py first.")
        return
    
    embeddings = OpenAIEmbeddings()
    client = QdrantClient(path=QDRANT_PATH)
    
    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
    
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    
    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know.\n\n"
        "{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    
    response = rag_chain.invoke({"input": question})
    print(f"Question: {question}\n")
    print(f"Answer: {response['answer']}\n")
    print("Source Documents:")
    for doc in response['context']:
        print(f"- {doc.page_content}")

if __name__ == "__main__":
    query_rag("What is LangChain?")
