"""完整备份文件与恢复请求契约。"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr

from movie_scheduler.features.movie.schemas import MovieChannel
from movie_scheduler.shared.types import SuccessEnvelope

BackupId = Annotated[StrictInt, Field(ge=-9007199254740991, le=9007199254740991)]


class _BackupRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class CinemaBackup(_BackupRecord):
    id: BackupId
    name: StrictStr
    address: StrictStr
    price: StrictStr | None
    allow_refund: StrictBool | None
    updated_at: datetime | None


class MovieBackup(_BackupRecord):
    id: BackupId
    title: StrictStr
    score: StrictStr | None
    douban_url: StrictStr | None
    genres: StrictStr | None
    actors: StrictStr | None
    release_date: StrictStr | None
    is_showing: StrictBool
    is_wished: StrictBool
    is_skipped: StrictBool
    is_watched: StrictBool
    channels: list[MovieChannel] = Field(max_length=1)
    viewing_location: Literal["home", "cinema"] | None
    director: StrictStr | None
    country: StrictStr | None
    language: StrictStr | None
    duration: StrictStr | None
    description: StrictStr | None
    first_showing_at: datetime | None
    updated_at: datetime | None
    shows_updated_at: datetime | None


class MovieShowBackup(_BackupRecord):
    id: BackupId
    movie_id: BackupId
    cinema_id: BackupId
    cinema_name: StrictStr
    date: StrictStr
    time: StrictStr
    price: StrictStr | None
    created_at: datetime


class PlanningItemBackup(_BackupRecord):
    id: BackupId
    show_key: StrictStr
    movie_id: BackupId
    movie_title: StrictStr
    date: StrictStr
    time: StrictStr
    cinema_id: BackupId
    cinema_name: StrictStr
    price: StrictStr | None
    duration_minutes: StrictInt | None
    purchased: StrictBool
    created_at: datetime
    updated_at: datetime


class BackupData(_BackupRecord):
    application: Literal["movie-scheduler"]
    format_version: Literal[1]
    exported_at: datetime
    cinemas: list[CinemaBackup]
    movies: list[MovieBackup]
    movie_shows: list[MovieShowBackup]
    planning_items: list[PlanningItemBackup]


class BackupResponse(SuccessEnvelope):
    model_config = ConfigDict(extra="forbid")
    success: StrictBool = True
    data: BackupData


class RestoreBackupRequest(_BackupRecord):
    backup: BackupResponse
    confirm_replace: StrictBool


class BackupCounts(BaseModel):
    cinemas: int
    movies: int
    movie_shows: int
    planning_items: int


class RestoreBackupResponse(SuccessEnvelope):
    data: BackupCounts
