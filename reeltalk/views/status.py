"""what are we here for if not for posting"""

import re
import logging

from django.contrib.auth.decorators import login_required
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

import mistune
from reeltalk import forms, models
from reeltalk.models.report import DELETE_ITEM
from reeltalk.utils import regex, sanitizer
from reeltalk.views.helpers import get_mergeable_object_or_404
from .helpers import handle_remote_webfinger, is_api_request
from .helpers import redirect_to_referer

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class EditStatus(View):
    """the view for *posting*"""

    def get(self, request, status_id):
        """load the edit panel"""
        status = get_object_or_404(
            models.Status.objects.select_subclasses(), id=status_id
        )

        if status.reply_parent:
            status_type = "reply"
        elif isinstance(status, models.ReviewRating):
            # a rating-only entry is still the user's review of the film
            status_type = "review"
        else:
            status_type = status.status_type.lower()
        data = {
            "type": status_type,
            "film": getattr(status, "film", None),
            "draft": status,
        }
        return TemplateResponse(request, "compose.html", data)


@method_decorator(login_required, name="dispatch")
class CreateStatus(View):
    """the view for *posting*"""

    def get(self, request, status_type):
        """compose view (...not used?)"""
        film = get_mergeable_object_or_404(models.Film, id=request.GET.get("film"))
        data = {"film": film}
        return TemplateResponse(request, "compose.html", data)

    @transaction.atomic
    def post(self, request, status_type, existing_status_id=None):
        """create status of whatever type"""
        created = not existing_status_id
        existing_status = None
        if existing_status_id:
            existing_status = get_object_or_404(
                models.Status.objects.select_subclasses(), id=existing_status_id
            )
            existing_status.edited_date = timezone.now()

        status_type = status_type[0].upper() + status_type[1:]

        try:
            form = getattr(forms, f"{status_type}Form")(
                request.POST, instance=existing_status
            )
        except AttributeError as err:
            logger.exception(err)
            return HttpResponseBadRequest()

        if not form.is_valid():
            if is_api_request(request):
                logger.exception(form.errors)
                return HttpResponseBadRequest()
            return redirect_to_referer(request)

        # one review per film: an existing review can only be edited
        if status_type == "Review" and not existing_status:
            film = form.cleaned_data.get("film")
            if (
                film
                and models.Review.objects.filter(
                    film=film, user=request.user, deleted=False
                ).exists()
            ):
                if is_api_request(request):
                    return HttpResponseBadRequest()
                return redirect_to_referer(request)

        status = form.save(request, commit=False)
        # save the plain, unformatted version of the status for future editing
        status.raw_content = status.content

        status.sensitive = status.content_warning not in [None, ""]
        # the status has to be saved now before we can add many to many fields
        # like mentions
        status.save(broadcast=False)

        # inspect the text for user tags
        content = status.content
        mentions = find_mentions(request.user, content)
        for _, mention_user in mentions.items():
            # add them to status mentions fk
            status.mention_users.add(mention_user)
        content = format_mentions(content, mentions)

        # add reply parent to mentions
        if status.reply_parent:
            status.mention_users.add(status.reply_parent.user)

        uploaded_images = find_images(content, request.user)
        for _, upload in uploaded_images.items():
            status.user_image_uploads.add(upload)
        content = format_images(content, uploaded_images)

        # inspect the text for hashtags
        hashtags = find_or_create_hashtags(content)
        for _, mention_hashtag in hashtags.items():
            # add them to status mentions fk
            status.mention_hashtags.add(mention_hashtag)
        content = format_hashtags(content, hashtags)

        # deduplicate mentions
        status.mention_users.set(set(status.mention_users.all()))

        # don't apply formatting to generated notes
        if not isinstance(status, models.GeneratedNote) and content:
            status.content = to_markdown(content)

        status.save(created=created)

        if is_api_request(request):
            return HttpResponse()
        return redirect_to_referer(request)


def find_images(content, user):
    """Detect special image tags for responsive images"""
    if not content:
        return {}
    images = {}
    for matchobj in re.finditer(r"!image\(([^)]+)\)", content):
        upload = user.user_uploads.get(original_file=matchobj.group(1))
        images[matchobj.group(0)] = upload
    return images


def format_images(content, images):
    for str, upload in images.items():
        content = content.replace(str, responsive_image_tag(upload))
    return content


def responsive_image_tag(upload):
    srcs = [
        [version.file.url, version.max_dimension] for version in upload.versions.all()
    ]
    srcset = ", ".join([f"{src[0]} {src[1]}w" for src in srcs])
    return f'<img srcset="{srcset}" sizes="(width <= 600px) 100vw, 60vw" src="{srcs[-1][0]}" />'


def format_mentions(content, mentions):
    """Detect @mentions and make them links"""
    for mention_text, mention_user in mentions.items():
        # turn the mention into a link
        content = re.sub(
            rf"(?<!/)\B{mention_text}\b(?!@)",
            rf'<a href="{mention_user.remote_id}">{mention_text}</a>',
            content,
        )
    return content


def format_hashtags(content, hashtags):
    """Detect #hashtags and make them links"""
    for mention_text, mention_hashtag in hashtags.items():
        # turn the mention into a link
        content = re.sub(
            rf"(?<!/)\B{mention_text}\b(?!@)",
            rf'<a href="{mention_hashtag.remote_id}" data-mention="hashtag">'
            + rf"{mention_text}</a>",
            content,
        )
    return content


@method_decorator(login_required, name="dispatch")
class DeleteStatus(View):
    """tombstone that bad boy"""

    def post(self, request, status_id, report_id=None):
        """delete and tombstone a status"""
        status = get_object_or_404(models.Status, id=status_id)

        # don't let people delete other people's statuses
        status.raise_not_deletable(request.user)

        # perform deletion
        status.delete()
        # record deletion if it's related to a report
        if report_id:
            models.Report.record_action(report_id, DELETE_ITEM, request.user)

        return redirect_to_referer(request, "/")


def find_mentions(user, content):
    """detect @mentions in raw status content"""
    if not content:
        return {}
    # The regex has nested match groups, so the 0th entry has the full (outer) match
    # And because the strict username starts with @, the username is 1st char onward
    usernames = [m[0][1:] for m in re.findall(regex.STRICT_USERNAME, content)]

    known_users = (
        models.User.viewer_aware_objects(user)
        .filter(Q(username__in=usernames) | Q(localname__in=usernames))
        .distinct()
    )
    # Prepare a lookup based on both username and localname
    username_dict = {
        **{f"@{u.username}": u for u in known_users},
        **{f"@{u.localname}": u for u in known_users.filter(local=True)},
    }

    # Users not captured here could be blocked or not yet loaded on the server
    not_found = set(usernames) - set(username_dict.keys())
    for username in not_found:
        mention_user = handle_remote_webfinger(username, unknown_only=True)
        if not mention_user:
            # this user is blocked or can't be found
            continue
        username_dict[f"@{mention_user.username}"] = mention_user
        username_dict[f"@{mention_user.localname}"] = mention_user
    return username_dict


def find_or_create_hashtags(content):
    """detect #hashtags in raw status content

    it stores hashtags case-sensitive, but ensures that an existing
    hashtag with different case are found and re-used. for example,
    an existing #ReelTalk hashtag will be found and used even if the
    status content is using #reeltalk.
    """
    if not content:
        return {}

    found_hashtags = {t.lower(): t for t in re.findall(regex.HASHTAG, content)}
    if len(found_hashtags) == 0:
        return {}

    known_hashtags = {
        t.name.lower(): t
        for t in models.Hashtag.objects.filter(
            Q(name__in=found_hashtags.keys())
        ).distinct()
    }

    not_found = found_hashtags.keys() - known_hashtags.keys()
    for lower_name in not_found:
        tag_name = found_hashtags[lower_name]
        mention_hashtag = models.Hashtag(name=tag_name)
        mention_hashtag.save()
        known_hashtags[lower_name] = mention_hashtag

    return {found_hashtags[k]: v for k, v in known_hashtags.items()}


def format_links(content):
    """detect and format links"""
    validator = URLValidator(["http", "https"])
    schema_re = re.compile(r"\bhttps?://")
    split_content = re.split(r"(\s+)", content)

    for i, potential_link in enumerate(split_content):
        if not schema_re.search(potential_link):
            continue

        # Strip surrounding brackets and trailing punctuation.
        prefix, potential_link, suffix = _unwrap(potential_link)
        try:
            # raises an error on anything that's not a valid link
            validator(potential_link)

            # use everything but the scheme in the presentation of the link
            link = schema_re.sub("", potential_link)
            split_content[i] = f'{prefix}<a href="{potential_link}">{link}</a>{suffix}'
        except (ValidationError, UnicodeError):
            pass

    return "".join(split_content)


def _unwrap(text):
    """split surrounding brackets and trailing punctuation from a string of text"""
    punct = re.compile(r'([.,;:!?"’”»]+)$')
    prefix = suffix = ""

    if punct.search(text):
        # Move punctuation to suffix segment.
        text, suffix, _ = punct.split(text)

    for wrapper in ("()", "[]", "{}"):
        if text[0] == wrapper[0] and text[-1] == wrapper[-1]:
            # Split out wrapping chars.
            suffix = text[-1] + suffix
            prefix, text = text[:1], text[1:-1]
            break  # Nested wrappers not supported atm.

    if punct.search(text):
        # Move inner punctuation to suffix segment.
        text, inner_punct, _ = punct.split(text)
        suffix = inner_punct + suffix

    return prefix, text, suffix


def to_markdown(content):
    """catch links and convert to markdown"""
    content = format_links(content)
    content = mistune.html(content).rstrip()
    # sanitize resulting html
    return sanitizer.clean(content)
