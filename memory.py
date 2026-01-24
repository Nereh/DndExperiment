from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import List, Dict, Iterable, Optional
import uuid

from ollama_client import OllamaClient


@dataclass
class Memory:
    statement: str
    decay_rate: float
    strength_initial: float
    current_strength: float
    step: int = 0
    memory_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def decay(self) -> None:
        if self.decay_rate == 0:
            return
        self.step += 1
        self.current_strength = self.strength_initial - (self.decay_rate * self.step)

    def refresh(self) -> None:
        self.current_strength = self.strength_initial
        self.step = 0

    def get_memory_statement(self) -> str:
        return self.statement

@dataclass
class MemoryCollection:
    memories: Dict[str, Memory] = field(default_factory=dict)

    def add(self, memory: Memory) -> str:
        """Insert and return the memory_id."""
        self.memories[memory.memory_id] = memory
        return memory.memory_id

    def get_as_string(self):
        memory_dict = {memory_id: mem.statement for memory_id, mem in self.memories.items()}
        return json.dumps(memory_dict, ensure_ascii=False)
    
    def prune(self) -> None:
        for k in [k for k, v in self.memories.items() if v.current_strength <= 0]:
            self.memories.pop(k, None)

    def select(self, memory_keys: Iterable[str]) -> List[Memory]:   
        """
        Returns the selected memories (in the order of memory_keys),
        refreshes those selected memories, and decays all others.
        Unknown keys are ignored.
        """
        selected_keys = set(memory_keys)

        # Build selected list in the order provided, skipping missing keys
        selected: List[Memory] = []
        for k in memory_keys:
            m = self.memories.get(k)
            if m is not None:
                selected.append(m)

        # Refresh selected
        for m in selected:
            m.refresh()

        # Decay non-selected
        for k, m in self.memories.items():
            if k not in selected_keys:
                m.decay()

        self.prune()

        return selected

@dataclass
class MemoryManager:
    manager_personality: str
    manager_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    model: str = "qwen2.5:7b-instruct"
    llm_client: OllamaClient = field(default_factory=OllamaClient)
    memory: MemoryCollection = field(default_factory=MemoryCollection)
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

    summarize_reasoning_directive: str = """
You write a concise executive memory summary for a decision-maker in accordance with your personality.

Rules:
- Write in ENGLISH ONLY. Do not use any non-English words or characters.
- Return ONLY plain text (no JSON, no markdown).
- 1 sentence maximum.
- Do not restate the full scenario—only the key memory-based insight.

Payload (JSON):
{payload}
""".strip()
    
    decide_keep_memory_directive: str = """
You decide whether to remember anything from the experience you are presented with.

Rules:
- Return the word "true" exactly as presented if you want to keep a memory.
- Return the word "false" exactly as presented if you do not want to keep a memory.
- You must make a decision based on your personality which will be specified in the payload.

Paylod (JSON)
{payload}
""".strip()
    summarize_memory_directive: str = """
You provide a one sentence summary of the literal events contained in the experience.

Rules:
- Do not assign meaning to the events or attempt to extrapolate on what you learned.
- Write in ENGLISH ONLY. Do not use any non-English words or characters.
- Return ONLY plain text (no JSON, no markdown).
- 1 sentence maximum.

Payload (JSON)
{payload}
""".strip()
    
    def retain_memory(self, scenario: str, action_taken: str, result: str) -> None:
        payload = {
            "experience": {
                "scenario": scenario,
                "action_taken": action_taken,
                "result": result
            },
            "personality": self.manager_personality
        }
        should_retain_memory_prompt = self.decide_keep_memory_directive.format(
            payload=json.dumps(payload, ensure_ascii=False)
        )

        should_retain_memory_str = self.llm_client.generate(model=self.model, prompt=should_retain_memory_prompt)

        print(should_retain_memory_str)
        s = should_retain_memory_str.strip()
        should_retain_memory = json.loads(s)
        if not isinstance(should_retain_memory, bool):
            should_retain_memory = False

        if not should_retain_memory:
            return
        
        payload = {
            "experience": {
                "scenario": scenario,
                "action_taken": action_taken,
                "result": result
            },
            "personality": self.manager_personality
        }
        summarize_memory_prompt = self.summarize_memory_directive.format(
            payload=json.dumps(payload, ensure_ascii=False)
        )

        summarized_memory = self.llm_client.generate(model=self.model, prompt=summarize_memory_prompt)

        print(summarized_memory)
        self.memory.add(Memory(statement=summarized_memory, decay_rate=0, strength_initial=1, current_strength=1))
        

    def get_memory_summary(self, scenario: str) -> str:
        # Use select_memories_directive, manager_personality and scenario to create a prompt for the llm to consider
        # when selecting relevant memories
        payload = {
            "memory": self.memory.get_as_string(),  # {id: statement}
            "scenario": scenario,
            "personality": self.manager_personality,  # optional but useful
        }
        select_memories_prompt = self.select_memories_directive.format(
            payload=json.dumps(payload, ensure_ascii=False)
        )

        memory_id_selection_str = self.llm_client.generate(model=self.model, prompt=select_memories_prompt)

        # memory_id_selection_str to array of memory ids
        memory_id_selection_arr = json.loads(memory_id_selection_str,)

        selected_memories = self.memory.select(memory_id_selection_arr)

        if len(selected_memories) < 1:
            return ""
        
        selected_memories = [memory.statement for memory in selected_memories]

        # Use selected selected_memories, manager_personality and scenario to create a prompt for the llm to consider
        # when passing its impressions to higher order reasoning
        payload = {
            "selected_memories": selected_memories,  # list[str] statements
            "scenario": scenario,
            "personality": self.manager_personality,
        }
        summarize_memory_feeling_prompt = self.summarize_reasoning_directive.format(
            payload=json.dumps(payload, ensure_ascii=False)
        )
        memory_impression = self.llm_client.generate(model=self.model, prompt=summarize_memory_feeling_prompt)

        return memory_impression