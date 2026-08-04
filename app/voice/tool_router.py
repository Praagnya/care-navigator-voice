import asyncio
from google.genai import types
from tavily import TavilyClient
from app.config import get_settings

TAVILY_API_KEY = get_settings().tavily_api_key
tavily = TavilyClient(api_key=TAVILY_API_KEY)

async def route_tool_call(tool_call, session):
    for fn in tool_call.function_calls:
        print(f"Routing tool call: {fn.name}")
        if fn.name == "deep_research":
            await handle_deep_research(fn.id, fn.args, session)

async def handle_deep_research(call_id, args, session):
    # acknowledge immediately
    await session.send_tool_response(
        function_responses=[types.FunctionResponse(
            id=call_id,
            name="deep_research",
            response={"status": "Research has started and will take up to a minute. Keep chatting with the user meanwhile; present the findings naturally when they arrive as a follow-up result."}
        )]
    )
    asyncio.create_task(_run_and_deliver(call_id, args, session))


async def _run_and_deliver(call_id, args, session):
    # run tavily search
    results = await asyncio.to_thread(tavily.search, args["query"])
    await session.send_tool_response(
        function_responses=[types.FunctionResponse(
            id=call_id,
            name="deep_research",
            response=results,
            scheduling=types.FunctionResponseScheduling.INTERRUPT,
        )]
    )
