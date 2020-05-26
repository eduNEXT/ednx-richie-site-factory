"""Customizing Django storage backends to enable blue/green deployments."""
import re
from collections import OrderedDict

from django.conf import settings
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage

from storages.backends.s3boto3 import S3Boto3Storage

STATIC_POSTPROCESS_IGNORE_REGEX = re.compile(r"^richie\/js\/[0-9]*\..*\.index\.js$")


class CDNManifestStaticFilesStorage(ManifestStaticFilesStorage):
    """
    Manifest static files storage backend that can be placed behing a CDN
    and ignores files that are already versioned by webpack.
    """

    def post_process(self, paths, dry_run=False, **options):
        """
        Remove paths from file to post process.
        Some js static files generated by webpack already have a unique name per build
        and may be referenced from within the js applications. We therefore don't want
        to hash their name and include them in the manifest file.
        We use a regex configurable via settings to decide which files to ignore.
        Parameters
        ----------
        paths : OrderedDict
            List of files to post process
        dry_run: boolean
            run process but nothing is apply if True
        options: kwargs
            See HashedFilesMixin.post_process
        """
        filtered_paths = OrderedDict()
        for path in paths:
            if not STATIC_POSTPROCESS_IGNORE_REGEX.match(path):
                filtered_paths[path] = paths[path]

        yield from super().post_process(filtered_paths, dry_run=dry_run, **options)

    def url(self, name, force=False):
        """
        Prepend static files path by the CDN base url when configured in settings.
        """
        url = super().url(name, force=force)

        cdn_domain = getattr(settings, "CDN_DOMAIN", None)
        if cdn_domain:
            url = f"//{cdn_domain:s}{url:s}"

        return url


class MediaStorage(S3Boto3Storage):
    """A S3Boto3Storage backend to serve media files via CloudFront."""

    bucket_name = getattr(settings, "AWS_MEDIA_BUCKET_NAME", None)
    custom_domain = getattr(settings, "CDN_DOMAIN", None)
    file_overwrite = False
    location = settings.MEDIA_URL
