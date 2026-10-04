import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA

load_dotenv()

PERSIST_DIRECTORY = "./chroma_db"

def query_rag(question: str):
    if not os.path.exists(PERSIST_DIRECTORY):
        print("Vector store not found. Please run ingest.py first.")
        return
    
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )
    
    response = qa_chain.invoke({"query": question})
    print(f"Question: {question}\n")
    print(f"Answer: {response['result']}\n")
    print("Source Documents:")
    for doc in response['source_documents']:
        print(f"- {doc.page_content}")

if __name__ == "__main__":
    query_rag("What is LangChain?")
