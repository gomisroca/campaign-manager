import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.deps import get_current_user
from backend.models.user import User
from backend.schemas.campaign import (
    CampaignCreate,
    CampaignMemberAdd,
    CampaignMemberResponse,
    CampaignResponse,
    CampaignUpdate,
    CampaignWithStatsResponse,
    CharacterCreate,
    CharacterResponse,
    CharacterUpdate,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
    QuestCreate,
    QuestResponse,
    QuestUpdate,
    SessionCreate,
    SessionResponse,
    SessionUpdate,
)
from backend.services.campaign_service import (
    add_campaign_member,
    create_campaign,
    create_character,
    create_note,
    create_quest,
    create_session,
    delete_campaign,
    delete_character,
    delete_note,
    delete_quest,
    delete_session,
    get_campaign,
    get_character,
    get_note,
    get_quest,
    get_session,
    is_campaign_dm,
    is_campaign_member,
    list_campaign_members,
    list_campaigns,
    list_characters,
    list_notes,
    list_quests,
    list_sessions,
    remove_campaign_member,
    update_campaign,
    update_character,
    update_note,
    update_quest,
    update_session,
)
from backend.services.org_service import get_org_by_id, require_role

router = APIRouter(tags=["campaigns"])


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _get_org_or_404(db: AsyncSession, org_id: uuid.UUID):
    org = await get_org_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")
    return org


async def _get_campaign_or_404(
    db: AsyncSession, campaign_id: uuid.UUID, org_id: uuid.UUID | None = None
):
    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if org_id and campaign.org_id != org_id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

async def _require_campaign_member(
    db: AsyncSession, campaign_id: uuid.UUID, user_id: uuid.UUID
):
    if not await is_campaign_member(db, campaign_id, user_id):
        raise HTTPException(status_code=404, detail="Campaign not found")


async def _require_campaign_dm(
    db: AsyncSession, campaign_id: uuid.UUID, user_id: uuid.UUID
):
    if not await is_campaign_dm(db, campaign_id, user_id):
        raise HTTPException(
            status_code=403, detail="Only the DM can perform this action"
        )


# ── Campaigns ─────────────────────────────────────────────────────────────────
@router.post(
    "/orgs/{org_id}/campaigns",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    org_id: uuid.UUID,
    data: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new campaign. Creator becomes the DM automatically."""
    await _get_org_or_404(db, org_id)
    try:
        await require_role(db, current_user.id, org_id, "member")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    campaign = await create_campaign(db, org_id, current_user.id, data)
    return CampaignResponse.model_validate(campaign)


@router.get("/orgs/{org_id}/campaigns", response_model=list[CampaignWithStatsResponse])
async def list_all(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all campaigns the current user is a member of within an org."""
    await _get_org_or_404(db, org_id)
    try:
        await require_role(db, current_user.id, org_id, "member")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return await list_campaigns(db, org_id, current_user.id)


@router.get("/orgs/{org_id}/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_one(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_member(db, campaign_id, current_user.id)
    return CampaignResponse.model_validate(campaign)


@router.patch("/orgs/{org_id}/campaigns/{campaign_id}", response_model=CampaignResponse)
async def patch(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    data: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update campaign details. DM only."""
    campaign = await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_dm(db, campaign_id, current_user.id)
    return CampaignResponse.model_validate(await update_campaign(db, campaign, data))


@router.delete(
    "/orgs/{org_id}/campaigns/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a campaign and all its data. DM only."""
    campaign = await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_dm(db, campaign_id, current_user.id)
    await delete_campaign(db, campaign)


# ── Campaign Members ──────────────────────────────────────────────────────────
@router.get(
    "/orgs/{org_id}/campaigns/{campaign_id}/members",
    response_model=list[CampaignMemberResponse],
)
async def list_members(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_member(db, campaign_id, current_user.id)
    return await list_campaign_members(db, campaign_id)


@router.post(
    "/orgs/{org_id}/campaigns/{campaign_id}/members",
    response_model=CampaignMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    data: CampaignMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a member to a campaign. DM only."""
    await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_dm(db, campaign_id, current_user.id)

    try:
        member = await add_campaign_member(db, campaign_id, org_id, data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    members = await list_campaign_members(db, campaign_id)
    return next(m for m in members if m.user_id == member.user_id)


@router.delete(
    "/orgs/{org_id}/campaigns/{campaign_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member. DM only, or self-removal."""
    await _get_campaign_or_404(db, campaign_id, org_id)
    is_self = current_user.id == user_id
    if not is_self:
        await _require_campaign_dm(db, campaign_id, current_user.id)
    try:
        await remove_campaign_member(db, campaign_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Sessions ──────────────────────────────────────────────────────────────────
@router.post(
    "/orgs/{org_id}/campaigns/{campaign_id}/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a session. DM only."""
    await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_dm(db, campaign_id, current_user.id)
    session = await create_session(db, campaign_id, org_id, current_user.id, data)
    return SessionResponse.model_validate(session)


@router.get(
    "/orgs/{org_id}/campaigns/{campaign_id}/sessions",
    response_model=list[SessionResponse],
)
async def list_sessions_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_member(db, campaign_id, current_user.id)
    return [
        SessionResponse.model_validate(s)
        for s in await list_sessions(db, campaign_id)
    ]


@router.patch(
    "/orgs/{org_id}/campaigns/{campaign_id}/sessions/{session_id}",
    response_model=SessionResponse,
)
async def patch_session(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    session_id: uuid.UUID,
    data: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a session. DM only."""
    await _require_campaign_dm(db, campaign_id, current_user.id)
    session = await get_session(db, session_id)
    if not session or session.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse.model_validate(await update_session(db, session, data))


@router.delete(
    "/orgs/{org_id}/campaigns/{campaign_id}/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a session. DM only."""
    await _require_campaign_dm(db, campaign_id, current_user.id)
    session = await get_session(db, session_id)
    if not session or session.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Session not found")
    await delete_session(db, session)


# ── Characters ────────────────────────────────────────────────────────────────
@router.post(
    "/orgs/{org_id}/campaigns/{campaign_id}/characters",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_character_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    data: CharacterCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a character. Players create their own (user_id = self).
    DMs can create NPCs (is_npc=true, user_id = None).
    """
    await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_member(db, campaign_id, current_user.id)

    # NPCs can only be created by the DM
    if data.is_npc and not await is_campaign_dm(db, campaign_id, current_user.id):
        raise HTTPException(status_code=403, detail="Only the DM can create NPCs")

    user_id = None if data.is_npc else current_user.id
    character = await create_character(db, campaign_id, org_id, user_id, data)
    return CharacterResponse.model_validate(character)


@router.get(
    "/orgs/{org_id}/campaigns/{campaign_id}/characters",
    response_model=list[CharacterResponse],
)
async def list_characters_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    include_npcs: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_member(db, campaign_id, current_user.id)
    return [
        CharacterResponse.model_validate(c)
        for c in await list_characters(db, campaign_id, include_npcs)
    ]


@router.patch(
    "/orgs/{org_id}/campaigns/{campaign_id}/characters/{character_id}",
    response_model=CharacterResponse,
)
async def patch_character(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    character_id: uuid.UUID,
    data: CharacterUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a character. Players update their own, DMs update any."""
    await _get_campaign_or_404(db, campaign_id, org_id)
    character = await get_character(db, character_id)
    if not character or character.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Character not found")

    is_dm = await is_campaign_dm(db, campaign_id, current_user.id)
    is_owner = character.user_id == current_user.id

    if not is_dm and not is_owner:
        raise HTTPException(
            status_code=403, detail="You can only edit your own character"
        )

    return CharacterResponse.model_validate(await update_character(db, character, data))


@router.delete(
    "/orgs/{org_id}/campaigns/{campaign_id}/characters/{character_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_character_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    character_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a character. DM only."""
    await _require_campaign_dm(db, campaign_id, current_user.id)
    character = await get_character(db, character_id)
    if not character or character.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Character not found")
    await delete_character(db, character)


# ── Quests ────────────────────────────────────────────────────────────────────
@router.post(
    "/orgs/{org_id}/campaigns/{campaign_id}/quests",
    response_model=QuestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_quest_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    data: QuestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Post a quest. DM only."""
    await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_dm(db, campaign_id, current_user.id)
    quest = await create_quest(db, campaign_id, org_id, current_user.id, data)
    return QuestResponse.model_validate(quest)


@router.get(
    "/orgs/{org_id}/campaigns/{campaign_id}/quests",
    response_model=list[QuestResponse],
)
async def list_quests_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_member(db, campaign_id, current_user.id)
    return [
        QuestResponse.model_validate(q)
        for q in await list_quests(db, campaign_id, status_filter)
    ]


@router.patch(
    "/orgs/{org_id}/campaigns/{campaign_id}/quests/{quest_id}",
    response_model=QuestResponse,
)
async def patch_quest(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    quest_id: uuid.UUID,
    data: QuestUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a quest. DM only."""
    await _require_campaign_dm(db, campaign_id, current_user.id)
    quest = await get_quest(db, quest_id)
    if not quest or quest.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Quest not found")
    return QuestResponse.model_validate(await update_quest(db, quest, data))


@router.delete(
    "/orgs/{org_id}/campaigns/{campaign_id}/quests/{quest_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_quest_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    quest_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a quest. DM only."""
    await _require_campaign_dm(db, campaign_id, current_user.id)
    quest = await get_quest(db, quest_id)
    if not quest or quest.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Quest not found")
    await delete_quest(db, quest)


# ── Notes ─────────────────────────────────────────────────────────────────────
@router.post(
    "/orgs/{org_id}/campaigns/{campaign_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_note_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a note. Any campaign member can add notes."""
    await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_member(db, campaign_id, current_user.id)
    note = await create_note(db, campaign_id, org_id, current_user.id, data)
    return NoteResponse.model_validate(note)


@router.get(
    "/orgs/{org_id}/campaigns/{campaign_id}/notes",
    response_model=list[NoteResponse],
)
async def list_notes_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    category: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_campaign_or_404(db, campaign_id, org_id)
    await _require_campaign_member(db, campaign_id, current_user.id)
    return [
        NoteResponse.model_validate(n)
        for n in await list_notes(db, campaign_id, category)
    ]


@router.patch(
    "/orgs/{org_id}/campaigns/{campaign_id}/notes/{note_id}",
    response_model=NoteResponse,
)
async def patch_note(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    note_id: uuid.UUID,
    data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a note. Author or DM only."""
    await _get_campaign_or_404(db, campaign_id, org_id)
    note = await get_note(db, note_id)
    if not note or note.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Note not found")

    is_dm = await is_campaign_dm(db, campaign_id, current_user.id)
    is_author = note.created_by == current_user.id

    if not is_dm and not is_author:
        raise HTTPException(
            status_code=403, detail="You can only edit your own notes"
        )

    return NoteResponse.model_validate(await update_note(db, note, data))


@router.delete(
    "/orgs/{org_id}/campaigns/{campaign_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_note_route(
    org_id: uuid.UUID,
    campaign_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a note. Author or DM only."""
    await _get_campaign_or_404(db, campaign_id, org_id)
    note = await get_note(db, note_id)
    if not note or note.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Note not found")

    is_dm = await is_campaign_dm(db, campaign_id, current_user.id)
    is_author = note.created_by == current_user.id

    if not is_dm and not is_author:
        raise HTTPException(
            status_code=403, detail="You can only delete your own notes"
        )

    await delete_note(db, note)