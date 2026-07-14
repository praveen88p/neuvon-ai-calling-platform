import asyncio
import json
from app.integrations.dograh_client import DograhClient

async def test():
    client = DograhClient()
    # Try fetching campaign runs - we need the dograh campaign ID
    # Let's try a few recent campaign IDs from the user's logs
    for cid in [498, 497, 494, 493]:
        try:
            result = await client.get_campaign_runs(cid)
            print(f"\n=== Campaign {cid} ===")
            print(f"Type: {type(result)}")
            if isinstance(result, dict):
                print(f"Keys: {list(result.keys())}")
                runs = result.get("runs", result.get("data", []))
                if runs:
                    print(f"First run keys: {list(runs[0].keys())}")
                    print(f"First run data: {json.dumps(runs[0], indent=2, default=str)}")
                else:
                    print("No runs found in dict")
            elif isinstance(result, list):
                if result:
                    print(f"First run keys: {list(result[0].keys())}")
                    print(f"First run data: {json.dumps(result[0], indent=2, default=str)}")
                else:
                    print("Empty list")
        except Exception as e:
            print(f"Campaign {cid}: {e}")

asyncio.run(test())
