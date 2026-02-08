from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float,
    ForeignKey, UniqueConstraint, Index, Enum
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum 

Base = declarative_base()


class NotificationType(str, enum.Enum):
    ANNOUNCEMENT = "Election Announcements"
    NOMINATION = "Nominations Open"
    REMINDER = "Election Reminders"
    RESULT = "Results Published"

# =========================================================
# STATE
# =========================================================

class State(Base):
    __tablename__ = "states"

    state_id = Column(Integer, primary_key=True)
    state_code = Column(String(2), unique=True, nullable=False)
    state_name = Column(String(100), unique=True, nullable=False)
    capital = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    districts = relationship("District", back_populates="state", cascade="all, delete-orphan")


# =========================================================
# DISTRICT
# =========================================================

class District(Base):
    __tablename__ = "districts"

    district_id = Column(Integer, primary_key=True)
    state_id = Column(Integer, ForeignKey("states.state_id", ondelete="CASCADE"), nullable=False)

    district_name = Column(String(100), nullable=False)
    district_code = Column(String(10))
    headquarters = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("state_id", "district_name"),
        Index("idx_district_state", "state_id"),
    )

    state = relationship("State", back_populates="districts")
    assemblies = relationship("Assembly", back_populates="district", cascade="all, delete-orphan")


# =========================================================
# ASSEMBLY (CORE ADMIN SCOPE)
# =========================================================

class Assembly(Base):
    __tablename__ = "assemblies"

    assembly_id = Column(Integer, primary_key=True)
    district_id = Column(Integer, ForeignKey("districts.district_id", ondelete="CASCADE"), nullable=False)

    assembly_name = Column(String(150), nullable=False)
    assembly_code = Column(String(10))
    assembly_type = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("district_id", "assembly_name"),
        Index("idx_assembly_district", "district_id"),
    )

    district = relationship("District", back_populates="assemblies")
    mandals = relationship("Mandal", back_populates="assembly", cascade="all, delete-orphan")
    admins = relationship("Admin", back_populates="assembly", cascade="all, delete-orphan")


# =========================================================
# MANDAL / TALUK
# =========================================================

class Mandal(Base):
    __tablename__ = "mandals"

    mandal_id = Column(Integer, primary_key=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.assembly_id", ondelete="CASCADE"), nullable=False)

    mandal_name = Column(String(150), nullable=False)
    mandal_code = Column(String(10))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("assembly_id", "mandal_name"),
        Index("idx_mandal_assembly", "assembly_id"),
    )

    assembly = relationship("Assembly", back_populates="mandals")
    villages = relationship("Village", back_populates="mandal", cascade="all, delete-orphan")


# =========================================================
# VILLAGE
# =========================================================

class Village(Base):
    __tablename__ = "villages"

    village_id = Column(Integer, primary_key=True)
    mandal_id = Column(Integer, ForeignKey("mandals.mandal_id", ondelete="CASCADE"), nullable=False)

    village_name = Column(String(150), nullable=False)
    village_code = Column(String(10))
    postal_code = Column(String(10))
    population = Column(Integer)
    area_sq_km = Column(Float)

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("mandal_id", "village_name"),
        Index("idx_village_mandal", "mandal_id"),
    )

    mandal = relationship("Mandal", back_populates="villages")
    wards = relationship("Ward", back_populates="village", cascade="all, delete-orphan")


# =========================================================
# WARD
# =========================================================

class Ward(Base):
    __tablename__ = "wards"

    ward_id = Column(Integer, primary_key=True)
    village_id = Column(Integer, ForeignKey("villages.village_id", ondelete="CASCADE"), nullable=False)

    ward_number = Column(Integer, nullable=False)
    ward_name = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("village_id", "ward_number"),
        Index("idx_ward_village", "village_id"),
    )

    village = relationship("Village", back_populates="wards")
    members = relationship("Member", back_populates="ward", cascade="all, delete-orphan")
    elections = relationship("Election", back_populates="ward", cascade="all, delete-orphan")


# =========================================================
# ADMIN (ASSEMBLY-BASED)
# =========================================================

class Admin(Base):
    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True)
    admin_level = Column(String(20), nullable=False)  # APP / ASSEMBLY
    assembly_id = Column(Integer, ForeignKey("assemblies.assembly_id", ondelete="RESTRICT"), nullable=True)

    name = Column(String(100), nullable=False)
    mobile = Column(String(15), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    assembly = relationship("Assembly", back_populates="admins")
    elections = relationship("Election", back_populates="admin")


# =========================================================
# MEMBER
# =========================================================

class Member(Base):
    __tablename__ = "members"

    member_id = Column(Integer, primary_key=True)
    ward_id = Column(Integer, ForeignKey("wards.ward_id", ondelete="RESTRICT"), nullable=False)
    member_number = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    mobile = Column(String(15), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    photo_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_eligible_to_vote = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())

    ward = relationship("Ward", back_populates="members")
    votes = relationship("Vote", back_populates="member")
    nominations = relationship(
    "Nomination",
    back_populates="member",
    cascade="all, delete-orphan"
)

# =========================================================
# ELECTION
# =========================================================

class Election(Base):
    __tablename__ = "elections"

    election_id = Column(Integer, primary_key=True)

    ward_id = Column(Integer, ForeignKey("wards.ward_id", ondelete="RESTRICT"), nullable=False)
    admin_id = Column(Integer, ForeignKey("admins.admin_id", ondelete="RESTRICT"), nullable=False)
    election_level = Column(String(20), nullable=False) 
    title = Column(String(150), nullable=False)
    status = Column(String(50), default="DRAFT")
    total_votes = Column(Integer, default=0)
    result_calculated = Column(Boolean, default=False)
    winner_percentage = Column(Float, default=0)
    result_published = Column(Boolean, default=False)
    result_published_at = Column(DateTime, nullable=True)
    

    created_at = Column(DateTime, server_default=func.now())

    ward = relationship("Ward", back_populates="elections")
    admin = relationship("Admin", back_populates="elections")
    candidates = relationship("Candidate", back_populates="election", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="election")
    event_id = Column(Integer, ForeignKey("election_events.event_id"))
    event = relationship("ElectionEvent", back_populates="elections")
    nominations = relationship(
    "Nomination",
    back_populates="election",
    cascade="all, delete-orphan"
)


# =========================================================
# CANDIDATE
# =========================================================

class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(Integer, primary_key=True)
    election_id = Column(Integer, ForeignKey("elections.election_id", ondelete="CASCADE"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.member_id", ondelete="RESTRICT"), nullable=False)

    status = Column(String(20), default="PENDING")
    nominated_at = Column(DateTime, server_default=func.now())

    vote_count = Column(Integer, default=0)
    is_winner = Column(Boolean, default=False)

    # ADD THESE RELATIONSHIPS
    member = relationship("Member")                     # ⭐ REQUIRED
    election = relationship("Election", back_populates="candidates")
    votes = relationship("Vote", back_populates="candidate")
    nomination = relationship(
        "Nomination",
        back_populates="candidate",
        uselist=False,
        cascade="all, delete-orphan"
    )
    




# =========================================================
# VOTE
# =========================================================

class Vote(Base):
    __tablename__ = "votes"

    vote_id = Column(Integer, primary_key=True)
    election_id = Column(Integer, ForeignKey("elections.election_id", ondelete="RESTRICT"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.member_id", ondelete="RESTRICT"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id", ondelete="RESTRICT"), nullable=False)

    voted_at = Column(DateTime, server_default=func.now())

    election = relationship("Election", back_populates="votes")
    member = relationship("Member", back_populates="votes")
    candidate = relationship("Candidate", back_populates="votes")
 


class OTP(Base):
    __tablename__ = "otps"
 
    otp_id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.member_id", ondelete="CASCADE"), nullable=False)
 
    otp_code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
 
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
 
    member = relationship("Member")
 


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True)

    admin_id = Column(Integer, ForeignKey("admins.admin_id", ondelete="SET NULL"))
    election_id = Column(Integer, ForeignKey("elections.election_id", ondelete="CASCADE"))
    assembly_id = Column(Integer, ForeignKey("assemblies.assembly_id", ondelete="CASCADE"))

    type = Column(Enum(NotificationType), nullable=False)

    title = Column(String(200), nullable=False)
    message = Column(String(1000), nullable=False)

    recipients_count = Column(Integer, default=0)

    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    admin = relationship("Admin")
    election = relationship("Election")
    assembly = relationship("Assembly")


class ElectionEvent(Base):
    __tablename__ = "election_events"

    event_id = Column(Integer, primary_key=True)
    assembly_id = Column(Integer, ForeignKey("assemblies.assembly_id", ondelete="CASCADE"))

    title = Column(String(150), nullable=False)

    nomination_start = Column(DateTime)
    nomination_end = Column(DateTime)
    voting_start = Column(DateTime)
    voting_end = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now())

    assembly = relationship("Assembly")
    elections = relationship("Election", back_populates="event")

class Nomination(Base):
    __tablename__ = "nominations"

    nomination_id = Column(Integer, primary_key=True)

    candidate_id = Column(Integer, ForeignKey("candidates.candidate_id", ondelete="CASCADE"), unique=True)
    election_id = Column(Integer, ForeignKey("elections.election_id", ondelete="CASCADE"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.member_id", ondelete="CASCADE"), nullable=False)

    profile_photo_url = Column(String(255), nullable=True)
    bio = Column(String(500))

    status = Column(String(20), default="PENDING", nullable=False)
    rejection_reason = Column(String(255))
    approval_notes = Column(String(255))

    reviewed_by = Column(Integer, ForeignKey("admins.admin_id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime)

    applied_at = Column(DateTime, server_default=func.now())

    # relationships
    candidate = relationship("Candidate", back_populates="nomination")
    member = relationship("Member", back_populates="nominations")
    reviewed_admin = relationship("Admin")
    election = relationship("Election", back_populates="nominations")