from langgraph.types import RunnableConfig, StreamWriter
from src.agents.state import AgentState
from src.agents.llm import client, HAIKU_MODEL


def make_classify_intent_node(intent_labels: list[str]):
    labels_str = " | ".join(intent_labels)

    async def classify_intent(
        state: AgentState,
        writer: StreamWriter,
        config: RunnableConfig,
    ) -> dict:
        user_message = ""
        for msg in reversed(state["messages"]):
            if msg["role"] == "user":
                for block in msg.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        user_message = block["text"]
                        break
                break

        if not user_message:
            return {"intent": "GENERAL", "assembled_prompt": ""}

        try:
            resp = await client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=20,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Classify the user's message into exactly one label. Reply with the label only.\n"
                        f"Labels: {labels_str}\n\n"
                        f'User message: "{user_message}"\nLabel:'
                    ),
                }],
            )
            result = resp.content[0].text.strip().split()[0]
            intent = result if result in intent_labels else "GENERAL"
        except Exception:
            intent = "GENERAL"

        return {"intent": intent, "assembled_prompt": ""}

    return classify_intent
