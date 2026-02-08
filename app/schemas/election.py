from pydantic import BaseModel
from datetime import datetime, date, time
from typing import Optional


from pydantic import BaseModel
from datetime import datetime, date, time


class ElectionCreate(BaseModel):
    title: str
    assembly_id: int

    nomination_start: datetime
    nomination_end: datetime

    voting_start: datetime
    voting_end: datetime



class ElectionResponse(BaseModel):
    id: int
    name: str
    election_level: str
    status: str

    district: Optional[str]
    assembly: Optional[str]
    ward: Optional[str]

    polling_date: Optional[date]
    polling_start_time: Optional[time]
    polling_end_time: Optional[time]

    total_eligible_voters: int

    class Config:
        from_attributes = True
