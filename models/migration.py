from pydantic import BaseModel

class MigrationResult(BaseModel):
    migrated_code: str
    summary: str

class PathInputSchema(BaseModel):
    path: str