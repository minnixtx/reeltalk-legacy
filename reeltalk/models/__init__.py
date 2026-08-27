"""bring all the models into the app namespace"""

import inspect
import sys

from .film import Film, MergedFilm
from .link import Link, LinkDomain

from .shelf import Shelf, ShelfFilm
from .list import List, ListItem

from .status import Status, GeneratedNote, Comment, Quotation
from .status import Review, ReviewRating
from .status import Boost
from .attachment import Image
from .favorite import Favorite

from .user import User, KeyPair
from .relationship import UserFollows, UserFollowRequest, UserBlocks
from .report import Report, ReportAction
from .federated_server import FederatedServer
from .user_upload import UserUpload, UserUploadVersion

from .group import Group, GroupMember, GroupMemberInvitation

from .housekeeping import CleanUpUserExportFilesJob, start_export_deletions

from .reeltalk_export_job import ReeltalkExportJob

from .move import MoveUser

from .site import SiteSettings, Theme, SiteInvite
from .site import PasswordReset, InviteRequest
from .announcement import Announcement
from .antispam import EmailBlocklist, IPBlocklist, AutoMod, automod_task

from .notification import Notification, NotificationType

from .hashtag import Hashtag

from .session import UserSession, create_user_session

cls_members = inspect.getmembers(sys.modules[__name__], inspect.isclass)
activity_models = {
    c[1].activity_serializer.__name__: c[1]
    for c in cls_members
    if hasattr(c[1], "activity_serializer")
}

status_models = [
    c.__name__ for (_, c) in activity_models.items() if issubclass(c, Status)
]
