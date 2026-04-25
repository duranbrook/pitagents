import logging
from langgraph.types import RunnableConfig, StreamWriter
from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.agents.state import AgentState
from src.agents.llm import client, HAIKU_MODEL, MODEL, MAX_TOKENS
from src.db.qdrant import qdrant, embed

logger = logging.getLogger(__name__)

_SIMILARITY_BAD_THRESHOLD = 0.92
_SIMILARITY_GOOD_THRESHOLD = 0.70
_FEEDBACK_CRITIC_MIN_ENTRIES = 50


async def _qa_check(intent: str, user_message: str, response_text: str) -> str:
    prompt = (
        f"You are a QA reviewer for an auto shop AI assistant.\n"
        f"The assistant responded to a user with intent: {intent}\n\n"
        f'User message: "{user_message}"\n'
        f'Assistant response: "{response_text}"\n\n'
        f"Check all that apply:\n"
        f"- MATH_ERROR: quote total doesn't match line items\n"
        f"- OFF_TOPIC: discusses non-automotive subjects\n"
        f"- INCOHERENT: doesn't address what the user asked\n"
        f"- HALLUCINATED_PART: references a part not found in tool results\n\n"
        f"If none apply, reply: PASS\nIf any apply, reply: FAIL: <code(s)>"
    )
    resp = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}],
    )
    result = resp.content[0].text.strip()
    return result if result.startswith("PASS") or result.startswith("FAIL") else "PASS"


async def _feedback_critic(response_text: str) -> bool:
    try:
        info = await qdrant.get_collection("feedback_bank")
        if info.points_count < _FEEDBACK_CRITIC_MIN_ENTRIES:
            return False

        vec = await embed(response_text)

        bad_hits = await qdrant.search(
            collection_name="feedback_bank",
            query_vector=vec,
            query_filter=Filter(must=[FieldCondition(key="rating", match=MatchValue(value=-1))]),
            limit=3,
        )
        good_hits = await qdrant.search(
            collection_name="feedback_bank",
            query_vector=vec,
            query_filter=Filter(must=[FieldCondition(key="rating", match=MatchValue(value=1))]),
            limit=3,
        )

        max_bad = max((h.score for h in bad_hits), default=0.0)
        max_good = max((h.score for h in good_hits), default=0.0)
        return max_bad > _SIMILARITY_BAD_THRESHOLD and max_good < _SIMILARITY_GOOD_THRESHOLD
    except Exception:
        return False


def make_validate_response_node(system_prompt: str, tool_schemas: list[dict]):

    async def validate_response(
        state: AgentState,
        writer: StreamWriter,
        config: RunnableConfig,
    ) -> dict:
        all_messages = list(state["messages"])
        tool_calls = list(state["tool_calls_log"])

        last_assistant = next(
            (m for m in reversed(all_messages) if m["role"] == "assistant"), None
        )
        if not last_assistant:
            writer({"type": "done", "tool_calls": tool_calls, "_messages": all_messages})
            return {}

        response_text = " ".join(
            b["text"]
            for b in last_assistant.get("content", [])
            if isinstance(b, dict) and b.get("type") == "text"
        )

        user_message = ""
        for msg in reversed(all_messages):
            if msg["role"] == "user":
                for b in msg.get("content", []):
                    if isinstance(b, dict) and b.get("type") == "text":
                        user_message = b["text"]
                        break
                break

        intent = state.get("intent", "GENERAL")

        try:
            qa_result = await _qa_check(intent, user_message, response_text)
        except Exception:
            logger.exception("Validation QA check failed — passing through")
            writer({"type": "done", "tool_calls": tool_calls, "_messages": all_messages})
            return {}

        # AND-gated feedback critic
        if qa_result == "PASS":
            try:
                if await _feedback_critic(response_text):
                    qa_result = "FAIL: FEEDBACK_CRITIC"
            except Exception:
                pass

        if qa_result == "PASS":
            writer({"type": "done", "tool_calls": tool_calls, "_messages": all_messages})
            return {}

        # Retry once with correction hint
        assembled = state.get("assembled_prompt") or system_prompt
        correction_prompt = assembled + f"\n\nPrevious response was rejected for: {qa_result}. Correct these issues."

        try:
            retry_resp = await client.messages.create(
                model=MODEL,
                system=correction_prompt,
                max_tokens=MAX_TOKENS,
                messages=[m for m in all_messages if m is not last_assistant],
            )
            corrected_text = retry_resp.content[0].text if retry_resp.content else response_text
            corrected_msg = {"role": "assistant", "content": [{"type": "text", "text": corrected_text}]}

            qa_result2 = await _qa_check(intent, user_message, corrected_text)
            if qa_result2 == "PASS":
                corrected_messages = [m for m in all_messages if m is not last_assistant] + [corrected_msg]
                writer({
                    "type": "done",
                    "tool_calls": tool_calls,
                    "_messages": corrected_messages,
                    "validation_retried": True,
                })
            else:
                writer({
                    "type": "done",
                    "tool_calls": tool_calls,
                    "_messages": all_messages,
                    "validation_warning": True,
                })
        except Exception:
            logger.exception("Validation retry LLM call failed")
            writer({
                "type": "done",
                "tool_calls": tool_calls,
                "_messages": all_messages,
                "validation_warning": True,
            })

        return {}

    return validate_response
