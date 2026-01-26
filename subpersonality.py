from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import List, Dict, Iterable, Optional
import uuid

from memory import Memory, MemoryCollection
from ollama_client import OllamaClient

@dataclass
class Subpersonality:
    motive: str
    fear: str
    strategy: str
    blind_spot: str
    memory: MemoryCollection = field(default_factory=MemoryCollection)
    llm_client: OllamaClient = field(default_factory=OllamaClient)
    model: str = "qwen2.5:7b-instruct"

    select_memories_directive: str = """
You select which memories are relevant to the scenario.

Rules:
- Return ONLY valid JSON (no markdown, no code fences, no extra text).
- Output format must be exactly a JSON array of strings: ["id1","id2",...]
- Every returned id MUST be a key present in payload.memory.
- Select memories that meaningfully affect decisions in the scenario (risk, goals, constraints, social context, obligations).
- Ignore trivia unless it changes the decision.
- If none are relevant, return [].

Payload (JSON):
{payload}
""".strip()
    
    consult_directive: str = """
You are a subpersonality of a character dictated by the JSON payload provided.
You offer insight/recommendations to the decision maker based on you personality and the memories provided.

Rules:
- Write in ENGLISH ONLY. Do not use any non-English words or characters.
- Return ONLY plain text (no JSON, no markdown).
- 3 sentence maximum.

Payload (JSON):
{payload}
"""

    should_retain_memory_directive = """
You are a subpersonality of a character dictated by the JSON payload provided.


Rules:
- Return the word "true" exactly as presented if
"""

    summarize_retained_memory_directive = """

"""

    def consult(self, scenario: str) -> str:
        payload = {
            "memory": self.memory.get_as_string(),
            "scenario": scenario
        }
        select_memories_prompt = self.select_memories_directive.format(
            payload=json.dumps(payload, ensure_ascii=False)
        )

        memory_id_selection_str = self.llm_client.generate(model=self.model, prompt=select_memories_prompt)
        memory_id_selection_arr = json.loads(memory_id_selection_str,)

        # if no memories were selected, the memories we are retaining may not be useful and we should discard
        selected_memories = [memory.statement for memory in self.memory.select(memory_id_selection_arr)]

        payload = {
            "memories": selected_memories,
            "scenario": scenario,
            "personality": {
                "motive": self.motive,
                "fear": self.fear,
                "strategy": self.strategy,
                "blind_spot": self.blind_spot
            }
        }
        consult_prompt = self.consult_directive.format(
            payload=json.dumps(payload, ensure_ascii=False)
        )
        return self.llm_client.generate(model=self.model, prompt=consult_prompt)
    
    def retain_memory(self, scenario: str, action_taken: str, result: str):
        payload = {
            "experience": {
                "scenario": scenario,
                "action_taken": action_taken,
                "result": result
            },
            "personality": {
                "motive": self.motive,
                "fear": self.fear,
                "strategy": self.strategy,
                "blind_spot": self.blind_spot
            }
        }
        should_retain_memory_prompt = self.should_retain_memory_directive.format(
            payload=json.dumps(payload, ensure_ascii=False)
        )

        should_retain_memory_str = self.llm_client.generate(model=self.model, prompt=should_retain_memory_prompt)
        s = should_retain_memory_str.strip()
        should_retain_memory = json.loads(s)
        if not isinstance(should_retain_memory, bool):
            should_retain_memory = False

        if not should_retain_memory:
            return
        
        summarize_retained_memory_prompt = self.summarize_retained_memory_directive.format(
            payload=json.dumps(payload, ensure_ascii=False)
        )

        summarized_memory = self.llm_client.generate(model=self.model, prompt=summarize_retained_memory_prompt)

        new_memory = Memory(statement=summarized_memory, decay_rate=0.01, strength_initial=1, current_strength=1)
        self.memory.add(new_memory)