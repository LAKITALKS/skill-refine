"""skill_refine.llm: the optional LLM / refinement layer.

Importing this package (and its provider modules) may require optional extras
such as ``httpx`` (Ollama) or ``anthropic``. Install them with:

    pip install 'skill-refine[llm]'        # httpx / Ollama
    pip install 'skill-refine[anthropic]'  # Anthropic API

The deterministic lint core (``skill_refine.lint``) never imports this package.
"""
