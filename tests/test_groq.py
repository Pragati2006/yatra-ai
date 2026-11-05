import os
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("GROQ_API_KEY is missing from .env")
    else:
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0.2,
            api_key=api_key,
        )

        response = llm.invoke(
            "A family of 4 wants to visit Vaishno Devi from Bhopal "
            "for 3 days. They prefer travelling by train. "
            "Suggest a simple travel plan."
        )

        print("\n===== GROQ RESPONSE =====\n")
        print(response.content)
