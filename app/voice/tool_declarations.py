
from google.genai import types

RESEARCH_INSTRUCTIONS = """Use this tool when the user asks about a specific hospital or healthcare facility and wants reviews, patient experiences, or reputation
   information. Returns a research summary from web sources"""

DEEP_RESEARCH_DECLARATION = types.FunctionDeclaration(
      name="deep_research",
      description=RESEARCH_INSTRUCTIONS,
      parameters=types.Schema(
          type=types.Type.OBJECT,
          properties={
              "query": types.Schema(
                  type=types.Type.STRING,
                  description="The research query about the hospital or facility.",
              ),
          },
          required=["query"],
      ),
  )

TOOL_DECLARATIONS = [DEEP_RESEARCH_DECLARATION]