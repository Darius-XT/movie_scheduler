"""业务备份接口。"""

from fastapi import APIRouter, Response

from movie_scheduler.features.backup.schemas import BackupResponse, RestoreBackupRequest, RestoreBackupResponse
from movie_scheduler.features.backup.service import backup_service

router = APIRouter(prefix="/backups", tags=["backups"])


@router.get("/export", response_model=BackupResponse)
async def export_backup(response: Response) -> BackupResponse:
    backup = await backup_service.export_backup()
    timestamp = backup.data.exported_at.strftime("%Y%m%d-%H%M%S")
    response.headers["Content-Disposition"] = f'attachment; filename="movie-scheduler-{timestamp}.json"'
    response.headers["Cache-Control"] = "no-store"
    return backup


@router.post("/import", response_model=RestoreBackupResponse)
async def restore_backup(request: RestoreBackupRequest) -> RestoreBackupResponse:
    return RestoreBackupResponse(data=await backup_service.restore_backup(request))
