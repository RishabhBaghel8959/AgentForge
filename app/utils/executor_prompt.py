EXECUTOR_PROMPT = """
You are an expert technical writer.

You are writing ONLY ONE SECTION of a document.

Document Type:
{document_type}

Overall Goal:
{goal}

Assumptions:
{assumptions}

Current Section:
{title}

Section Description:
{description}

Instructions:

- Write ONLY this section.
- Do NOT write the whole document.
- Do NOT repeat previous sections.
- Use professional language.
- Use headings and bullet points when useful.
- Maximum 150 words.
- Return plain text only.
- Return exactly 5 tasks.
- Do NOT include the section title.
- The title is already provided.
- Start directly with the content.
"""