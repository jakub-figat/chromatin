"""Test project service functions"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, PermissionDeniedError
from projects.service import (
    create_project,
    get_project,
    list_user_projects,
    update_project,
    delete_project,
)
from projects.schemas import ProjectCreate, ProjectUpdate


@pytest.mark.asyncio
async def test_create_project(test_session: AsyncSession, test_user):
    """Test creating a project"""
    project_in = ProjectCreate(
        name="Test Project", description="A test project", is_public=False
    )

    project = await create_project(test_session, test_user.id, project_in)

    assert project.id is not None
    assert project.name == "Test Project"
    assert project.description == "A test project"
    assert project.is_public is False
    assert project.user_id == test_user.id


@pytest.mark.asyncio
async def test_create_project_defaults(test_session: AsyncSession, test_user):
    """Test creating project with default values"""
    project_in = ProjectCreate(
        name="Minimal Project",
        description=None,
    )

    project = await create_project(test_session, test_user.id, project_in)

    assert project.is_public is False
    assert project.description is None
    assert project.is_public is False


@pytest.mark.asyncio
async def test_get_project_as_owner(test_session: AsyncSession, test_user):
    """Test getting project as owner"""
    project_in = ProjectCreate(name="My Project", is_public=False)
    created = await create_project(test_session, test_user.id, project_in)

    project = await get_project(test_session, created.id, test_user.id)

    assert project.id == created.id
    assert project.name == "My Project"


@pytest.mark.asyncio
async def test_get_public_project_as_other_user(
    test_session: AsyncSession, test_user, test_superuser
):
    """Test getting public project as non-owner"""
    project_in = ProjectCreate(name="Public Project", is_public=True)
    created = await create_project(test_session, test_user.id, project_in)

    # test_superuser (different user) can access public project
    project = await get_project(test_session, created.id, test_superuser.id)

    assert project.id == created.id


@pytest.mark.asyncio
async def test_get_private_project_as_other_user(
    test_session: AsyncSession, test_user, test_superuser
):
    """Test that accessing private project as non-owner raises PermissionDenied"""
    project_in = ProjectCreate(name="Private Project", is_public=False)
    created = await create_project(test_session, test_user.id, project_in)

    with pytest.raises(PermissionDeniedError):
        await get_project(test_session, created.id, test_superuser.id)


@pytest.mark.asyncio
async def test_get_nonexistent_project(test_session: AsyncSession, test_user):
    """Test getting non-existent project raises NotFoundError"""
    with pytest.raises(NotFoundError) as exc_info:
        await get_project(test_session, 99999, test_user.id)

    assert "Project" in str(exc_info.value)
    assert "99999" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_user_projects(test_session: AsyncSession, test_user):
    """Test listing user's projects"""
    for i in range(3):
        project_in = ProjectCreate(name=f"Project {i}")
        await create_project(test_session, test_user.id, project_in)

    projects = await list_user_projects(test_session, test_user.id)
    assert len(projects) == 3


@pytest.mark.asyncio
async def test_list_user_projects_pagination(test_session: AsyncSession, test_user):
    """Test pagination in project listing"""
    # Create 5 projects
    for i in range(5):
        project_in = ProjectCreate(name=f"Project {i}")
        await create_project(test_session, test_user.id, project_in)

    # Get first page
    page1 = await list_user_projects(test_session, test_user.id, skip=0, limit=2)
    assert len(page1) == 2

    # Get second page
    page2 = await list_user_projects(test_session, test_user.id, skip=2, limit=2)
    assert len(page2) == 2

    # No overlap
    assert page1[0].id != page2[0].id


@pytest.mark.asyncio
async def test_list_user_projects_empty(test_session: AsyncSession, test_user):
    """Test listing projects when user has none"""
    projects = await list_user_projects(test_session, test_user.id)

    assert len(projects) == 0


@pytest.mark.asyncio
async def test_list_user_projects_only_own(
    test_session: AsyncSession, test_user, test_superuser
):
    """Test that listing only returns user's own projects"""
    # Create project for test_user
    project_in = ProjectCreate(name="User Project")
    await create_project(test_session, test_user.id, project_in)

    # Create project for test_superuser
    project_in2 = ProjectCreate(name="Admin Project")
    await create_project(test_session, test_superuser.id, project_in2)

    # Each user should only see their own
    user_projects = await list_user_projects(test_session, test_user.id)
    assert len(user_projects) == 1
    assert user_projects[0].name == "User Project"

    admin_projects = await list_user_projects(test_session, test_superuser.id)
    assert len(admin_projects) == 1
    assert admin_projects[0].name == "Admin Project"


@pytest.mark.asyncio
async def test_update_project_as_owner(test_session: AsyncSession, test_user):
    """Test updating project as owner"""
    project_in = ProjectCreate(name="Original Name", is_public=False)
    created = await create_project(test_session, test_user.id, project_in)

    update_in = ProjectUpdate(
        name="Updated Name", description="New description", is_public=True
    )

    updated = await update_project(test_session, created.id, test_user.id, update_in)

    assert updated.name == "Updated Name"
    assert updated.description == "New description"
    assert updated.is_public is True


@pytest.mark.asyncio
async def test_update_project_partial(test_session: AsyncSession, test_user):
    """Test partial update (only some fields)"""
    project_in = ProjectCreate(
        name="Original", description="Original desc", is_public=False
    )
    created = await create_project(test_session, test_user.id, project_in)

    # Only update name
    update_in = ProjectUpdate(name="New Name")
    updated = await update_project(test_session, created.id, test_user.id, update_in)

    assert updated.name == "New Name"
    assert updated.description == "Original desc"  # Unchanged
    assert updated.is_public is False  # Unchanged


@pytest.mark.asyncio
async def test_update_project_as_non_owner(
    test_session: AsyncSession, test_user, test_superuser
):
    """Test that non-owner cannot update project"""
    project_in = ProjectCreate(name="User Project", is_public=True)
    created = await create_project(test_session, test_user.id, project_in)

    update_in = ProjectUpdate(name="Hacked Name")

    with pytest.raises(PermissionDeniedError):
        await update_project(test_session, created.id, test_superuser.id, update_in)


@pytest.mark.asyncio
async def test_update_nonexistent_project(test_session: AsyncSession, test_user):
    """Test updating non-existent project raises NotFoundError"""
    update_in = ProjectUpdate(name="New Name")

    with pytest.raises(NotFoundError):
        await update_project(test_session, 99999, test_user.id, update_in)


@pytest.mark.asyncio
async def test_delete_project_as_owner(test_session: AsyncSession, test_user):
    """Test deleting project as owner"""
    project_in = ProjectCreate(name="To Delete")
    created = await create_project(test_session, test_user.id, project_in)

    await delete_project(test_session, created.id, test_user.id)

    # Verify it's deleted
    with pytest.raises(NotFoundError):
        await get_project(test_session, created.id, test_user.id)


@pytest.mark.asyncio
async def test_delete_project_as_non_owner(
    test_session: AsyncSession, test_user, test_superuser
):
    """Test that non-owner cannot delete project"""
    project_in = ProjectCreate(name="Protected Project", is_public=True)
    created = await create_project(test_session, test_user.id, project_in)

    with pytest.raises(PermissionDeniedError):
        await delete_project(test_session, created.id, test_superuser.id)


@pytest.mark.asyncio
async def test_delete_nonexistent_project(test_session: AsyncSession, test_user):
    """Test deleting non-existent project raises NotFoundError"""
    with pytest.raises(NotFoundError):
        await delete_project(test_session, 99999, test_user.id)
