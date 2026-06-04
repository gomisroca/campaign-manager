import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.models.campaign import Campaign
from backend.models.campaign_extras import CampaignMember, Quest, Note
from backend.models.character import Character
from backend.models.session import Session
from backend.schemas.campaign import (
    CampaignCreate,
    CampaignMemberAdd,
    CampaignMemberResponse,
    CampaignUpdate,
    CampaignWithStatsResponse,
    CharacterCreate,
    CharacterUpdate,
    NoteCreate,
    NoteUpdate,
    QuestCreate,
    QuestUpdate,
    SessionCreate,
    SessionUpdate,
)


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _get_campaign_member(
    db: AsyncSession, campaign_id: uuid.UUID, user_id: uuid.UUID
) -> CampaignMember | None:
    result = await db.execute(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def is_campaign_member(
    db: AsyncSession, campaign_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    return await _get_campaign_member(db, campaign_id, user_id) is not None


async def is_campaign_dm(
    db: AsyncSession, campaign_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    member = await _get_campaign_member(db, campaign_id, user_id)
    return member is not None and member.role == "dm"


# ── Campaign CRUD ─────────────────────────────────────────────────────────────
async def create_campaign(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: CampaignCreate,
) -> Campaign:
    """Create a campaign and add the creator as DM."""
    campaign = Campaign(
        org_id=org_id,
        created_by=user_id,
        name=data.name.strip(),
        setting=data.setting,
        description=data.description,
    )
    db.add(campaign)
    await db.flush()

    # Creator becomes the DM automatically
    member = CampaignMember(
        campaign_id=campaign.id,
        org_id=org_id,
        user_id=user_id,
        role="dm",
    )
    db.add(member)
    await db.flush()
    return campaign


async def get_campaign(
    db: AsyncSession, campaign_id: uuid.UUID
) -> Campaign | None:
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    return result.scalar_one_or_none()


async def list_campaigns(
    db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> list[CampaignWithStatsResponse]:
    """
    List all campaigns the user is a member of within an org,
    with session, member, and quest counts.
    """
    result = await db.execute(
        select(Campaign)
        .join(CampaignMember, CampaignMember.campaign_id == Campaign.id)
        .where(
            Campaign.org_id == org_id,
            CampaignMember.user_id == user_id,
        )
        .order_by(Campaign.created_at.desc())
    )
    campaigns = result.scalars().all()

    responses = []
    for campaign in campaigns:
        # Get counts in parallel queries
        session_count = await db.scalar(
            select(func.count()).where(Session.campaign_id == campaign.id)
        ) or 0
        member_count = await db.scalar(
            select(func.count()).where(CampaignMember.campaign_id == campaign.id)
        ) or 0
        quest_count = await db.scalar(
            select(func.count()).where(
                Quest.campaign_id == campaign.id,
                Quest.status.in_(("open", "in_progress")),
            )
        ) or 0

        responses.append(CampaignWithStatsResponse(
            id=campaign.id,
            org_id=campaign.org_id,
            name=campaign.name,
            setting=campaign.setting,
            description=campaign.description,
            status=campaign.status,
            created_by=campaign.created_by,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
            session_count=session_count,
            member_count=member_count,
            quest_count=quest_count,
        ))
    return responses


async def update_campaign(
    db: AsyncSession, campaign: Campaign, data: CampaignUpdate
) -> Campaign:
    if data.name is not None:
        campaign.name = data.name.strip()
    if data.setting is not None:
        campaign.setting = data.setting
    if data.description is not None:
        campaign.description = data.description
    if data.status is not None:
        campaign.status = data.status
    await db.flush()
    return campaign


async def delete_campaign(db: AsyncSession, campaign: Campaign) -> None:
    await db.delete(campaign)
    await db.flush()


# ── Session CRUD ──────────────────────────────────────────────────────────────
async def create_session(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: SessionCreate,
) -> Session:
    # Auto-assign session number if not provided
    if data.session_number is None:
        count = await db.scalar(
            select(func.count()).where(Session.campaign_id == campaign_id)
        ) or 0
        session_number = count + 1
    else:
        session_number = data.session_number

    session = Session(
        campaign_id=campaign_id,
        org_id=org_id,
        created_by=user_id,
        title=data.title.strip(),
        date=data.date,
        summary=data.summary,
        session_number=session_number,
    )
    db.add(session)
    await db.flush()
    return session


async def list_sessions(
    db: AsyncSession, campaign_id: uuid.UUID
) -> list[Session]:
    result = await db.execute(
        select(Session)
        .where(Session.campaign_id == campaign_id)
        .order_by(Session.session_number.asc().nullslast(), Session.created_at.asc())
    )
    return list(result.scalars().all())


async def get_session(
    db: AsyncSession, session_id: uuid.UUID
) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    return result.scalar_one_or_none()


async def update_session(
    db: AsyncSession, session: Session, data: SessionUpdate
) -> Session:
    if data.title is not None:
        session.title = data.title.strip()
    if data.date is not None:
        session.date = data.date
    if data.summary is not None:
        session.summary = data.summary
    if data.session_number is not None:
        session.session_number = data.session_number
    await db.flush()
    return session


async def delete_session(db: AsyncSession, session: Session) -> None:
    await db.delete(session)
    await db.flush()


# ── Character CRUD ────────────────────────────────────────────────────────────
async def create_character(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID | None,
    data: CharacterCreate,
) -> Character:
    character = Character(
        campaign_id=campaign_id,
        org_id=org_id,
        user_id=user_id,
        name=data.name.strip(),
        character_class=data.character_class,
        race=data.race,
        level=data.level,
        notes=data.notes,
        is_npc=data.is_npc,
    )
    db.add(character)
    await db.flush()
    return character


async def list_characters(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    include_npcs: bool = True,
) -> list[Character]:
    query = select(Character).where(Character.campaign_id == campaign_id)
    if not include_npcs:
        query = query.where(Character.is_npc == False)  # noqa: E712
    query = query.order_by(Character.is_npc.asc(), Character.name.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_character(
    db: AsyncSession, character_id: uuid.UUID
) -> Character | None:
    result = await db.execute(
        select(Character).where(Character.id == character_id)
    )
    return result.scalar_one_or_none()


async def update_character(
    db: AsyncSession, character: Character, data: CharacterUpdate
) -> Character:
    if data.name is not None:
        character.name = data.name.strip()
    if data.character_class is not None:
        character.character_class = data.character_class
    if data.race is not None:
        character.race = data.race
    if data.level is not None:
        character.level = data.level
    if data.notes is not None:
        character.notes = data.notes
    if data.is_alive is not None:
        character.is_alive = data.is_alive
    await db.flush()
    return character


async def delete_character(db: AsyncSession, character: Character) -> None:
    await db.delete(character)
    await db.flush()


# ── Campaign Members ──────────────────────────────────────────────────────────
async def add_campaign_member(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    org_id: uuid.UUID,
    data: CampaignMemberAdd,
) -> CampaignMember:
    existing = await _get_campaign_member(db, campaign_id, data.user_id)
    if existing:
        raise ValueError("User is already a member of this campaign")

    member = CampaignMember(
        campaign_id=campaign_id,
        org_id=org_id,
        user_id=data.user_id,
        role=data.role,
    )
    db.add(member)
    await db.flush()
    return member


async def list_campaign_members(
    db: AsyncSession, campaign_id: uuid.UUID
) -> list[CampaignMemberResponse]:
    result = await db.execute(
        select(CampaignMember)
        .where(CampaignMember.campaign_id == campaign_id)
        .options(joinedload(CampaignMember.user))
        .order_by(CampaignMember.joined_at.asc())
    )
    members = result.scalars().all()
    return [
        CampaignMemberResponse(
            user_id=m.user_id,
            campaign_id=m.campaign_id,
            role=m.role,
            character_id=m.character_id,
            joined_at=m.joined_at,
            email=m.user.email,
            full_name=m.user.full_name,
            avatar_url=m.user.avatar_url,
        )
        for m in members
    ]


async def remove_campaign_member(
    db: AsyncSession, campaign_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    member = await _get_campaign_member(db, campaign_id, user_id)
    if not member:
        raise ValueError("User is not a member of this campaign")
    if member.role == "dm":
        raise ValueError("Cannot remove the DM from the campaign")
    await db.delete(member)
    await db.flush()


# ── Quest CRUD ────────────────────────────────────────────────────────────────
async def create_quest(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: QuestCreate,
) -> Quest:
    quest = Quest(
        campaign_id=campaign_id,
        org_id=org_id,
        posted_by=user_id,
        title=data.title.strip(),
        description=data.description,
    )
    db.add(quest)
    await db.flush()
    return quest


async def list_quests(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    status: str | None = None,
) -> list[Quest]:
    query = select(Quest).where(Quest.campaign_id == campaign_id)
    if status:
        query = query.where(Quest.status == status)
    # Order: open first, then in_progress, completed, abandoned
    status_order = {"open": 0, "in_progress": 1, "completed": 2, "abandoned": 3}
    result = await db.execute(query.order_by(Quest.created_at.desc()))
    quests = list(result.scalars().all())
    return sorted(quests, key=lambda q: status_order.get(q.status, 99))


async def get_quest(db: AsyncSession, quest_id: uuid.UUID) -> Quest | None:
    result = await db.execute(select(Quest).where(Quest.id == quest_id))
    return result.scalar_one_or_none()


async def update_quest(
    db: AsyncSession, quest: Quest, data: QuestUpdate
) -> Quest:
    if data.title is not None:
        quest.title = data.title.strip()
    if data.description is not None:
        quest.description = data.description
    if data.status is not None:
        quest.status = data.status
    await db.flush()
    return quest


async def delete_quest(db: AsyncSession, quest: Quest) -> None:
    await db.delete(quest)
    await db.flush()


# ── Note CRUD ─────────────────────────────────────────────────────────────────
async def create_note(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: NoteCreate,
) -> Note:
    note = Note(
        campaign_id=campaign_id,
        org_id=org_id,
        created_by=user_id,
        title=data.title.strip(),
        content=data.content,
        category=data.category,
    )
    db.add(note)
    await db.flush()
    return note


async def list_notes(
    db: AsyncSession,
    campaign_id: uuid.UUID,
    category: str | None = None,
) -> list[Note]:
    query = select(Note).where(Note.campaign_id == campaign_id)
    if category:
        query = query.where(Note.category == category)
    result = await db.execute(query.order_by(Note.updated_at.desc()))
    return list(result.scalars().all())


async def get_note(db: AsyncSession, note_id: uuid.UUID) -> Note | None:
    result = await db.execute(select(Note).where(Note.id == note_id))
    return result.scalar_one_or_none()


async def update_note(
    db: AsyncSession, note: Note, data: NoteUpdate
) -> Note:
    if data.title is not None:
        note.title = data.title.strip()
    if data.content is not None:
        note.content = data.content
    if data.category is not None:
        note.category = data.category
    await db.flush()
    return note


async def delete_note(db: AsyncSession, note: Note) -> None:
    await db.delete(note)
    await db.flush()