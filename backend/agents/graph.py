from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from agents.prompts import SYSTEM_PROMPT
from agents.tools import ALL_TOOLS


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def create_graph():
    llm = ChatOpenAI(model="gpt-4.1", temperature=0, streaming=True)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    async def agent_node(state: AgentState):
        messages = state["messages"]
        # Inject system prompt if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(ALL_TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()
