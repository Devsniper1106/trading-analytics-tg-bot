from llama_index.core import SummaryIndex
from llama_index.readers.mongodb import SimpleMongoReader
from llama_index.llms.openai import OpenAI
from datetime import datetime
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Initialize LLM with better error handling
llm = OpenAI(
        model="gpt-4o-mini",  # Using standard gpt-4o-mini model
        api_key=os.getenv("OPENAI_API_KEY"),
        max_output_tokens=500,
        temperature=0.7  # Add temperature for better response variety
    )
mongo_uri = os.getenv("MONGO_URI")
db_name = "telegram_bot_db"
collection_name = "token_contracts_analytics_data"

host = mongo_uri
port = 27017
field_names = [
    "token_contracts",
    "mentioned_lastdate",
    "total_mentions",
    "daily_mentions",
    "token_analytics_data"
]

reader = SimpleMongoReader(host, port)

documents = reader.load_data(
            db_name, collection_name, field_names
)

async def ai_insight():
    try:
        prompt = f"""Today's date is {datetime.now().strftime('%d/%m/%Y')}.\n
               You serve as a crypto advisor for daily reports, focusing on unusual token patterns, daily mentions, price changes, buyers, and volume trends to deliver actionable investment insights.
provide advanced AI for pattern recognition to deliver high-quality insights and predictions.
                   Here are examples:  
                Example 1: "Noted an unusual spike in [token name] mentions on [chain] over the last [hours], with a [percent]% increase in volume. Consider this token!"  
                Example 2: "There’s an upward trend in mentions and liquidity for [token name]. Similar tokens have historically risen by [percent]% - [percent]% in the past [hours]."  
                Include:  
                - Analysis date  
                - Token contract address with red color  
                - URLs (X, Telegram, origin, dex, if available and ignore #)  
                Format response in Markdown under 600 characters.
                """

        # Initialize index with callback manager
        index = SummaryIndex.from_documents(
            documents,
        )
        # Configure query engine with streaming and response mode
        query_engine = index.as_query_engine(
            llm=llm,
            streaming=True,
            response_mode="compact"
        )

        start_time = datetime.now()

        response = await query_engine.aquery(prompt)

        end_time = datetime.now()
        print(f"Query response received in {end_time - start_time} seconds.")
        
        return response

    except Exception as e:
        print(f"An error occurred: {e}")
        return "An error occurred while processing your request."

if __name__ == "__main__":
    response=asyncio.run(ai_insight())
    print(f"Query response received.-----------:{response}")