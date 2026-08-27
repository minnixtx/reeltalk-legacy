"""utilities for fetching remote data (nodeinfo, webfinger, covers)"""

import ipaddress
import logging
from typing import Any, Optional, Union
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError
from requests import HTTPError
from requests.exceptions import RequestException

from reeltalk import models, settings

logger = logging.getLogger(__name__)


class RemoteDataError(HTTPError):
    """when remote data can't be fetched or is invalid"""


def raise_not_valid_url(url: str) -> None:
    """do some basic reality checks on the url"""
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        raise RemoteDataError("Invalid scheme: ", url)

    if not parsed.hostname:
        raise RemoteDataError("Hostname missing: ", url)

    try:
        ipaddress.ip_address(parsed.hostname)
        raise RemoteDataError("Provided url is an IP address: ", url)
    except ValueError:
        # it's not an IP address, which is good
        pass

    if models.FederatedServer.is_blocked(url):
        raise RemoteDataError(f"Attempting to load data from blocked url: {url}")


def get_data(
    url: str,
    params: Optional[dict[str, str]] = None,
    timeout: int = settings.QUERY_TIMEOUT,
    is_activitypub: bool = True,
) -> dict[str, Any]:
    """wrapper for requests.get that returns parsed json"""
    # make sure this isn't a forbidden federated request
    if is_activitypub:
        models.SiteSettings.raise_federation_disabled()

    # check if the url is blocked
    raise_not_valid_url(url)

    try:
        resp = requests.get(
            url,
            params=params,
            headers={
                "Accept": (
                    'application/json, application/activity+json, application/ld+json; profile="https://www.w3.org/ns/activitystreams"; charset=utf-8'
                ),
                "User-Agent": settings.USER_AGENT,
            },
            timeout=timeout,
        )
    except RequestException as err:
        logger.info(err)
        raise RemoteDataError(err)

    if not resp.ok:
        if resp.status_code == 401:
            # this is probably an AUTHORIZED_FETCH issue
            resp.raise_for_status()
        else:
            raise RemoteDataError()
    try:
        data = resp.json()
    except ValueError as err:
        logger.info(err)
        raise RemoteDataError(err)

    if not isinstance(data, dict):
        raise RemoteDataError("Unexpected data format")

    return data


def get_image(
    url: str, timeout: int = 10
) -> Union[tuple[ContentFile, str], tuple[None, None]]:
    """wrapper for requesting an image"""
    raise_not_valid_url(url)
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": settings.USER_AGENT,
            },
            timeout=timeout,
        )
    except RequestException as err:
        logger.info(err)
        return None, None

    if not resp.ok:
        return None, None

    image_content = ContentFile(resp.content)
    try:
        with Image.open(image_content) as im:
            extension = str(im.format).lower()
            return image_content, extension
    except UnidentifiedImageError:
        logger.info("File requested was not an image: %s", url)
        return None, None
