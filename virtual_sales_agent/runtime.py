from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages.tool import ToolMessage

from virtual_sales_agent.graph import graph


class AgentRuntime:
    registry = {}

    @classmethod
    def get_or_create(cls, customer_id: str, thread_id: str):
        key = (customer_id, thread_id)
        runtime = cls.registry.get(key)
        if runtime is None:
            runtime = cls(customer_id, thread_id)
            cls.registry[key] = runtime
        return runtime

    def __init__(self, customer_id: str, thread_id: str):
        self.config = {
            "configurable": {
                "customer_id": customer_id,
                "thread_id": thread_id,
            }
        }

    def _empty_response(self) -> dict:
        response = {
            "thread_id": self.config["configurable"]["thread_id"],
            "status": "ok",
            "assistant_message": "",
            "tool_call": None,
            "error": None,
        }
        return response

    def chat(self, message: str) -> dict:
        request = {"messages": [HumanMessage(content=message)]}
        events = list(graph.stream(request, self.config, stream_mode="values"))

        last_event = events[-1]
        messages = last_event["messages"]
        last_message = messages[-1]

        response = self._empty_response()
        if isinstance(last_message, AIMessage):
            response["assistant_message"] = last_message.content or ""

        tool_calls = getattr(last_message, "tool_calls", None)
        if not tool_calls:
            return response

        snapshot = graph.get_state(self.config)
        if snapshot.next:
            response["status"] = "needs_approval"
            response["tool_call"] = tool_calls[0]

        return response

    def approve(self) -> dict:
        result = graph.invoke(None, self.config)
        messages = result["messages"]
        last_message = messages[-1]

        response = self._empty_response()
        if isinstance(last_message, AIMessage):
            response["assistant_message"] = last_message.content or ""
        return response

    def deny(self, reason: str) -> dict:
        snapshot = graph.get_state(self.config)
        messages = snapshot.values["messages"]
        last_message = messages[-1]

        tool_call = last_message.tool_calls[0]
        tool_message = ToolMessage(
            tool_call_id=tool_call["id"],
            content=(
                "API call denied by user. "
                f"Reasoning: '{reason}'. Continue assisting, accounting for the user's input."
            ),
        )
        invoke_payload = {"messages": [tool_message]}
        result = graph.invoke(invoke_payload, self.config)

        result_messages = result["messages"]
        final_message = result_messages[-1]

        response = self._empty_response()
        if isinstance(final_message, AIMessage):
            response["assistant_message"] = final_message.content or ""
        return response
