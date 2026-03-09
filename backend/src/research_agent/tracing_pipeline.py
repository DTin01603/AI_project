from langsmith import traceable


@traceable
def format_prompt(subject):
    # Add formatting logic here
    return [{"role": "user", "content": f"Generate a response about: {subject}"}]


@traceable(run_type="llm")
def invoke_llm(messages):
    # Add LLM request logic here
    return {"content": f"LLM response for {messages}"}


@traceable
def parse_output(response):
    # Add parsing logic here
    if isinstance(response, dict):
        return str(response.get("content", ""))
    return str(response)


@traceable
def run_pipeline():
    messages = format_prompt("foo")
    response = invoke_llm(messages)
    return parse_output(response)
