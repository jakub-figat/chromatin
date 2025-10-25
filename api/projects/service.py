from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import AccessType
from core.exceptions import NotFoundError, PermissionDeniedError
from projects import Project
from projects import models, schemas
from projects.schemas import ProjectOutput


def check_project_access(
    project: Project | ProjectOutput,
    user_id: int,
    access_type: AccessType = AccessType.READ,
    raise_exception: bool = False,
) -> bool:
    if project.user_id == user_id:
        return True

    access = access_type == AccessType.READ and project.is_public

    if raise_exception and not access:
        if project.is_public:
            raise PermissionDeniedError("update", "project")
        else:
            raise NotFoundError("project", project.id)

    return access


async def create_project(
    db: AsyncSession, user_id: int, project_input: schemas.ProjectInput
) -> schemas.ProjectOutput:
    db_project = models.Project(
        name=project_input.name,
        description=project_input.description,
        is_public=project_input.is_public
        if project_input.is_public is not None
        else False,
        user_id=user_id,
    )

    db.add(db_project)
    await db.flush()
    await db.refresh(db_project)

    return schemas.ProjectOutput.model_validate(db_project)


async def get_project(
    db: AsyncSession, project_id: int, user_id: int
) -> schemas.ProjectOutput:
    stmt = select(models.Project).where(models.Project.id == project_id)
    project = await db.scalar(stmt)

    if not project:
        raise NotFoundError("Project", project_id)

    check_project_access(project, user_id, AccessType.READ, raise_exception=True)

    return schemas.ProjectOutput.model_validate(project)


async def list_user_projects(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
) -> list[schemas.ProjectOutput]:
    """List all projects owned by a user"""
    stmt = (
        select(models.Project)
        .where(models.Project.user_id == user_id)
        .order_by(models.Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    results = await db.scalars(stmt)
    return [schemas.ProjectOutput.model_validate(project) for project in results]


async def update_project(
    db: AsyncSession, project_id: int, user_id: int, project_input: schemas.ProjectInput
) -> schemas.ProjectOutput:
    stmt = select(models.Project).where(models.Project.id == project_id)
    db_project = await db.scalar(stmt)

    if not db_project:
        raise NotFoundError("Project", project_id)

    check_project_access(db_project, user_id, AccessType.WRITE, raise_exception=True)

    db_project.name = project_input.name
    db_project.description = project_input.description
    db_project.is_public = project_input.is_public

    await db.flush()
    await db.refresh(db_project)

    return schemas.ProjectOutput.model_validate(db_project)


async def delete_project(db: AsyncSession, project_id: int, user_id: int) -> None:
    stmt = select(models.Project).where(models.Project.id == project_id)
    db_project = await db.scalar(stmt)

    if not db_project:
        raise NotFoundError("Project", project_id)

    check_project_access(db_project, user_id, AccessType.WRITE, raise_exception=True)

    await db.delete(db_project)
    await db.flush()
