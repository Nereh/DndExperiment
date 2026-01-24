from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Dict, List, Optional

from memory import MemoryManager
from ollama_client import OllamaClient


@dataclass
class Executive:
    model: str = "qwen2.5:7b-instruct"
    llm_client: OllamaClient = field(default_factory=OllamaClient)
    memory_units: Dict[str, MemoryManager] = field(default_factory=dict)

    decide_memory_units_to_consult_directive: str = """
You decide which personalities to consult when making a decision.

Rules:
- Return ONLY valid JSON (no markdown, no code fences, no extra text).
- Output format must be exactly a JSON array of strings: ["id1","id2",...]
- Every returned id MUST be a key present in payload.personalities.
- Select at most 4 ids.
- Select personalities that would have useful insight for the scenario.
- If none are relevant, return [].

Payload (JSON):
{payload}
""".strip()

    make_decision_directive: str = """
You are the executive function of the brain. You take insight from your subpersonalities to make a decision in the given scenario.

Rules:
- Write in ENGLISH ONLY. Do not use any non-English words or characters.
- Return ONLY plain text (no JSON, no markdown).
- Be as descriptive as you wish in terms of what decision you make and why you made it.
- Speak as the person the brain belongs to.

Payload (JSON):
{payload}
""".strip()

    def register_memory_manager(self, manager_personality: str, name: Optional[str] = None) -> None:
        """
        Register a memory manager under a stable id (e.g. 'safety', 'social', etc.).
        """
        manager = MemoryManager(manager_personality=manager_personality)
        key = name or manager.manager_id
        self.memory_units[key] = manager

    def decide_action(self, scenario: str) -> str:
        # Build the "personalities catalog" for the selector model
        personalities = {mid: mgr.manager_personality for mid, mgr in self.memory_units.items()}
        selector_payload = {"personalities": personalities, "scenario": scenario}

        selector_prompt = self.decide_memory_units_to_consult_directive.format(
            payload=json.dumps(selector_payload, ensure_ascii=False)
        )

        selected_managers_raw = self.llm_client.generate(model=self.model, prompt=selector_prompt).strip()

        # Parse selected manager ids safely
        try:
            selected_manager_ids = json.loads(selected_managers_raw)
            if not isinstance(selected_manager_ids, list) or not all(isinstance(x, str) for x in selected_manager_ids):
                selected_manager_ids = []
        except json.JSONDecodeError:
            selected_manager_ids = []

        # Filter to valid ids only (no hallucinated ids)
        selected_manager_ids = [mid for mid in selected_manager_ids if mid in self.memory_units]

        # If selector returns nothing, you can still choose to consult all or none.
        # I’ll default to consulting none, because that matches your prompt.
        summaries: List[str] = []
        for manager_id in selected_manager_ids:
            s = self.memory_units[manager_id].get_memory_summary(scenario=scenario)
            if s.strip():
                summaries.append(s.strip())
        
        print(summaries)

        decision_payload = {"advisor_insights": summaries, "scenario": scenario}
        decision_prompt = self.make_decision_directive.format(
            payload=json.dumps(decision_payload, ensure_ascii=False)
        )

        return self.llm_client.generate(model=self.model, prompt=decision_prompt)
