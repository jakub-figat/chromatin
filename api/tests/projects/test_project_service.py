import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import AccessType
from common.models import User
from core.exceptions import NotFoundError, PermissionDeniedError
from projects.service import (
    create_project,
    get_project,
    list_user_projects,
    update_project,
    delete_project,
    check_project_access,
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


@pytest.mark.parametrize(
    "is_public,is_owner,access_type,should_pass,expected_exception",
    [
        # Owner always has access
        (True, True, AccessType.READ, True, None),
        (True, True, AccessType.WRITE, True, None),
        (False, True, AccessType.READ, True, None),
        (False, True, AccessType.WRITE, True, None),
        # Non-owner on public project
        (True, False, AccessType.READ, True, None),  # Can read public
        (
            True,
            False,
            AccessType.WRITE,
            False,
            PermissionDeniedError,
        ),  # Cannot write public
        # Non-owner on private project
        (
            False,
            False,
            AccessType.READ,
            False,
            NotFoundError,
        ),  # Cannot read private (appears as not found)
        (
            False,
            False,
            AccessType.WRITE,
            False,
            NotFoundError,
        ),  # Cannot write private (appears as not found)
    ],
)
async def test_check_project_access(
    test_session: AsyncSession,
    test_user: User,
    test_user_2: User,
    is_public: bool,
    is_owner: bool,
    access_type: AccessType,
    should_pass: bool,
    expected_exception: type[Exception] | None,
):
    """Test project access control for different scenarios"""
    # Create project as test_user
    project_in = ProjectInput(name="Test Project", is_public=is_public)
    project = await create_project(test_session, test_user.id, project_in)

    # Determine which user to check access for
    user_id = test_user.id if is_owner else test_user_2.id

    # Test with raise_exception=False
    result = check_project_access(project, user_id, access_type, raise_exception=False)
    assert result == should_pass

    # Test with raise_exception=True
    if should_pass:
        # Should not raise
        check_project_access(project, user_id, access_type, raise_exception=True)
    else:
        # Should raise the specific exception
        with pytest.raises(expected_exception):
            check_project_access(project, user_id, access_type, raise_exception=True)
