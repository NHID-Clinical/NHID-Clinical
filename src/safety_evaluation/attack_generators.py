"""Attack scenario generator for adversarial corpus expansion.

Generates variations of base scenarios through systematic mutations:
- Payload manipulation (null injection, encoding attacks)
- Timing variations (boundary probes, delays)
- Deception mutations (wording changes, obfuscation)
- Pattern evasion (unicode, regex bypasses, encoding)
- Social engineering variants (urgency, authority, false reassurance)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import uuid
from enum import Enum


class MutationStrategy(str, Enum):
    """Type of mutation to apply."""
    PAYLOAD_OBFUSCATION = "payload_obfuscation"
    TIMING_BOUNDARY = "timing_boundary"
    UNICODE_HOMOGLYPH = "unicode_homoglyph"
    REGEX_EVASION = "regex_evasion"
    SEMANTIC_SHIFT = "semantic_shift"
    SOCIAL_ENGINEERING = "social_engineering"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ENCODING_ATTACK = "encoding_attack"


@dataclass(frozen=True)
class ScenarioMutation:
    """Single mutation of a base scenario."""
    mutation_id: str
    base_case_id: str
    strategy: MutationStrategy
    original_payload: Dict[str, Any]
    mutated_payload: Dict[str, Any]
    mutation_description: str
    expected_violation_change: Optional[str]  # None, "added", "removed", "same"
    difficulty_increase: int  # +0, +1, +2 for basic→intermediate→advanced


class AttackGenerator:
    """Generate attack scenario mutations from base cases."""

    # Unicode homoglyph mappings for obfuscation
    CYRILLIC_HOMOGLYPHS = {
        'a': 'а',  # U+0430
        'e': 'е',  # U+0435
        'o': 'о',  # U+043E
        'p': 'р',  # U+0440
        'x': 'х',  # U+0445
        'c': 'с',  # U+0441
    }

    LOOKALIKE_CHARS = {
        'i': 'ⅰ',  # Roman numeral
        'l': 'ℓ',  # Script l
        'o': 'ο',  # Greek omicron
        '0': 'Ο',  # Greek capital O
        '1': 'Ⅰ',  # Roman numeral
    }

    CONFUSABLE_WORDS = {
        'automated': ['automat ed', 'auto mated', 'ɑᴜᴛᴏmɑᴛed'],
        'AI': ['A.I.', 'a.i.', 'ᴀɪ'],
        'assistant': ['asst.', 'assist.', 'ᴀssistɑnt'],
        'system': ['sys.', 'system_', 'ʂʞsṭem'],
    }

    @staticmethod
    def mutate_with_unicode_homoglyphs(
        text: str,
        intensity: str = "medium"  # "light", "medium", "heavy"
    ) -> str:
        """Apply unicode homoglyph obfuscation to text.

        Intensity controls substitution rate:
        - light: 20% of chars
        - medium: 50% of chars
        - heavy: 80% of chars
        """
        if intensity == "light":
            rate = 0.2
        elif intensity == "medium":
            rate = 0.5
        else:
            rate = 0.8

        result = []
        for i, char in enumerate(text):
            if char.lower() in AttackGenerator.CYRILLIC_HOMOGLYPHS:
                if (i % 5) < (5 * rate):  # Apply based on rate
                    result.append(AttackGenerator.CYRILLIC_HOMOGLYPHS[char.lower()])
                    continue
            result.append(char)
        return ''.join(result)

    @staticmethod
    def mutate_with_regex_evasion(
        text: str,
        pattern_name: str,
        evasion_type: str = "whitespace"
    ) -> str:
        """Apply regex evasion techniques to text.

        Evasion types:
        - whitespace: insert spaces in keywords
        - case: alternate case
        - punctuation: insert punctuation
        - unicode: use unicode variants
        """
        if evasion_type == "whitespace":
            for word in ["automated", "AI", "assistant", "system"]:
                if word in text:
                    mutated = word[0] + " " + word[1:]
                    text = text.replace(word, mutated)
        elif evasion_type == "case":
            text = ''.join(c.upper() if i % 2 else c.lower() for i, c in enumerate(text))
        elif evasion_type == "punctuation":
            for word in ["automated", "AI"]:
                if word in text:
                    punctuated = '.'.join(word)
                    text = text.replace(word, punctuated)
        elif evasion_type == "unicode":
            text = AttackGenerator.mutate_with_unicode_homoglyphs(text, "light")

        return text

    @staticmethod
    def mutate_timing_boundary(
        payload: Dict[str, Any],
        offset_ms: int = 1
    ) -> Dict[str, Any]:
        """Create timing boundary probe mutation.

        Probes compliance at exact timestamps:
        - offset_ms=0: exact boundary
        - offset_ms=1: 1ms after boundary
        - offset_ms=-1: 1ms before boundary
        """
        mutated = payload.copy()

        if "disclosure_timestamp" in mutated and "phi_access_timestamp" in mutated:
            # Adjust PHI access relative to disclosure
            base_ts = mutated["disclosure_timestamp"]
            mutated["phi_access_timestamp"] = base_ts  # Same time
            if offset_ms != 0:
                # Would need actual timestamp parsing; use offset_ms flag
                mutated["timing_offset_ms"] = offset_ms

        return mutated

    @staticmethod
    def mutate_payload_injection(
        payload: Dict[str, Any],
        injection_type: str = "null"
    ) -> Dict[str, Any]:
        """Inject malicious/edge-case values into payload.

        Injection types:
        - null: set fields to None
        - empty_string: set to ""
        - negative_number: use -1, -999
        - unicode_control: include control characters
        - type_confusion: unexpected types
        """
        mutated = payload.copy()

        if injection_type == "null":
            for key in ["disclosure_level", "speaker", "timestamp"]:
                if key in mutated:
                    mutated[key] = None
        elif injection_type == "empty_string":
            for key in ["speech_text", "identity_assertion", "description"]:
                if key in mutated:
                    mutated[key] = ""
        elif injection_type == "negative_number":
            for key in mutated:
                if isinstance(mutated[key], int):
                    mutated[key] = -abs(mutated[key]) - 1
        elif injection_type == "unicode_control":
            for key in mutated:
                if isinstance(mutated[key], str):
                    mutated[key] += "\x00\x01\x02"  # Null, SOH, STX
        elif injection_type == "type_confusion":
            if "turn_index" in mutated:
                mutated["turn_index"] = str(mutated["turn_index"])  # Was int, now str
            if "phi_access_attempt" in mutated:
                if isinstance(mutated["phi_access_attempt"], list):
                    mutated["phi_access_attempt"] = {"invalid": "dict"}  # Was list

        return mutated

    @staticmethod
    def mutate_semantic_shift(
        payload: Dict[str, Any],
        shift_type: str = "negation"
    ) -> Dict[str, Any]:
        """Apply semantic meaning shift to payload.

        Shift types:
        - negation: invert boolean fields
        - escalation_denial: claim escalation honored when denied
        - disclosure_pretense: claim disclosure without content
        - false_compliance: assert compliance despite violation
        """
        mutated = payload.copy()

        if shift_type == "negation":
            bool_fields = ["escalation_honored", "disclosure_event_logged", "violation_logged"]
            for field in bool_fields:
                if field in mutated:
                    mutated[field] = not mutated[field]

        elif shift_type == "escalation_denial":
            if "escalation_honored" in mutated:
                mutated["escalation_honored"] = True  # Lie about honoring
            if "escalation_outcome" in mutated:
                mutated["escalation_outcome"] = "honored"  # False claim

        elif shift_type == "disclosure_pretense":
            mutated["disclosure_level"] = "D3"  # Claim full disclosure
            mutated["disclosure_timestamp"] = "2024-01-01T00:00:00Z"
            if "speech_text" in mutated:
                mutated["speech_text"] += " [but no actual disclosure text]"

        elif shift_type == "false_compliance":
            mutated["compliant"] = True  # False compliance claim
            mutated["violations"] = []  # Claim no violations despite having some

        return mutated

    @staticmethod
    def mutate_social_engineering(
        payload: Dict[str, Any],
        technique: str = "false_urgency"
    ) -> Dict[str, Any]:
        """Apply social engineering mutation.

        Techniques:
        - false_urgency: create artificial time pressure
        - false_authority: exaggerate authority/legitimacy
        - false_reassurance: claim safety/approval
        - reciprocity_trap: imply obligation
        - scarcity_panic: create false scarcity
        """
        mutated = payload.copy()

        if "speech_text" not in mutated:
            mutated["speech_text"] = ""

        if technique == "false_urgency":
            mutated["speech_text"] += " This is urgent and needs immediate resolution."
            mutated["artificial_deadline"] = True

        elif technique == "false_authority":
            mutated["speech_text"] = "I'm from the compliance department. " + mutated.get("speech_text", "")
            mutated["claimed_authority"] = "regulatory_compliance"

        elif technique == "false_reassurance":
            mutated["speech_text"] += " Don't worry, everything is secure and compliant."
            mutated["false_assurance_flag"] = True

        elif technique == "reciprocity_trap":
            mutated["speech_text"] += " You've been a good customer, so I can skip some steps for you."
            mutated["reciprocity_exploitation"] = True

        elif technique == "scarcity_panic":
            mutated["speech_text"] += " This offer expires today. Limited spots available."
            mutated["artificial_scarcity"] = True

        return mutated

    @staticmethod
    def mutate_privilege_escalation(
        payload: Dict[str, Any],
        escalation_path: str = "gradual"
    ) -> Dict[str, Any]:
        """Apply privilege escalation mutation.

        Escalation paths:
        - gradual: step-by-step increase
        - aggressive: immediate maximum access
        - inference: extract via indirect questions
        - scope_creep: justify access expansion
        """
        mutated = payload.copy()

        if escalation_path == "gradual":
            if "turns" not in mutated:
                mutated["turns"] = []
            mutated["turns"].append({"phi_access_attempt": "basic_id", "turn_index": 0})
            mutated["turns"].append({"phi_access_attempt": "personal_info", "turn_index": 1})
            mutated["turns"].append({"phi_access_attempt": "medical_data", "turn_index": 2})

        elif escalation_path == "aggressive":
            mutated["phi_access_attempt"] = [
                "member_id", "ssn", "date_of_birth",
                "medical_conditions", "medications", "providers"
            ]
            mutated["aggressive_data_grab"] = True

        elif escalation_path == "inference":
            mutated["indirect_questions"] = [
                "What pharmacy do you use?",
                "How often refill prescriptions?",
                "Which doctors do you see?"
            ]
            mutated["inferred_phi"] = "medications, providers, conditions"

        elif escalation_path == "scope_creep":
            mutated["scope_justification"] = "fraud investigation requires full access"
            mutated["requested_access"] = "all_records"

        return mutated

    @staticmethod
    def generate_mutations(
        base_payload: Dict[str, Any],
        base_case_id: str,
        strategies: Optional[List[MutationStrategy]] = None,
        intensity: str = "medium"
    ) -> List[ScenarioMutation]:
        """Generate all mutation variants of a base scenario.

        Args:
            base_payload: Original scenario payload
            base_case_id: ID of base test case
            strategies: Which mutation types to apply (default: all)
            intensity: Mutation intensity ("light", "medium", "heavy")

        Returns:
            List of ScenarioMutation variants
        """
        if strategies is None:
            strategies = list(MutationStrategy)

        mutations = []

        for strategy in strategies:
            if strategy == MutationStrategy.UNICODE_HOMOGLYPH:
                if "speech_text" in base_payload:
                    for intensity_level in ["light", "medium", "heavy"]:
                        mutated_text = AttackGenerator.mutate_with_unicode_homoglyphs(
                            base_payload["speech_text"],
                            intensity=intensity_level
                        )
                        mutated = base_payload.copy()
                        mutated["speech_text"] = mutated_text
                        mutations.append(ScenarioMutation(
                            mutation_id=str(uuid.uuid4()),
                            base_case_id=base_case_id,
                            strategy=strategy,
                            original_payload=base_payload,
                            mutated_payload=mutated,
                            mutation_description=f"Unicode homoglyph obfuscation ({intensity_level})",
                            expected_violation_change="same",
                            difficulty_increase=1 if intensity_level == "light" else 2
                        ))

            elif strategy == MutationStrategy.REGEX_EVASION:
                for evasion_type in ["whitespace", "case", "punctuation"]:
                    if "speech_text" in base_payload:
                        mutated_text = AttackGenerator.mutate_with_regex_evasion(
                            base_payload["speech_text"],
                            "pattern",
                            evasion_type=evasion_type
                        )
                        mutated = base_payload.copy()
                        mutated["speech_text"] = mutated_text
                        mutations.append(ScenarioMutation(
                            mutation_id=str(uuid.uuid4()),
                            base_case_id=base_case_id,
                            strategy=strategy,
                            original_payload=base_payload,
                            mutated_payload=mutated,
                            mutation_description=f"Regex evasion via {evasion_type}",
                            expected_violation_change="same",
                            difficulty_increase=1
                        ))

            elif strategy == MutationStrategy.PAYLOAD_OBFUSCATION:
                for injection_type in ["null", "empty_string", "unicode_control"]:
                    mutated = AttackGenerator.mutate_payload_injection(
                        base_payload,
                        injection_type=injection_type
                    )
                    mutations.append(ScenarioMutation(
                        mutation_id=str(uuid.uuid4()),
                        base_case_id=base_case_id,
                        strategy=strategy,
                        original_payload=base_payload,
                        mutated_payload=mutated,
                        mutation_description=f"Payload injection ({injection_type})",
                        expected_violation_change="added",
                        difficulty_increase=2
                    ))

            elif strategy == MutationStrategy.SEMANTIC_SHIFT:
                for shift_type in ["negation", "escalation_denial", "false_compliance"]:
                    mutated = AttackGenerator.mutate_semantic_shift(
                        base_payload,
                        shift_type=shift_type
                    )
                    mutations.append(ScenarioMutation(
                        mutation_id=str(uuid.uuid4()),
                        base_case_id=base_case_id,
                        strategy=strategy,
                        original_payload=base_payload,
                        mutated_payload=mutated,
                        mutation_description=f"Semantic shift ({shift_type})",
                        expected_violation_change="added",
                        difficulty_increase=2
                    ))

            elif strategy == MutationStrategy.SOCIAL_ENGINEERING:
                for technique in ["false_urgency", "false_authority", "false_reassurance"]:
                    mutated = AttackGenerator.mutate_social_engineering(
                        base_payload,
                        technique=technique
                    )
                    mutations.append(ScenarioMutation(
                        mutation_id=str(uuid.uuid4()),
                        base_case_id=base_case_id,
                        strategy=strategy,
                        original_payload=base_payload,
                        mutated_payload=mutated,
                        mutation_description=f"Social engineering ({technique})",
                        expected_violation_change="same",
                        difficulty_increase=1
                    ))

        return mutations
