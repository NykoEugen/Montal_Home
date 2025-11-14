from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class R2MediaStorage(S3Boto3Storage):
    """
    Кастомний storage для Cloudflare R2 з можливістю передати boto3 Config.
    """

    def __init__(self, *args, **kwargs):
        self._extra_config = getattr(settings, "AWS_S3_CLIENT_CONFIG", None)
        super().__init__(*args, **kwargs)

    def _get_or_create_bucket(self, *args, **kwargs):
        if self._extra_config:
            self.connection.meta.client.meta.config.max_pool_connections = (
                self._extra_config.max_pool_connections
            )
        return super()._get_or_create_bucket(*args, **kwargs)
