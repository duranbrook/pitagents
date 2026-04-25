from langgraph.types import RunnableConfig, StreamWriter
from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.agents.state import AgentState
from src.db.qdrant import qdrant, embed


def make_assemble_prompt_node(prompt_blocks: dict[str, str]):

    async def assemble_prompt(
        state: AgentState,
        writer: StreamWriter,
        config: RunnableConfig,
    ) -> dict:
        intent = state.get("intent", "GENERAL")

        # Part A: static blocks
        parts = [prompt_blocks.get("base", "")]
        if intent in prompt_blocks and intent != "base":
            parts.append(prompt_blocks[intent])

        # Part B: semantic few-shots from Qdrant
        try:
            user_message = ""
            for msg in reversed(state["messages"]):
                if msg["role"] == "user":
                    for block in msg.get("content", []):
                        if isinstance(block, dict) and block.get("type") == "text":
                            user_message = block["text"]
                            break
                    break

            if user_message:
                query_vector = await embed(user_message)
                hits = await qdrant.search(
                    collection_name="few_shots",
                    query_vector=query_vector,
                    query_filter=Filter(
                        must=[FieldCondition(key="intent", match=MatchValue(value=intent))]
                    ),
                    limit=3,
                )
                if hits:
                    examples = "\n\n".join(
                        f"<example>\nUser: {h.payload['question']}\n"
                        f"Assistant: {h.payload['ideal_response']}\n</example>"
                        for h in hits
                    )
                    parts.append(f"Examples of ideal responses:\n{examples}")
        except Exception:
            pass  # Qdrant unavailable — fall back to static blocks only

        assembled = "\n\n".join(p for p in parts if p)
        return {"assembled_prompt": assembled}

    return assemble_prompt
