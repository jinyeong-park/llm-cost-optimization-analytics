from dotenv import load_dotenv
from langfuse import observe, get_client

load_dotenv()

# Initialize OpenTelemetry instrumentation for LangChain
from opentelemetry.instrumentation.langchain import LangchainInstrumentor

LangchainInstrumentor().instrument()

# use with any langchain component
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate


@observe()
def run_langchain_example():
    """Run a simple LangChain example with observability."""
    llm = ChatAnthropic(model="claude-sonnet-4-20250514")
    prompt = ChatPromptTemplate.from_template("Explain {topic} in simple terms.")
    chain = prompt | llm

    # OpenTelemetry instrumentation captures this automatically
    response = chain.invoke({"topic": "quantum computing"})
    return response


if __name__ == "__main__":
    response = run_langchain_example()
    print(response)
    get_client().flush()  # Ensure all events are sent to Langfuse
