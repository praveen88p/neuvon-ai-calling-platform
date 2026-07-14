import asyncio
from app.services.campaign_service import CampaignService
from app.schemas.auth import UserContext

async def main():
    service = CampaignService()
    user = UserContext(
        user_id="778c63ad-caee-4876-849e-11ec7d4cb0ee",
        organization_id="deacc140-d881-4c24-9b79-a94ead64b686",
        role="authenticated"
    )
    prog = await service.get_progress("ec805c4c-fdcd-4a4d-aa5a-35b3db4b363e", user)
    print("API Progress Result:", prog.model_dump())

asyncio.run(main())
