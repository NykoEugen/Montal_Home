from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class _BaseR2Storage(S3Boto3Storage):
    """
    Extend S3 storage with Cloudflare R2 specific tweaks (pool size, SSL, etc.).
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


class R2MediaStorage(_BaseR2Storage):
    """
    Кастомний storage для Cloudflare R2 для користувацьких завантажень.
    """


class R2StaticStorage(_BaseR2Storage):
    """
    Cloudflare R2 storage для статичних файлів, які потім віддає Bunny CDN.
    """

    def __init__(self, *args, **kwargs):
        bucket_name = getattr(
            settings,
            "STATICFILES_BUCKET_NAME",
            getattr(settings, "AWS_STORAGE_BUCKET_NAME", None),
        )
        custom_domain = getattr(settings, "STATIC_CDN_DOMAIN", None)
        location = getattr(settings, "STATICFILES_LOCATION", "static")

        kwargs.setdefault("bucket_name", bucket_name)
        kwargs.setdefault("custom_domain", custom_domain)
        kwargs.setdefault("location", location)
        kwargs.setdefault("querystring_auth", False)
        kwargs.setdefault("default_acl", "public-read")

        super().__init__(*args, **kwargs)
