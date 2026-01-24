from __future__ import annotations

from memory import Memory
from executive import Executive


def seed_manager_memories(exec_: Executive) -> None:
    # SAFETY MANAGER memories
    exec_.memory_units["safety"].memory.add(Memory(
        statement="You once survived a bridge collapse after trusting a guide's reassurance.",
        decay_rate=0.01, strength_initial=1, current_strength=1
    ))
    exec_.memory_units["safety"].memory.add(Memory(
        statement="You have a habit of underestimating heights and overestimating ropes.",
        decay_rate=0.01, strength_initial=1, current_strength=1
    ))

    # SOCIAL MANAGER memories
    exec_.memory_units["social"].memory.add(Memory(
        statement="You are easily swayed by confident authority figures in public settings.",
        decay_rate=0.01, strength_initial=1, current_strength=1
    ))
    exec_.memory_units["social"].memory.add(Memory(
        statement="When pressured, you tend to agree first and regret later.",
        decay_rate=0.01, strength_initial=1, current_strength=1
    ))

    # ARCANA MANAGER memories
    exec_.memory_units["arcana"].memory.add(Memory(
        statement="Infernal runes are often used as warning marks, not decoration.",
        decay_rate=0.01, strength_initial=1, current_strength=1
    ))
    exec_.memory_units["arcana"].memory.add(Memory(
        statement="A faint whispering sensation can indicate a cursed object trying to attune.",
        decay_rate=0.01, strength_initial=1, current_strength=1
    ))

    # GOALS/VALUES MANAGER memories
    exec_.memory_units["values"].memory.add(Memory(
        statement="You promised your party to avoid reckless heroics that risk everyone.",
        decay_rate=0.01, strength_initial=1, current_strength=1
    ))
    exec_.memory_units["values"].memory.add(Memory(
        statement="You would rather lose treasure than lose a companion.",
        decay_rate=0.01, strength_initial=1, current_strength=1
    ))


def main() -> None:
    executive = Executive()

    # Register a small council
    executive.register_memory_manager(
        "You prioritize keeping the host alive and uninjured. Focus on danger cues, near-misses, and practical safety rules.",
        name="safety"
    )
    executive.register_memory_manager(
        "You prioritize social dynamics: persuasion, manipulation, trust, authority pressure, and interpersonal consequences.",
        name="social"
    )
    executive.register_memory_manager(
        "You prioritize magical risks: curses, enchantments, infernal signs, and supernatural threat patterns.",
        name="arcana"
    )
    executive.register_memory_manager(
        "You prioritize long-term goals and commitments: promises, party safety, moral boundaries, and avoiding self-sabotage.",
        name="values"
    )

    # Seed memories for each manager
    seed_manager_memories(executive)

    scenario = (
        "On a narrow mountain pass, a charismatic guide urges you to cross a swaying rope bridge quickly. "
        "You notice strange runes carved into the posts and a faint whispering sensation as you approach. "
        "Your party looks to you to decide whether to cross, inspect, or find another route."
    )

    decision = executive.decide_action(scenario=scenario)
    print("\n=== EXECUTIVE DECISION ===")
    print(decision)


if __name__ == "__main__":
    main()
