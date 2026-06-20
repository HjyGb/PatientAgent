"""Chat service — handle question/answer, streaming via core Patient agent.

Phase 3: DB-backed message persistence and turn tracking.
"""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.ext.asyncio import AsyncSession as DbAsyncSession

# Thread pool for running synchronous LLM calls without blocking the event loop
_executor = ThreadPoolExecutor(max_workers=4)


class ChatService:
    """Processes doctor questions and returns patient answers."""

    @classmethod
    async def get_patient_answer(
        cls,
        session_id: str,
        question: str,
        db: DbAsyncSession | None = None,
    ) -> dict:
        """Blocking patient answer — calls Patient.patient_ans() in a thread pool.

        Optionally persists the Q&A pair to the database and increments turn count.
        """
        from server.services.session_service import SessionService

        patient = SessionService.get_patient_agent(session_id)
        if patient is None:
            raise ValueError(f"Session {session_id} not found or expired")

        loop = asyncio.get_event_loop()
        answer, score, rel, faith, human = await loop.run_in_executor(
            _executor, patient.patient_ans, question
        )

        # Extract confirmed info (simple keyword extraction)
        confirmed_info = _extract_confirmed_info(answer)

        # ── DB persistence ──
        turn = 0
        if db is not None:
            # Increment turn counter atomically
            turn = await SessionService.increment_turn(db, session_id)

            # Save doctor question
            await SessionService.save_message(
                db,
                session_id=session_id,
                role="doctor",
                content=question,
                turn_number=turn,
            )

            # Save patient answer with scores
            await SessionService.save_message(
                db,
                session_id=session_id,
                role="patient",
                content=answer,
                turn_number=turn,
                score_overall=int(score) if score else None,
                score_relevance=int(rel) if rel else None,
                score_faithfulness=int(faith) if faith else None,
                score_robustness=int(human) if human else None,
                confirmed_info=confirmed_info,
            )

        return {
            "answer": answer,
            "scores": {
                "overall": score,
                "relevance": rel,
                "faithfulness": faith,
                "robustness": human,
            },
            "turn": turn,
            "is_max_turns": False,  # checked by the router
            "confirmed_info": confirmed_info,
        }

    @classmethod
    async def stream_patient_answer(
        cls,
        session_id: str,
        question: str,
        db: DbAsyncSession | None = None,
    ):
        """Async generator yielding SSE events for token-by-token streaming.

        Persists messages to DB on completion and tracks turn count.
        """
        from server.services.session_service import SessionService

        patient = SessionService.get_patient_agent(session_id)
        if patient is None:
            yield {"event": "error", "data": "Session not found"}
            return

        loop = asyncio.get_event_loop()

        # Increment turn first (so the DB is up-to-date)
        turn = 0
        if db is not None:
            turn = await SessionService.increment_turn(db, session_id)

            # Save doctor question immediately
            await SessionService.save_message(
                db,
                session_id=session_id,
                role="doctor",
                content=question,
                turn_number=turn,
            )

        if hasattr(patient, "patient_ans_stream"):
            gen = await loop.run_in_executor(_executor, patient.patient_ans_stream, question)
            full_answer = ""
            while True:
                # Use a wrapper to safely consume the generator without
                # letting StopIteration escape into an asyncio Future.
                def _safe_next(g):
                    try:
                        return (next(g), False)  # (token, not_done)
                    except StopIteration as e:
                        return (e.value, True)  # (result, done)

                token_or_result, done = await loop.run_in_executor(_executor, _safe_next, gen)
                if done:
                    result = token_or_result  # (answer, score, rel, faith, human)
                    if result and isinstance(result, tuple) and len(result) >= 5:
                        answer, score, rel, faith, human = result
                    else:
                        answer, score, rel, faith, human = full_answer, 3, 3, 3, 3
                    full_answer = answer  # use the complete answer
                    break
                else:
                    full_answer += token_or_result
                    yield {"event": "patient_token", "data": token_or_result}
        else:
            # Fallback: use blocking call and yield as one chunk
            result = await cls.get_patient_answer(session_id, question, db=None)
            answer = result["answer"]
            scores = result["scores"]
            score = scores["overall"]
            rel = scores["relevance"]
            faith = scores["faithfulness"]
            human = scores["robustness"]
            yield {"event": "patient_token", "data": answer}

        # ── Persist patient answer to DB ──
        confirmed_info = _extract_confirmed_info(full_answer)
        if db is not None and turn > 0:
            await SessionService.save_message(
                db,
                session_id=session_id,
                role="patient",
                content=full_answer,
                turn_number=turn,
                score_overall=int(score) if score else None,
                score_relevance=int(rel) if rel else None,
                score_faithfulness=int(faith) if faith else None,
                score_robustness=int(human) if human else None,
                confirmed_info=confirmed_info,
            )

        # Yield complete event with scores
        yield {
            "event": "patient_complete",
            "data": json.dumps({
                "answer": full_answer,
                "scores": {
                    "overall": score,
                    "relevance": rel,
                    "faithfulness": faith,
                    "robustness": human,
                },
                "turn": turn,
                "is_max_turns": False,
                "confirmed_info": confirmed_info,
            }, ensure_ascii=False),
        }


def _extract_confirmed_info(patient_answer: str) -> list[dict]:
    """Extract symptom/fact keywords from patient answer."""
    import re

    facts = []
    seen = set()

    symptom_patterns = [
        r"([一-鿿]{2,6}(?:疼痛|不适|肿胀|发热|咳嗽|头晕|恶心|呕吐|腹泻|便秘|乏力|消瘦|出血|发红|瘙痒|麻木|抽筋|痉挛|肿胀|僵硬))",
        r"(没有[一-鿿]{2,6})",
        r"((?:吃了|服用|注射|用过)[一-鿿]{2,8})",
        r"([一-鿿]{1,3}(?:天|周|月|年|小时)[一-鿿]{0,4})",
    ]

    for pattern in symptom_patterns:
        for match in re.finditer(pattern, patient_answer):
            fact = match.group(1)
            if fact not in seen and len(fact) >= 2:
                seen.add(fact)
                facts.append({
                    "category": "symptom",
                    "detail": fact,
                    "turn_discovered": 0,
                })

    return facts[:8]
