import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import AccessType
from common.models import User
from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from projects import Project
from projects.service import create_project, check_project_access
from projects.schemas import ProjectInput
from sequences.enums import SequenceType
from sequences.schemas import SequenceInput
from sequences.service import (
    create_sequence,
    get_sequence,
    list_user_sequences,
    list_project_sequences,
    update_sequence,
    delete_sequence,
    check_sequence_is_valid,
)


async def test_create_sequence(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    sequence_input = SequenceInput(
        name="test_sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGCATGC",
        description="test",
        project_id=test_project.id,
    )

    sequence = await create_sequence(sequence_input, test_user.id, test_session)
    assert sequence.model_dump() == {
        "id": sequence.id,
        "description": "test",
        "gc_content": 0.5,
        "length": 8,
        "molecular_weight": 0.0,
        "name": "test_sequence",
        "project_id": test_project.id,
        "sequence_data": "ATGCATGC",
        "sequence_type": SequenceType.DNA,
        "user_id": test_user.id,
    }


async def test_create_sequence_invalid_dna(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    sequence_input = SequenceInput(
        name="invalid_dna",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGCXYZ",  # Invalid characters for DNA
        description="test",
        project_id=test_project.id,
    )

    with pytest.raises(ValidationError):
        await create_sequence(sequence_input, test_user.id, test_session)


async def test_create_sequence_invalid_rna(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    sequence_input = SequenceInput(
        name="invalid_rna",
        sequence_type=SequenceType.RNA,
        sequence_data="AUGCAUGCT",  # T is not valid in RNA
        description="test",
        project_id=test_project.id,
    )

    with pytest.raises(ValidationError):
        await create_sequence(sequence_input, test_user.id, test_session)


async def test_create_sequence_invalid_protein(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    sequence_input = SequenceInput(
        name="invalid_protein",
        sequence_type=SequenceType.PROTEIN,
        sequence_data="ACDEFGXYZ",  # X, Z not in standard amino acids
        description="test",
        project_id=test_project.id,
    )

    with pytest.raises(ValidationError):
        await create_sequence(sequence_input, test_user.id, test_session)


async def test_create_sequence_nonexistent_project(
    test_session: AsyncSession, test_user: User
):
    sequence_input = SequenceInput(
        name="test_sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=99999,
    )

    with pytest.raises(NotFoundError):
        await create_sequence(sequence_input, test_user.id, test_session)


async def test_create_sequence_in_other_users_project(
    test_session: AsyncSession, test_user: User, test_user_2: User
):
    # Create project as test_user
    project_in = ProjectInput(name="User 1 Project", is_public=False)
    project = await create_project(test_session, test_user.id, project_in)

    # Try to create sequence as test_user_2
    sequence_input = SequenceInput(
        name="test_sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=project.id,
    )

    with pytest.raises(NotFoundError):
        await create_sequence(sequence_input, test_user_2.id, test_session)


async def test_get_sequence_as_owner(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    sequence_input = SequenceInput(
        name="my_sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=test_project.id,
    )
    created = await create_sequence(sequence_input, test_user.id, test_session)

    sequence = await get_sequence(created.id, test_user.id, test_session)

    assert sequence.id == created.id
    assert sequence.name == "my_sequence"


async def test_get_sequence_in_public_project_as_other_user(
    test_session: AsyncSession, test_user: User, test_user_2: User
):
    # Create public project
    project_in = ProjectInput(name="Public Project", is_public=True)
    project = await create_project(test_session, test_user.id, project_in)

    # Create sequence
    sequence_input = SequenceInput(
        name="public_sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=project.id,
    )
    created = await create_sequence(sequence_input, test_user.id, test_session)

    # Get as other user
    sequence = await get_sequence(created.id, test_user_2.id, test_session)
    assert sequence.id == created.id


async def test_get_sequence_in_private_project_as_other_user(
    test_session: AsyncSession, test_user: User, test_user_2: User
):
    # Create private project
    project_in = ProjectInput(name="Private Project", is_public=False)
    project = await create_project(test_session, test_user.id, project_in)

    # Create sequence
    sequence_input = SequenceInput(
        name="private_sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=project.id,
    )
    created = await create_sequence(sequence_input, test_user.id, test_session)

    # Try to get as other user
    with pytest.raises(NotFoundError):
        await get_sequence(created.id, test_user_2.id, test_session)


async def test_get_nonexistent_sequence(test_session: AsyncSession, test_user: User):
    with pytest.raises(NotFoundError):
        await get_sequence(99999, test_user.id, test_session)


async def test_list_user_sequences(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    for i in range(3):
        sequence_input = SequenceInput(
            name=f"sequence_{i}",
            sequence_type=SequenceType.DNA,
            sequence_data="ATGC",
            project_id=test_project.id,
        )
        await create_sequence(sequence_input, test_user.id, test_session)

    sequences = await list_user_sequences(test_user.id, test_session)
    assert len(sequences) == 3


async def test_list_user_sequences_pagination(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    for i in range(5):
        sequence_input = SequenceInput(
            name=f"sequence_{i}",
            sequence_type=SequenceType.DNA,
            sequence_data="ATGC",
            project_id=test_project.id,
        )
        await create_sequence(sequence_input, test_user.id, test_session)

    page1 = await list_user_sequences(test_user.id, test_session, skip=0, limit=2)
    assert len(page1) == 2

    page2 = await list_user_sequences(test_user.id, test_session, skip=2, limit=2)
    assert len(page2) == 2

    assert page1[0].id != page2[0].id


async def test_list_user_sequences_empty(test_session: AsyncSession, test_user: User):
    sequences = await list_user_sequences(test_user.id, test_session)
    assert len(sequences) == 0


async def test_list_project_sequences(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    for i in range(3):
        sequence_input = SequenceInput(
            name=f"sequence_{i}",
            sequence_type=SequenceType.DNA,
            sequence_data="ATGC",
            project_id=test_project.id,
        )
        await create_sequence(sequence_input, test_user.id, test_session)

    sequences = await list_project_sequences(
        test_project.id, test_user.id, test_session
    )
    assert len(sequences) == 3


async def test_list_project_sequences_as_other_user_public_project(
    test_session: AsyncSession, test_user: User, test_user_2: User
):
    # Create public project
    project_in = ProjectInput(name="Public Project", is_public=True)
    project = await create_project(test_session, test_user.id, project_in)

    # Create sequences
    for i in range(2):
        sequence_input = SequenceInput(
            name=f"sequence_{i}",
            sequence_type=SequenceType.DNA,
            sequence_data="ATGC",
            project_id=project.id,
        )
        await create_sequence(sequence_input, test_user.id, test_session)

    # List as other user
    sequences = await list_project_sequences(project.id, test_user_2.id, test_session)
    assert len(sequences) == 2


async def test_list_project_sequences_as_other_user_private_project(
    test_session: AsyncSession, test_user: User, test_user_2: User
):
    # Create private project
    project_in = ProjectInput(name="Private Project", is_public=False)
    project = await create_project(test_session, test_user.id, project_in)

    # Try to list as other user
    with pytest.raises(NotFoundError):
        await list_project_sequences(project.id, test_user_2.id, test_session)


async def test_list_project_sequences_nonexistent_project(
    test_session: AsyncSession, test_user: User
):
    with pytest.raises(NotFoundError):
        await list_project_sequences(99999, test_user.id, test_session)


async def test_update_sequence_as_owner(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    sequence_input = SequenceInput(
        name="original_name",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=test_project.id,
    )
    created = await create_sequence(sequence_input, test_user.id, test_session)

    update_input = SequenceInput(
        name="updated_name",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGCATGC",
        description="Updated description",
        project_id=test_project.id,
    )

    updated = await update_sequence(
        created.id, test_user.id, update_input, test_session
    )

    assert updated.name == "updated_name"
    assert updated.sequence_data == "ATGCATGC"
    assert updated.description == "Updated description"
    assert updated.length == 8


async def test_update_sequence_change_project(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    # Create second project
    project_in = ProjectInput(name="Second Project")
    project2 = await create_project(test_session, test_user.id, project_in)

    # Create sequence in first project
    sequence_input = SequenceInput(
        name="sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=test_project.id,
    )
    created = await create_sequence(sequence_input, test_user.id, test_session)

    # Update to move to second project
    update_input = SequenceInput(
        name="sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=project2.id,
    )

    updated = await update_sequence(
        created.id, test_user.id, update_input, test_session
    )

    assert updated.project_id == project2.id


async def test_update_sequence_change_to_other_users_project(
    test_session: AsyncSession,
    test_user: User,
    test_user_2: User,
    test_project: Project,
):
    # Create second user's project
    project_in = ProjectInput(name="User 2 Project")
    project2 = await create_project(test_session, test_user_2.id, project_in)

    # Create sequence in first project
    sequence_input = SequenceInput(
        name="sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=test_project.id,
    )
    created = await create_sequence(sequence_input, test_user.id, test_session)

    # Try to move to user 2's project
    update_input = SequenceInput(
        name="sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=project2.id,
    )

    with pytest.raises(NotFoundError):
        await update_sequence(created.id, test_user.id, update_input, test_session)


async def test_update_sequence_invalid_data(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    sequence_input = SequenceInput(
        name="sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=test_project.id,
    )
    created = await create_sequence(sequence_input, test_user.id, test_session)

    update_input = SequenceInput(
        name="sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGCXYZ",  # Invalid
        project_id=test_project.id,
    )

    with pytest.raises(ValidationError):
        await update_sequence(created.id, test_user.id, update_input, test_session)


async def test_update_sequence_as_non_owner(
    test_session: AsyncSession, test_user: User, test_user_2: User
):
    # Create public project and sequence
    project_in = ProjectInput(name="Public Project", is_public=True)
    project = await create_project(test_session, test_user.id, project_in)

    sequence_input = SequenceInput(
        name="sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=project.id,
    )
    created = await create_sequence(sequence_input, test_user.id, test_session)

    # Try to update as other user
    update_input = SequenceInput(
        name="hacked_name",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=project.id,
    )

    with pytest.raises(PermissionDeniedError):
        await update_sequence(created.id, test_user_2.id, update_input, test_session)


async def test_update_nonexistent_sequence(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    update_input = SequenceInput(
        name="sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=test_project.id,
    )

    with pytest.raises(NotFoundError):
        await update_sequence(99999, test_user.id, update_input, test_session)


async def test_delete_sequence_as_owner(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    sequence_input = SequenceInput(
        name="to_delete",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=test_project.id,
    )
    created = await create_sequence(sequence_input, test_user.id, test_session)

    await delete_sequence(created.id, test_user.id, test_session)

    # Verify it's deleted
    with pytest.raises(NotFoundError):
        await get_sequence(created.id, test_user.id, test_session)


async def test_delete_sequence_as_non_owner(
    test_session: AsyncSession, test_user: User, test_user_2: User
):
    # Create public project and sequence
    project_in = ProjectInput(name="Public Project", is_public=True)
    project = await create_project(test_session, test_user.id, project_in)

    sequence_input = SequenceInput(
        name="protected_sequence",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGC",
        project_id=project.id,
    )
    created = await create_sequence(sequence_input, test_user.id, test_session)

    # Try to delete as other user
    with pytest.raises(PermissionDeniedError):
        await delete_sequence(created.id, test_user_2.id, test_session)


async def test_delete_nonexistent_sequence(test_session: AsyncSession, test_user: User):
    with pytest.raises(NotFoundError):
        await delete_sequence(99999, test_user.id, test_session)


# Unit tests for sequence validation


@pytest.mark.parametrize(
    "sequence_data,sequence_type,expected",
    [
        # Valid DNA sequences
        ("ATGC", SequenceType.DNA, True),
        ("ATGCATGC", SequenceType.DNA, True),
        ("AAAATTTTGGGGCCCC", SequenceType.DNA, True),
        ("atgc", SequenceType.DNA, True),  # Lowercase should work
        ("ATGCatgc", SequenceType.DNA, True),  # Mixed case
        # Invalid DNA sequences
        ("ATGCU", SequenceType.DNA, False),  # U is RNA
        ("ATGCXYZ", SequenceType.DNA, False),  # Invalid characters
        ("ATGC123", SequenceType.DNA, False),  # Numbers
        ("ATG-C", SequenceType.DNA, False),  # Special characters
        # Valid RNA sequences
        ("AUGC", SequenceType.RNA, True),
        ("AUGCAUGC", SequenceType.RNA, True),
        ("AAAAUUUUGGGGCCCC", SequenceType.RNA, True),
        ("augc", SequenceType.RNA, True),  # Lowercase
        ("AUGCaugc", SequenceType.RNA, True),  # Mixed case
        # Invalid RNA sequences
        ("AUGCT", SequenceType.RNA, False),  # T is DNA
        ("AUGCXYZ", SequenceType.RNA, False),  # Invalid characters
        ("AUGC123", SequenceType.RNA, False),  # Numbers
        # Valid protein sequences
        ("ACDEFGHIKLMNPQRSTVWY", SequenceType.PROTEIN, True),
        ("MKVLWAALLVTFLAGCQAKVE", SequenceType.PROTEIN, True),
        ("acdefg", SequenceType.PROTEIN, True),  # Lowercase
        ("ACDEFGacdefg", SequenceType.PROTEIN, True),  # Mixed case
        # Invalid protein sequences
        ("ACDEFGXYZ", SequenceType.PROTEIN, False),  # X, Z not in standard set
        ("ACDEFG123", SequenceType.PROTEIN, False),  # Numbers
        ("ACDEFG-", SequenceType.PROTEIN, False),  # Special characters
        # Edge cases
        ("", SequenceType.DNA, True),  # Empty string
        ("A", SequenceType.DNA, True),  # Single character
        ("U", SequenceType.RNA, True),  # Single RNA base
        ("M", SequenceType.PROTEIN, True),  # Single amino acid
    ],
)
def test_check_sequence_is_valid(
    sequence_data: str, sequence_type: SequenceType, expected: bool
):
    """Test sequence validation for different types and data"""
    result = check_sequence_is_valid(sequence_data, sequence_type)
    assert result == expected


# Integration tests for check_project_access


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
