from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class AWSSettings(BaseSettings):
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "eu-west-1"
    s3_bucket_name: str

    model_config = ConfigDict(
        env_file=".env", extra="ignore"  # Allow extra fields but ignore them
    )


aws_settings = AWSSettings()
