import asyncio
import json
from app.integrations.dograh_client import DograhClient

async def test():
    client = DograhClient()
    for cid in [507]:
        try:
            result = await client.get_campaign_progress(cid)
            print(f"\n=== Campaign {cid} Progress ===")
            print(f"Data: {json.dumps(result, indent=2, default=str)}")
        except Exception as e:
            print(f"Campaign {cid}: {e}")

asyncio.run(test())
