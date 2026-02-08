from pydantic import BaseModel
from typing import Optional


class ResultPublishRequest(BaseModel):
    district_id: Optional[int] = None
    assembly_id: Optional[int] = None
    mandal_id: Optional[int] = None
    village_id: Optional[int] = None
    ward_id: Optional[int] = None