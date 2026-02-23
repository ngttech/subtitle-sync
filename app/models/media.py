from pydantic import BaseModel


class Movie(BaseModel):
    id: int
    title: str
    year: int = 0
    file_path: str = ""
    folder_path: str = ""
    has_file: bool = False
    size_on_disk: int = 0
    added: str = ""


class Series(BaseModel):
    id: int
    title: str
    year: int = 0
    path: str = ""
    season_count: int = 0
    episode_count: int = 0
    added: str = ""


class Episode(BaseModel):
    id: int
    series_id: int
    series_title: str = ""
    season_number: int
    episode_number: int
    title: str = ""
    file_path: str = ""
    has_file: bool = False
