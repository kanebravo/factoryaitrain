import os
from dotenv import load_dotenv

class AgentBase:
    def __init__(self, model_name: str = "openai:gpt-3.5-turbo"):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key: # Ensure API key is loaded, pydantic_ai.Agent will use it
            raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in a .env file.")
        self.model_name = model_name # e.g., "openai:gpt-3.5-turbo"
        # The actual pydantic_ai.Agent will be initialized in the subclass

# Example of how other agents might inherit or use this
# class SpecificAgent(AgentBase):
#     def __init__(self):
#         super().__init__()
#         # Now self.llm is initialized and ready to use
