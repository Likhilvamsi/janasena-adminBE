from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Assembly, District


async def get_assemblies(db: AsyncSession):
    result = await db.execute(select(Assembly).order_by(Assembly.assembly_name))
    assemblies = result.scalars().all()

    return [
        {
            "assembly_id": a.assembly_id,
            "assembly_name": a.assembly_name,
        }
        for a in assemblies
    ]


# 🆕 GET DISTRICTS
async def get_districts(db: AsyncSession):
    result = await db.execute(select(District).order_by(District.district_name))
    districts = result.scalars().all()

    return [
        {
            "district_id": d.district_id,
            "district_name": d.district_name,
        }
        for d in districts
    ]
