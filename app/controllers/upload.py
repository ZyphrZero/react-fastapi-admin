import os
import shutil
import uuid
from io import BytesIO
from datetime import datetime
from typing import Dict, List

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.settings.config import settings
from app.services.system_setting_service import system_setting_service

# Conditionally import oss2 and fall back to None when it is unavailable.
try:
    import oss2
    OSS_AVAILABLE = True
except ImportError:
    oss2 = None
    OSS_AVAILABLE = False


class UploadController:
    """File upload controller."""

    def ensure_storage_directory(self, path: str) -> None:
        """
        Ensure the storage directory exists and create it only when needed.

        Args:
            path: Directory path to create.
        """
        os.makedirs(path, exist_ok=True)

    def get_file_extension(self, filename: str) -> str:
        """Return the file extension."""
        return os.path.splitext(filename)[1] if "." in filename else ""

    async def get_storage_settings(self) -> dict:
        return await system_setting_service.get_runtime_storage_settings()

    @staticmethod
    def is_object_storage_enabled(storage_settings: dict) -> bool:
        return storage_settings.get("provider") == "oss"

    @staticmethod
    def is_local_file_key(file_key: str, storage_settings: dict) -> bool:
        local_full_url = storage_settings.get("local_full_url", "").rstrip("/")
        return file_key.startswith("/static/") or (local_full_url and file_key.startswith(local_full_url))

    def generate_oss_file_name(self, original_filename: str, extension_override: str | None = None) -> str:
        """Generate an object-storage filename based on the current time and a UUID."""
        ext = extension_override or self.get_file_extension(original_filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_uuid = str(uuid.uuid4()).replace("-", "")[:8]
        return f"{timestamp}_{random_uuid}{ext}"

    def convert_avatar_to_webp(self, file_content: bytes, max_edge: int = 512, quality: int = 82) -> bytes:
        """Convert an avatar image to WebP and constrain the final dimensions."""
        try:
            with Image.open(BytesIO(file_content)) as image:
                image = ImageOps.exif_transpose(image)

                if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
                    image = image.convert("RGBA")
                else:
                    image = image.convert("RGB")

                image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

                buffer = BytesIO()
                image.save(buffer, format="WEBP", quality=quality, method=6)
                return buffer.getvalue()
        except UnidentifiedImageError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法识别的图片文件") from exc
        except OSError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片处理失败，请更换文件重试") from exc

    def generate_oss_path(self, upload_dir: str, file_type: str = "common") -> str:
        """
        Generate an object-storage path based on file type and the current date.

        Args:
            upload_dir: Upload directory in object storage.
            file_type: File category used for classification, such as image or document.

        Returns:
            str: Object-storage path.
        """
        today = datetime.now()
        date_str = today.strftime("%Y%m%d")  # Use a compact YYYYMMDD date format.

        # Object storage always uses forward slashes. Replace Windows backslashes after joining.
        path = os.path.join(upload_dir, file_type, date_str)
        return path.replace("\\", "/")

    def generate_local_path(self, storage_settings: dict, file_type: str = "common") -> str:
        """
        Generate a local-storage path based on file type and the current date.

        Args:
            storage_settings: Current storage configuration.
            file_type: File category used for classification, such as image or document.

        Returns:
            tuple: (local filesystem path, URL path)
        """
        today = datetime.now()
        date_str = today.strftime("%Y%m%d")  # Use a compact YYYYMMDD date format.
        local_upload_dir = storage_settings["local_upload_dir"]
        local_url_prefix = storage_settings["local_url_prefix"]

        # Local filesystem path.
        fs_path = os.path.join(settings.storage_root_path, local_upload_dir, file_type, date_str)
        # URL path.
        url_path = os.path.join(local_url_prefix, file_type, date_str).replace("\\", "/")

        # Ensure the directory exists only when it is actually needed.
        self.ensure_storage_directory(fs_path)

        return fs_path, url_path

    async def check_image_file(self, file: UploadFile) -> bytes:
        """
        Validate an uploaded image file.

        Args:
            file: Uploaded file.

        Returns:
            bytes: File contents.

        Raises:
            HTTPException: Raised when the file is invalid.
        """
        # Validate the file type.
        file_extension = self.get_file_extension(file.filename).lower()
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的图片格式，仅支持: {', '.join(allowed_extensions)}",
            )

        # Read the file contents.
        file_content = await file.read()

        # Validate the file size with a 10 MB limit.
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"文件大小超出限制，最大允许10MB")

        return file_content

    async def check_file(self, file: UploadFile) -> bytes:
        """
        Validate a generic uploaded file.

        Args:
            file: Uploaded file.

        Returns:
            bytes: File contents.

        Raises:
            HTTPException: Raised when the file is invalid.
        """
        # Read the file contents.
        file_content = await file.read()

        # Validate the file size with a 10 MB limit.
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"文件大小超出限制，最大允许10MB")

        return file_content

    def validate_object_storage_config(self, storage_settings: dict) -> None:
        if not OSS_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="对象存储 SDK 不可用，请安装 oss2 或切换为本地存储",
            )

        required_fields = {
            "oss_access_key_id": "AccessKey ID",
            "oss_access_key_secret": "AccessKey Secret",
            "oss_bucket_name": "Bucket 名称",
            "oss_endpoint": "Endpoint",
        }
        missing_fields = [label for field, label in required_fields.items() if not storage_settings.get(field)]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"对象存储配置不完整，缺少: {', '.join(missing_fields)}",
            )

    def build_oss_bucket(self, storage_settings: dict):
        self.validate_object_storage_config(storage_settings)
        auth = oss2.Auth(storage_settings["oss_access_key_id"], storage_settings["oss_access_key_secret"])
        return oss2.Bucket(auth, storage_settings["oss_endpoint"], storage_settings["oss_bucket_name"])

    @staticmethod
    def build_oss_file_url(storage_settings: dict, object_key: str) -> str:
        bucket_domain = storage_settings.get("oss_bucket_domain", "")
        if bucket_domain:
            return f"https://{bucket_domain}/{object_key}"
        return f"https://{storage_settings['oss_bucket_name']}.{storage_settings['oss_endpoint']}/{object_key}"

    async def upload_to_local(
        self,
        file_content: bytes,
        filename: str,
        storage_settings: dict,
        file_type: str = "common",
    ) -> str:
        """
        Upload a file to local storage.

        Args:
            file_content: File contents.
            filename: File name.
            storage_settings: Current storage configuration.
            file_type: File category, such as image or document.

        Returns:
            str: File URL.

        Raises:
            HTTPException: Raised when the upload fails.
        """
        try:
            # Resolve the local storage path.
            local_storage_full_url = storage_settings["local_full_url"]
            local_upload_dir = storage_settings["local_upload_dir"]
            fs_path, url_path = self.generate_local_path(storage_settings, file_type)

            # Full file path.
            file_path = os.path.join(fs_path, filename)

            # Write the file to disk.
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Build the returned file URL.
            if local_storage_full_url:
                relative_path = url_path[len("/static/") :].lstrip("/")
                file_url = f"{local_storage_full_url.rstrip('/')}/{relative_path}/{filename}"
            else:
                # Otherwise, return a relative path.
                file_url = f"{url_path}/{filename}"

            return file_url

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"上传到本地存储失败: {str(e)}"
            )

    async def upload_to_oss(self, file_content: bytes, oss_file_name: str, file_type: str = "common") -> str:
        """
        Upload a file to object storage or local storage.

        Args:
            file_content: File contents.
            oss_file_name: File name in object storage.
            file_type: File category, such as image or document.

        Returns:
            str: File URL.

        Raises:
            HTTPException: Raised when the upload fails.
        """
        storage_settings = await self.get_storage_settings()
        if not self.is_object_storage_enabled(storage_settings):
            return await self.upload_to_local(file_content, oss_file_name, storage_settings, file_type)

        bucket = self.build_oss_bucket(storage_settings)

        # Build the final OSS object path, including date-based directory segmentation.
        upload_dir = storage_settings.get("oss_upload_dir") or "uploads"
        oss_path = self.generate_oss_path(upload_dir, file_type)
        # Join the path with os.path.join, then normalize it to OSS path format.
        oss_file_path = os.path.join(oss_path, oss_file_name).replace("\\", "/")

        # Upload the file.
        try:
            # Upload the file and set the ACL to public-read so it can be accessed publicly.
            headers = {"x-oss-object-acl": "public-read"}
            bucket.put_object(oss_file_path, file_content, headers=headers)

            return self.build_oss_file_url(storage_settings, oss_file_path)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"上传到对象存储失败: {str(e)}",
            )

    async def upload_image(self, file: UploadFile) -> Dict:
        """
        Upload a single image to object storage or local storage.

        Args:
            file: Uploaded image file.

        Returns:
            Dict: Upload result payload.
        """
        # Validate the file.
        file_content = await self.check_image_file(file)

        # Generate the target file name.
        file_name = self.generate_oss_file_name(file.filename)

        # Upload the file according to the configured storage provider.
        file_url = await self.upload_to_oss(file_content, file_name, file_type="image")

        # Return the upload result.
        return {"url": file_url, "name": file.filename, "size": len(file_content)}

    async def upload_avatar(self, file: UploadFile) -> Dict:
        """
        Upload an avatar image and normalize it to WebP before storing it.

        Args:
            file: Uploaded avatar file.

        Returns:
            Dict: Upload result payload.
        """
        file_content = await self.check_image_file(file)
        webp_content = self.convert_avatar_to_webp(file_content)
        file_name = self.generate_oss_file_name(file.filename, extension_override=".webp")
        file_url = await self.upload_to_oss(webp_content, file_name, file_type="avatar")

        return {"url": file_url, "name": file_name, "size": len(webp_content)}

    async def upload_files(self, files: List[UploadFile]) -> List[Dict]:
        """
        Upload multiple files to object storage or local storage.

        Args:
            files: Uploaded files.

        Returns:
            List[Dict]: Upload result payload list.
        """
        if not files:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有提供要上传的文件")

        # Enforce the maximum number of uploaded files.
        max_files = 10
        if len(files) > max_files:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"一次最多上传{max_files}个文件")

        result = []

        for file in files:
            # Validate the file.
            file_content = await self.check_file(file)

            # Generate the target file name.
            file_name = self.generate_oss_file_name(file.filename)

            # Resolve the file type from its extension.
            file_extension = self.get_file_extension(file.filename).lower()
            file_type = "common"

            # Map the extension to a storage category.
            if file_extension in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                file_type = "image"
            elif file_extension in [".doc", ".docx", ".pdf", ".txt", ".xls", ".xlsx"]:
                file_type = "document"
            elif file_extension in [".mp4", ".avi", ".mov", ".wmv"]:
                file_type = "video"

            # Upload the file according to the configured storage provider.
            file_url = await self.upload_to_oss(file_content, file_name, file_type=file_type)

            result.append({"url": file_url, "name": file.filename, "size": len(file_content)})

        return result

    async def list_files(self, prefix: str = None, max_keys: int = 100) -> List[Dict]:
        """
        Return the file list from object storage.

        Args:
            prefix: Path prefix, for example `"image/"`.
            max_keys: Maximum number of items to return. Defaults to 100.

        Returns:
            List[Dict]: File metadata list.
        """
        storage_settings = await self.get_storage_settings()
        if not self.is_object_storage_enabled(storage_settings):
            return []

        try:
            bucket = self.build_oss_bucket(storage_settings)

            # Build the full prefix with os.path.join and normalize separators.
            upload_dir = storage_settings.get("oss_upload_dir") or "uploads"
            if prefix:
                full_prefix = os.path.join(upload_dir, prefix).replace("\\", "/")
            else:
                full_prefix = upload_dir

            # Enumerate files.
            result = []
            for obj in oss2.ObjectIterator(bucket, prefix=full_prefix, max_keys=max_keys):
                if not obj.key.endswith("/"):  # Exclude directory placeholders.
                    file_name = os.path.basename(obj.key)

                    result.append(
                        {
                            "name": file_name,
                            "url": self.build_oss_file_url(storage_settings, obj.key),
                            "key": obj.key,
                            "size": obj.size,
                            "last_modified": obj.last_modified.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )

            return result

        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取文件列表失败: {str(e)}")

    async def delete_local_file(self, file_path: str, storage_settings: dict) -> bool:
        """
        Delete a file from local storage.

        Args:
            file_path: Relative file path or full URL.
            storage_settings: Current storage configuration.

        Returns:
            bool: Whether deletion succeeded.
        """
        try:
            print(f"Attempting to delete local file: {file_path}")
            local_storage_full_url = storage_settings["local_full_url"].rstrip("/")

            if local_storage_full_url and file_path.startswith(local_storage_full_url):
                relative_path = file_path[len(local_storage_full_url) :].lstrip("/")
            elif file_path.startswith("/static/"):
                relative_path = file_path[len("/static/") :].lstrip("/")
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的本地文件路径")

            full_path = os.path.join(settings.storage_root_path, relative_path)

            print(f"Resolved full path: {full_path}")

            # Check whether the file exists.
            if os.path.isfile(full_path):
                os.remove(full_path)
                print(f"File deleted successfully: {full_path}")
                return True

            # If the file does not exist, log the condition without raising.
            print(f"File does not exist: {full_path}")
            return False

        except HTTPException:
            raise
        except Exception as e:
            print(f"Failed to delete local file: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除本地文件失败: {str(e)}")

    async def delete_file(self, file_key: str) -> bool:
        """
        Delete a file from OSS or local storage.

        Args:
            file_key: OSS object key or local storage path.

        Returns:
            bool: Whether deletion succeeded.
        """
        storage_settings = await self.get_storage_settings()
        if not self.is_object_storage_enabled(storage_settings) or self.is_local_file_key(file_key, storage_settings):
            return await self.delete_local_file(file_key, storage_settings)

        try:
            bucket = self.build_oss_bucket(storage_settings)

            # Delete the object.
            bucket.delete_object(file_key)
            return True

        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除文件失败: {str(e)}")

    async def set_public_acl(self, prefix: str = None) -> Dict:
        """
        Set public-read ACL on files under the given prefix.

        Args:
            prefix: Path prefix, for example `"image/"`.

        Returns:
            Dict: Operation result.
        """
        storage_settings = await self.get_storage_settings()
        if not self.is_object_storage_enabled(storage_settings):
            return {
                "success": False,
                "message": "当前未启用对象存储",
                "count": 0,
                "error_count": 0,
            }

        try:
            bucket = self.build_oss_bucket(storage_settings)

            # Build the full prefix.
            upload_dir = storage_settings.get("oss_upload_dir") or "uploads"
            if prefix:
                full_prefix = os.path.join(upload_dir, prefix).replace("\\", "/")
            else:
                full_prefix = upload_dir

            # Track success and failure counts.
            count = 0
            error_count = 0

            # Enumerate files and set ACL values.
            for obj in oss2.ObjectIterator(bucket, prefix=full_prefix):
                if not obj.key.endswith("/"):  # Exclude directory placeholders.
                    try:
                        # Set the file ACL to public-read.
                        bucket.put_object_acl(obj.key, oss2.OBJECT_ACL_PUBLIC_READ)
                        count += 1
                    except Exception:
                        error_count += 1

            return {
                "success": True,
                "message": f"成功设置 {count} 个文件的ACL为公共读，失败 {error_count} 个",
                "count": count,
                "error_count": error_count,
            }

        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"设置文件ACL失败: {str(e)}")


upload_controller = UploadController()
