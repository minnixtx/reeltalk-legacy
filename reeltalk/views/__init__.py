"""make sure all our nice views are available"""

# site admin
from .admin.announcements import Announcements, Announcement
from .admin.announcements import EditAnnouncement, delete_announcement
from .admin.automod import AutoMod, automod_delete, run_automod
from .admin.automod import schedule_automod_task, unschedule_automod_task
from .admin.celery_status import CeleryStatus, celery_ping
from .admin.redis import RedisStatus
from .admin.schedule import ScheduledTasks
from .admin.dashboard import Dashboard
from .admin.federation import Federation, FederatedServer
from .admin.federation import AddFederatedServer, ImportServerBlocklist
from .admin.federation import block_server, unblock_server, refresh_server
from .admin.federation_settings import FederationSettings
from .admin.files_maintenance import (
    FilesMaintenance,
    run_export_deletions,
    schedule_export_delete_task,
    unschedule_file_maintenance_task,
    set_export_expiry_age,
    cancel_export_delete_job,
)
from .admin.email_blocklist import EmailBlocklist
from .admin.email_config import EmailConfig
from .admin.ip_blocklist import IPBlocklist
from .admin.invite import ManageInvites, Invite, InviteRequest
from .admin.invite import ManageInviteRequests, ignore_invite_request
from .admin.link_domains import LinkDomain, update_domain_status
from .admin.reports import (
    ReportAdmin,
    ReportsAdmin,
    resolve_report,
    suspend_user,
    unsuspend_user,
    moderator_delete_user,
)
from .admin.site import Site, Registration, RegistrationLimited
from .admin.themes import Themes, delete_theme, test_theme
from .admin.user_admin import UserAdmin, UserAdminList, ActivateUserAdmin
from .admin.user_admin import ForcePasswordResetAdmin

# user preferences
from .preferences.change_password import ChangePassword
from .preferences.edit_user import EditUser
from .preferences.export import Export, ExportUser, ExportArchive
from .preferences.move_user import MoveUser, AliasUser, remove_alias, unmove
from .preferences.delete_user import DeleteUser, DeactivateUser, ReactivateUser
from .preferences.block import Block, unblock
from .preferences.films import BlockedFilms, unblock_film
from .preferences.security import (
    UserSecurity,
    logout_session,
    Edit2FA,
    Confirm2FA,
    Disable2FA,
    GenerateBackupCodes,
    LoginWith2FA,
    Prompt2FA,
)

# films
from .films.films import (
    Film,
    upload_poster,
    add_description,
)

from .films.edit_film import (
    EditFilm,
    ConfirmEditFilm,
    CreateFilm,
)

# landing
from .landing.about import about, privacy, impressum
from .landing.landing import Home, Landing
from .landing.login import Login, Logout
from .landing.register import Register
from .landing.register import ConfirmEmail, ConfirmEmailCode, ResendConfirmEmail
from .landing.password import PasswordResetRequest, PasswordReset, ForcePasswordReset

# shelves
from .shelf.shelf import Shelf
from .shelf.shelf_actions import shelve, unshelve

# lists
from .list.curate import Curate
from .list.embed import unsafe_embed_list
from .list.list_item import ListItem
from .list.lists import Lists, SavedLists, UserLists
from .list.list import (
    List,
    save_list,
    unsave_list,
    delete_list,
    add_film,
    remove_film,
    set_film_position,
)

# misc views
from .directory import Directory
from .discover import Discover
from .feed import DirectMessage, Feed, Replies, Status
from .follow import (
    follow,
    unfollow,
    remove_follow,
    ostatus_follow_request,
    ostatus_follow_success,
    remote_follow,
    remote_follow_page,
)
from .follow import accept_follow_request, delete_follow_request
from .get_started import GetStartedFilms, GetStartedProfile, GetStartedUsers
from .group import (
    Group,
    UserGroups,
    FindUsers,
    delete_group,
    invite_member,
    remove_member,
    accept_membership,
    reject_membership,
)
from .hashtag import Hashtag
from .inbox import Inbox
from .interaction import Favorite, Unfavorite, Boost, Unboost
from .notifications import Notifications
from .outbox import Outbox
from .reading import ReadingStatus
from .report import Report
from .rss_feed import (
    RssFeed,
    RssReviewsOnlyFeed,
    RssQuotesOnlyFeed,
    RssCommentsOnlyFeed,
)
from .search import (
    Search,
    FilmWatchlistAdd,
    film_search_clickthrough,
    film_search_suggest,
)
from .setup import InstanceConfig, CreateAdmin
from .status import CreateStatus, EditStatus, DeleteStatus
from .updates import get_notification_count, get_unread_status_string
from .user import (
    User,
    UserReviewsComments,
    hide_suggestions,
    user_redirect,
    toggle_guided_tour,
)
from .user_upload import CreateUserUpload
from .relationships import Relationships
from .wellknown import *
from .annual_summary import (
    AnnualSummary,
    personal_annual_summary,
    summary_add_key,
    summary_revoke_key,
)
from .server_error import server_error
from .permission_denied import permission_denied
