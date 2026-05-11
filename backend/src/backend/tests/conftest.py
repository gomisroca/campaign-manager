import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.db.session import Base, get_db
from backend.main import app
from backend.models.user import User
from backend.models.org import Org
from backend.models.membership import Membership
from backend.services.auth_service import hash_password, create_access_token

# ── Test database ─────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Session-scoped setup: create tables once per test run ─────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ── Function-scoped DB session ────────────────────
@pytest_asyncio.fixture
async def db():
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


# ── HTTP client wired to test DB ──────────────────────────────────────────────
@pytest_asyncio.fixture
async def client(db: AsyncSession):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Reusable test data fixtures ───────────────────────────────────────────────
@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    user = User(
        email="test@example.com",
        hashed_password=hash_password("password123"),
        full_name="Test User",
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def test_user_2(db: AsyncSession) -> User:
    user = User(
        email="other@example.com",
        hashed_password=hash_password("password123"),
        full_name="Other User",
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Authorization headers for test_user."""
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_headers_2(test_user_2: User) -> dict:
    """Authorization headers for test_user_2."""
    token = create_access_token(test_user_2.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_org(db: AsyncSession, test_user: User) -> Org:
    org = Org(name="Test Org", slug="test-org")
    db.add(org)
    await db.flush()
    membership = Membership(user_id=test_user.id, org_id=org.id, role="owner")
    db.add(membership)
    await db.flush()
    return org