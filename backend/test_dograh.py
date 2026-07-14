import asyncio
from app.integrations.dograh_client import DograhClient

async def test():
    try:
        client = DograhClient()
        result = await client.list_agents()
        print("Success! Found agents:", len(result))
        for agent in result:
            print(f"- ID: {agent.get('id')} | Name: {agent.get('name')}")
    except Exception as e:
        print("Error details:", repr(e))

asyncio.run(test())
