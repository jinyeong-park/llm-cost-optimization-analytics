from langfuse import observe, get_client
from dotenv import load_dotenv


load_dotenv()


@observe
def verify_connection():
    test_generation()

    # get client and flush it
    client = get_client()
    client.flush()

    print("Connection to Langfuse is successful!")
    print("check your dashboard at https://app.langfuse.com/dashboard")


@observe
def test_generation():
    """A simple test generation function to verify Langfuse connection."""

    # The observe decorator will automatically log this function call to Langfuse
    return "Hello, Langfuse!"


if __name__ == "__main__":
    verify_connection()
