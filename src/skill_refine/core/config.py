"""Configuration constants for skill-refine."""

EXPECTED_SECTIONS = [
    "description",
    "when to apply",
    "when not to apply",
    "warnings",
    "inputs",
    "outputs",
    "steps",
    "examples",
]

RECOMMENDED_FRONTMATTER_FIELDS = [
    "name",
    "description",
    "tags",
]

# Thresholds
MAX_SECTION_WORDS = 500
MAX_PARAGRAPH_WORDS = 150
MAX_TOTAL_WORDS = 3000
MIN_DESCRIPTION_WORDS = 10

# Scoring weights (sum to 1.0)
SCORE_WEIGHTS = {
    "completeness": 0.35,
    "structure": 0.25,
    "metadata": 0.15,
    "conciseness": 0.25,
}

# Vague trigger phrases that indicate an imprecise "when to apply"
VAGUE_TRIGGER_PHRASES = [
    "when needed",
    "as appropriate",
    "if necessary",
    "when applicable",
    "as needed",
    "use this when you need to",
    "whenever",
    "in general",
    "sometimes",
    "usually",
]
