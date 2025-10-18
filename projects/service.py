from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, PermissionDeniedError
from projects import schemas, models


async def create_project(
    db: AsyncSession, user_id: int, project_in: schemas.ProjectCreate
) -> schemas.ProjectResponse:
    db_project = models.Project(
        name=project_in.name,
        description=project_in.description,
        is_public=project_in.is_public if project_in.is_public is not None else False,
        user_id=user_id,
    )

    db.add(db_project)
    await db.flush()

    return schemas.ProjectResponse.model_validate(db_project)


async def get_project(
    db: AsyncSession, project_id: int, user_id: int
) -> schemas.ProjectResponse:
    stmt = select(models.Project).where(models.Project.id == project_id)
    project = await db.scalar(stmt)

    if not project:
        raise NotFoundError("Project", project_id)

    # Check if user has access
    if project.user_id != user_id and not project.is_public:
        raise PermissionDeniedError("access", "project")

    return schemas.ProjectResponse.model_validate(project)


async def list_user_projects(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
) -> list[schemas.ProjectResponse]:
    """List all projects owned by a user"""
    stmt = (
        select(models.Project)
        .where(models.Project.user_id == user_id)
        .order_by(models.Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    results = await db.scalars(stmt)
    return [schemas.ProjectResponse.model_validate(project) for project in results]


async def update_project(
    db: AsyncSession, project_id: int, user_id: int, project_in: schemas.ProjectUpdate
) -> schemas.ProjectResponse:
    stmt = select(models.Project).where(models.Project.id == project_id)
    db_project = await db.scalar(stmt)

    if not db_project:
        raise NotFoundError("Project", project_id)

    if db_project.user_id != user_id:
        if db_project.is_public:
            raise PermissionDeniedError("delete", "project")
        else:
            raise NotFoundError("project", project_id)

    if project_in.name is not None:
        db_project.name = project_in.name
    if project_in.description is not None:
        db_project.description = project_in.description
    if project_in.is_public is not None:
        db_project.is_public = project_in.is_public

    await db.flush()

    return schemas.ProjectResponse.model_validate(db_project)


async def delete_project(db: AsyncSession, project_id: int, user_id: int) -> None:
    stmt = select(models.Project).where(models.Project.id == project_id)
    db_project = await db.scalar(stmt)

    if not db_project:
        raise NotFoundError("Project", project_id)

    if db_project.user_id != user_id:
        if db_project.is_public:
            raise PermissionDeniedError("delete", "project")
        else:
            raise NotFoundError("project", project_id)

    await db.delete(db_project)
    await db.flush()
