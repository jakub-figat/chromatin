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
from projects.schemas import ProjectInput


async def test_create_project(test_session: AsyncSession, test_user):
    project_in = ProjectInput(
        name="Test Project", description="A test project", is_public=False
    )

    project = await create_project(test_session, test_user.id, project_in)

    assert project.id is not None
    assert project.name == "Test Project"
    assert project.description == "A test project"
    assert project.is_public is False
    assert project.user_id == test_user.id


async def test_get_project_as_owner(test_session: AsyncSession, test_user):
    project_in = ProjectInput(name="My Project", is_public=False)
    created = await create_project(test_session, test_user.id, project_in)

    project = await get_project(test_session, created.id, test_user.id)

    assert project.id == created.id
    assert project.name == "My Project"


async def test_get_public_project_as_other_user(
    test_session: AsyncSession, test_user, test_user_2
):
    project_in = ProjectInput(name="Public Project", is_public=True)
    created = await create_project(test_session, test_user.id, project_in)

    project = await get_project(test_session, created.id, test_user_2.id)

    assert project.id == created.id


async def test_get_private_project_as_other_user(
    test_session: AsyncSession, test_user, test_user_2
):
    project_in = ProjectInput(name="Private Project", is_public=False)
    created = await create_project(test_session, test_user.id, project_in)

    with pytest.raises(NotFoundError):
        await get_project(test_session, created.id, test_user_2.id)


async def test_get_nonexistent_project(test_session: AsyncSession, test_user):
    with pytest.raises(NotFoundError):
        await get_project(test_session, 99999, test_user.id)


async def test_list_user_projects(test_session: AsyncSession, test_user):
    for i in range(3):
        project_in = ProjectInput(name=f"Project {i}")
        await create_project(test_session, test_user.id, project_in)

    projects = await list_user_projects(test_session, test_user.id)
    assert len(projects) == 3


async def test_list_user_projects_pagination(test_session: AsyncSession, test_user):
    for i in range(5):
        project_in = ProjectInput(name=f"Project {i}")
        await create_project(test_session, test_user.id, project_in)

    page1 = await list_user_projects(test_session, test_user.id, skip=0, limit=2)
    assert len(page1) == 2

    page2 = await list_user_projects(test_session, test_user.id, skip=2, limit=2)
    assert len(page2) == 2

    assert page1[0].id != page2[0].id


async def test_list_user_projects_empty(test_session: AsyncSession, test_user):
    projects = await list_user_projects(test_session, test_user.id)

    assert len(projects) == 0


async def test_update_project_as_owner(test_session: AsyncSession, test_user):
    project_in = ProjectInput(name="Original Name", is_public=False)
    created = await create_project(test_session, test_user.id, project_in)

    update_in = ProjectInput(
        name="Updated Name", description="New description", is_public=True
    )

    updated = await update_project(test_session, created.id, test_user.id, update_in)

    assert updated.name == "Updated Name"
    assert updated.description == "New description"
    assert updated.is_public is True


async def test_update_project_as_non_owner(
    test_session: AsyncSession, test_user, test_user_2
):
    project_in = ProjectInput(name="User Project", is_public=True)
    created = await create_project(test_session, test_user.id, project_in)

    update_in = ProjectInput(name="Hacked Name")

    with pytest.raises(PermissionDeniedError):
        await update_project(test_session, created.id, test_user_2.id, update_in)


async def test_update_nonexistent_project(test_session: AsyncSession, test_user):
    update_in = ProjectInput(name="New Name")

    with pytest.raises(NotFoundError):
        await update_project(test_session, 99999, test_user.id, update_in)


async def test_delete_project_as_owner(test_session: AsyncSession, test_user):
    project_in = ProjectInput(name="To Delete")
    created = await create_project(test_session, test_user.id, project_in)

    await delete_project(test_session, created.id, test_user.id)

    # Verify it's deleted
    with pytest.raises(NotFoundError):
        await get_project(test_session, created.id, test_user.id)


async def test_delete_project_as_non_owner(
    test_session: AsyncSession, test_user, test_superuser
):
    project_in = ProjectInput(name="Protected Project", is_public=True)
    created = await create_project(test_session, test_user.id, project_in)

    with pytest.raises(PermissionDeniedError):
        await delete_project(test_session, created.id, test_superuser.id)


async def test_delete_nonexistent_project(test_session: AsyncSession, test_user):
    with pytest.raises(NotFoundError):
        await delete_project(test_session, 99999, test_user.id)
