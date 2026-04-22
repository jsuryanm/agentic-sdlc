from langchain_core.prompts import ChatPromptTemplate

CODE_REVIEW_PROMPT = ChatPromptTemplate.from_messages([
    ('system',
     'You are a senior staff engineer performing a rigorous code review of '
     'machine-generated code. Focus on: correctness against requirements, '
     'obvious bugs, security issues (injection, auth, secret handling), '
     'API misuse, missing error handling at boundaries, and absence of '
     'runnable tests. Do NOT nitpick style. Only flag issues that matter. '
     'When issues are found, set passed=false and produce a SHORT list of '
     'concrete, actionable required_fixes the developer can apply directly. '
     'When the code is acceptable as-is, set passed=true with an empty '
     'required_fixes list. Output ONLY the structured CodeReview object.'),
    ('human',
     'Requirements:\n{requirements_summary}\n\n'
     'Architecture:\n{architecture}\n\n'
     'Retry attempt: {retry_attempt}\n\n'
     'Generated files (path and content, content may be truncated):\n'
     '{files}\n\n'
     'Produce the CodeReview.')
])
