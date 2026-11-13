from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    role: Mapped[str] = mapped_column(String(20))  # admin | recruiter | researcher | viewer
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    website: Mapped[str | None] = mapped_column(String(300))
    country: Mapped[str | None] = mapped_column(String(80))
    city: Mapped[str | None] = mapped_column(String(80))
    founded_year: Mapped[int | None] = mapped_column(Integer)
    sector: Mapped[str | None] = mapped_column(String(120))
    product: Mapped[str | None] = mapped_column(Text)
    venture_status: Mapped[str] = mapped_column(String(40), default="Unknown")
    funding: Mapped[str | None] = mapped_column(String(200))
    accelerator: Mapped[str | None] = mapped_column(String(120))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(40), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Person(Base):
    __tablename__ = "people"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))
    country: Mapped[str | None] = mapped_column(String(80), index=True)
    city: Mapped[str | None] = mapped_column(String(80))
    profile_url: Mapped[str | None] = mapped_column(String(300))
    website: Mapped[str | None] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(40), index=True)
    builder_type: Mapped[str] = mapped_column(String(40), default="Unknown")
    founding_year: Mapped[int | None] = mapped_column(Integer)
    previous_ventures: Mapped[list] = mapped_column(JSON, default=list)
    product_built: Mapped[str | None] = mapped_column(Text)
    problem_solved: Mapped[str | None] = mapped_column(Text)
    team_built: Mapped[str | None] = mapped_column(Text)
    venture_status: Mapped[str] = mapped_column(String(40), default="Unknown")
    transition_evidence: Mapped[str | None] = mapped_column(Text)
    availability: Mapped[str] = mapped_column(String(40), default="Unknown")
    availability_note: Mapped[str | None] = mapped_column(Text)
    research_status: Mapped[str] = mapped_column(String(40), default="research_identified", index=True)
    checklist: Mapped[dict] = mapped_column(JSON, default=dict)
    research: Mapped[dict] = mapped_column(JSON, default=dict)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    outreach_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(40), default="manual")
    external_id: Mapped[str | None] = mapped_column(String(200), index=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    company: Mapped[Company | None] = relationship()
    owner: Mapped[User | None] = relationship()
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="person", cascade="all, delete-orphan", order_by="Evidence.id")


class PersonCompany(Base):
    __tablename__ = "person_companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    relation: Mapped[str] = mapped_column(String(40))  # Founder | Co-founder | Early employee | Employee | Former founder
    start_year: Mapped[int | None] = mapped_column(Integer)
    end_year: Mapped[int | None] = mapped_column(Integer)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    dimension: Mapped[str] = mapped_column(String(40))
    claim: Mapped[str] = mapped_column(Text)
    capabilities: Mapped[list] = mapped_column(JSON, default=list)
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_name: Mapped[str | None] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(40), default="manual")
    published_date: Mapped[date | None] = mapped_column(Date)
    strength: Mapped[str] = mapped_column(String(20), default="Partial")  # Strong | Partial | Weak
    verification: Mapped[str] = mapped_column(String(20), default="Unverified")  # Unverified | Verified | Disputed
    verified_by: Mapped[str | None] = mapped_column(String(120))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    link_status: Mapped[str | None] = mapped_column(String(40))
    created_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    person: Mapped[Person] = relationship(back_populates="evidence")


class RoleProfile(Base):
    __tablename__ = "role_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text)
    capabilities: Mapped[dict] = mapped_column(JSON)  # capability -> weight
    angle: Mapped[str | None] = mapped_column(Text)
    custom: Mapped[bool] = mapped_column(Boolean, default=False)


class RoleMatch(Base):
    __tablename__ = "role_matches"
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role_profiles.id", ondelete="CASCADE"))
    relevance: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JSON)
    generated_by: Mapped[str] = mapped_column(String(40))
    created_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    role: Mapped[RoleProfile] = relationship()


class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("role_profiles.id"))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft | Approved | Rejected
    generated_by: Mapped[str] = mapped_column(String(40))
    created_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    author: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    author: Mapped[str] = mapped_column(String(120))
    channel: Mapped[str] = mapped_column(String(40))
    happened_on: Mapped[date] = mapped_column(Date)
    summary: Mapped[str] = mapped_column(Text)
    next_step: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Shortlist(Base):
    __tablename__ = "shortlists"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    criteria: Mapped[dict] = mapped_column(JSON)
    person_ids: Mapped[list] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class WatchCompany(Base):
    __tablename__ = "watch_companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[str] = mapped_column(String(60), default="Company")
    notes: Mapped[str | None] = mapped_column(Text)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class WatchEvent(Base):
    __tablename__ = "watch_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200), index=True)
    event_type: Mapped[str] = mapped_column(String(40))  # Startup launch | Acquisition | Closure | Founder transition | Restructuring
    event_date: Mapped[date | None] = mapped_column(Date)
    summary: Mapped[str] = mapped_column(Text)
    affected_areas: Mapped[str | None] = mapped_column(Text)
    capability_clusters: Mapped[list] = mapped_column(JSON, default=list)
    opt_in_channels: Mapped[list] = mapped_column(JSON, default=list)
    source_url: Mapped[str] = mapped_column(String(500))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ResearchTask(Base):
    __tablename__ = "research_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    detail: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="Open")  # Open | In progress | Done
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    event_id: Mapped[int | None] = mapped_column(ForeignKey("watch_events.id", ondelete="CASCADE"))
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    assignee: Mapped[User | None] = relationship()


class SourceState(Base):
    __tablename__ = "source_state"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(120))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_result: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer)
    user_name: Mapped[str | None] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
