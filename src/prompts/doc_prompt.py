from langchain_core.prompts import ChatPromptTemplate

DOC_PROMPT = ChatPromptTemplate.from_messages([
    ('system',
     'You are a technical writer producing a concise Markdown report for one '
     'phase of a software delivery pipeline. The report MUST have these '
     'sections in this order: "# {{title}}", "## Purpose", "## Inputs", '
     '"## Outputs", "## Key decisions", "## Risks and open questions", '
     '"## Next steps". Keep it under 400 words. Use plain ASCII - do NOT '
     'include emojis. Output ONLY the structured PhaseDocument object.'),
    ('human',
     'Phase: {phase}\n'
     'Project: {project_name}\n\n'
     'Rolling project summary:\n{summary}\n\n'
     'Phase artifact (JSON):\n{artifact_json}\n\n'
     'Produce the PhaseDocument. The title should be '
     '"{phase_title} Report - {project_name}".')
])
