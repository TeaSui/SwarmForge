from __future__ import annotations

import logging
import os

import boto3
from botocore.exceptions import ProfileNotFound

from config import settings

logger = logging.getLogger(__name__)


def get_aws_client(service_name: str, **kwargs) -> object:
    """Create a boto3 client with optional LocalStack endpoint override."""
    session = get_boto3_session()
    endpoint_url = settings.AWS_ENDPOINT_URL
    if endpoint_url:
        kwargs.setdefault("endpoint_url", endpoint_url)
    return session.client(service_name, **kwargs)


def get_boto3_session() -> boto3.Session:
    # Empty or invalid AWS_PROFILE in env can break botocore profile resolution.
    env_profile = os.environ.get("AWS_PROFILE", None)
    if env_profile == "":
        os.environ.pop("AWS_PROFILE", None)

    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        try:
            return boto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
        except ProfileNotFound:
            # Explicit credentials should not depend on local profile files.
            os.environ.pop("AWS_PROFILE", None)
            return boto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
    profile = settings.AWS_PROFILE.strip()
    if profile:
        try:
            return boto3.Session(
                profile_name=profile,
                region_name=settings.AWS_REGION,
            )
        except ProfileNotFound:
            # ECS/Lambda runtime often has no local profile file; fall back to IAM role.
            logger.warning(
                "AWS profile '%s' not found. Falling back to default credential chain.",
                profile,
            )
            os.environ.pop("AWS_PROFILE", None)
    try:
        return boto3.Session(region_name=settings.AWS_REGION)
    except ProfileNotFound:
        # Last-resort fallback for environments that inject invalid AWS_PROFILE.
        os.environ.pop("AWS_PROFILE", None)
        return boto3.Session(region_name=settings.AWS_REGION)
