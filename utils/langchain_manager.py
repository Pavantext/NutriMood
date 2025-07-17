import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_weaviate import WeaviateVectorStore
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
import weaviate
from weaviate.classes.init import Auth
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt.memory import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from typing import Dict

load_dotenv()

class LangChainManager:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.7,
            max_output_tokens=1024
        )
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.weaviate_client = weaviate.connect_to_weaviate_cloud(
            cluster_url=os.getenv("WEAVIATE_URL"),
            auth_credentials=Auth.api_key(os.getenv("WEAVIATE_API_KEY")),
        )
        self.class_name = "FoodItem"
        self.vectorstore = WeaviateVectorStore(
            client=self.weaviate_client,
            index_name=self.class_name,
            text_key="description",
            embedding=self.embeddings
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a friendly, expert food assistant. Your job is to recommend food that matches the user's preferences, context, and mood, and to explain your reasoning in a conversational way. If the user's request implies a preference (e.g., 'something light', 'good for a cold day', 'healthy', 'good for weight loss'), infer the underlying need and recommend accordingly. If the user has health or calorie concerns (even implied), address them in your response. Avoid repeating recent recommendations unless specifically requested. Respond in a natural, conversational tone."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
            ("system", "Here are some relevant food items from the menu:\n{context}")
        ])

        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            combine_docs_chain_kwargs={"prompt": self.prompt}
        )

        # In-memory store for per-user chat histories
        self._store: Dict[str, ChatMessageHistory] = {}

        def get_session_history(session_id: str):
            if session_id not in self._store:
                self._store[session_id] = ChatMessageHistory()
            return self._store[session_id]

        # Wrap the chain with LangGraph message history
        self.runnable = RunnableWithMessageHistory(
            self.chain,
            get_session_history,
            input_messages_key="question",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

    def ask(self, question: str, session_id: str):
        # session_id should be unique per user (e.g., username)
        result = self.runnable.invoke(
            {"question": question},
            config={"configurable": {"session_id": session_id}}
        )
        return result 