import asyncio
from app.integrations.insforge_client import get_insforge_client

async def test():
    try:
        client = get_insforge_client()
        result = await client.auth.create_user(
            email="test_failure@neuvon.com",
            password="TestPassword123!",
            name="Test Failure"
        )
        print("Success:", result)
    except Exception as e:
        print("Error details:", repr(e))
        print("Stringified error:", str(e))

asyncio.run(test())
