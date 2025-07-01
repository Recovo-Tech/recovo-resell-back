import os
import uuid
from typing import List
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import io
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config.aws_config import aws_settings


class FileUploadService:
    """Service for handling file uploads to S3, particularly product images"""

    def __init__(self, bucket_name: str = None):
        self.bucket_name = bucket_name or aws_settings.s3_bucket_name
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_settings.aws_access_key_id,
            aws_secret_access_key=aws_settings.aws_secret_access_key,
            region_name=aws_settings.aws_region,
        )

    def _validate_image(self, file: UploadFile) -> None:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required"
            )
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(self.allowed_extensions)}",
            )
        # Note: UploadFile does not have .size, so you may want to check after reading

    def _generate_filename(
        self, original_filename: str, user_id: str = None, shopify_url: str = None
    ) -> str:
        file_extension = os.path.splitext(original_filename)[1].lower()
        unique_id = str(uuid.uuid4())

        # Create a more descriptive filename with user and shopify info
        filename_parts = [unique_id]

        if user_id:
            # Take first 8 characters of user ID for brevity
            user_part = str(user_id)[:8] if len(str(user_id)) > 8 else str(user_id)
            filename_parts.append(f"user_{user_part}")

        if shopify_url:
            # Extract domain from shopify URL and sanitize
            domain = (
                shopify_url.replace("https://", "").replace("http://", "").split("/")[0]
            )
            domain = domain.replace(".myshopify.com", "").replace(".", "_")[
                :20
            ]  # Limit length
            filename_parts.append(f"shop_{domain}")

        filename = "_".join(filename_parts) + file_extension
        return filename

    def _generate_s3_key(
        self, original_filename: str, user_id: str = None, shopify_url: str = None
    ) -> str:
        file_extension = os.path.splitext(original_filename)[1].lower()
        image_id = str(uuid.uuid4())
        shop_name = "unknownshop"
        if shopify_url:
            # Extract and sanitize shop name
            domain = (
                shopify_url.replace("https://", "").replace("http://", "").split("/")[0]
            )
            shop_name = domain.replace(".myshopify.com", "").replace(".", "_")[
                :32
            ]  # Limit length
        user_part = str(user_id) if user_id else "nouser"
        s3_key = (
            f"second_hand_products/{shop_name}/{user_part}/{image_id}{file_extension}"
        )
        return s3_key

    async def _optimize_image(
        self, file_content: bytes, max_width: int = 1200, quality: int = 85
    ) -> bytes:
        try:
            image = Image.open(io.BytesIO(file_content))
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True)
            return output.getvalue()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error processing image: {str(e)}",
            )

    async def upload_image(
        self,
        file: UploadFile,
        optimize: bool = True,
        user_id: str = None,
        shopify_url: str = None,
    ) -> str:
        self._validate_image(file)
        file_content = await file.read()
        if len(file_content) > self.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size too large. Maximum size: {self.max_file_size / (1024*1024):.1f}MB",
            )
        if optimize:
            file_content = await self._optimize_image(file_content)
        s3_key = self._generate_s3_key(file.filename, user_id, shopify_url)
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType="image/jpeg",
            )
            s3_url = f"https://{self.bucket_name}.s3.{aws_settings.aws_region}.amazonaws.com/{s3_key}"
            return s3_url
        except (BotoCoreError, ClientError) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload image to S3: {str(e)}",
            )

    async def upload_multiple_images(
        self,
        files: List[UploadFile],
        max_files: int = 10,
        user_id: str = None,
        shopify_url: str = None,
    ) -> List[str]:
        if len(files) > max_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many files. Maximum allowed: {max_files}",
            )
        uploaded_urls = []
        for file in files:
            url = await self.upload_image(
                file, user_id=user_id, shopify_url=shopify_url
            )
            uploaded_urls.append(url)
        return uploaded_urls

    def delete_image(self, s3_url: str) -> bool:
        """Delete an image from S3 given its URL"""
        try:
            s3_key = s3_url.split(f"{self.bucket_name}/")[-1]
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except Exception:
            return False

    def delete_multiple_images(self, s3_urls: List[str]) -> int:
        deleted_count = 0
        for url in s3_urls:
            if self.delete_image(url):
                deleted_count += 1
        return deleted_count
