import uuid
import urllib.parse
import base62
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from utils.common import pretty_url
from opencivicdata.core.models import Person
from opencivicdata.legislative.models import Bill
from .utils import utcnow


DAILY = "d"
WEEKLY = "w"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    organization_name = models.CharField(max_length=100, blank=True)
    about = models.TextField(blank=True)

    # feature flags
    feature_subscriptions = models.BooleanField(default=False)

    subscription_emails_html = models.BooleanField(default=True)
    subscription_frequency = models.CharField(
        max_length=1, choices=((DAILY, "daily"), (WEEKLY, "weekly")), default=WEEKLY
    )
    subscription_last_checked = models.DateTimeField(default=utcnow)

    def __str__(self):
        return f"Profile for {self.user}"


class Subscription(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscriptions"
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    query = models.CharField(max_length=300, blank=True)
    state = models.CharField(max_length=2, blank=True)
    chamber = models.CharField(max_length=15, blank=True)
    session = models.CharField(max_length=100, blank=True)
    classification = models.CharField(max_length=50, blank=True)
    subjects = ArrayField(models.CharField(max_length=100), blank=True)
    status = ArrayField(models.CharField(max_length=50), blank=True)
    sponsor = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        null=True,
        blank=True,
    )
    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        null=True,
        blank=True,
    )

    @property
    def subscription_type(self):
        if self.bill_id:
            return "bill"
        elif self.query:
            return "query"
        elif self.sponsor_id:
            return "sponsor"
        raise ValueError(f"invalid subscription: {self.__dict__}")

    @property
    def pretty(self):
        if self.subscription_type == "bill":
            return f"Updates on {self.bill}"
        elif self.subscription_type == "sponsor":
            return f"Bills sponsored by {self.sponsor}"
        elif self.subscription_type == "query":
            state = self.state.upper() if self.state else "all states"
            pretty_str = f"Bills matching '{self.query}' from {state}"
            if self.chamber in ("upper", "lower"):
                pretty_str += f", {self.chamber} chamber"
            if self.session:
                pretty_str += f", {self.session}"
            if self.classification:
                pretty_str += f", classified as {self.classification}"
            if self.subjects:
                pretty_str += f", including subjects '{', '.join(self.subjects)}'"
            if self.status:
                pretty_str += f", status includes '{', '.join(self.status)}'"
            if self.sponsor:
                pretty_str += f", sponsored by {self.sponsor}"
            return pretty_str

    @property
    def site_url(self):
        if self.subscription_type == "query":
            queryobj = {
                "query": self.query,
                "subjects": self.subjects or [],
                "status": self.status or [],
            }
            if self.classification:
                queryobj["classification"] = self.classification
            if self.session:
                queryobj["session"] = self.session
            if self.chamber:
                queryobj["chamber"] = self.chamber
            if self.sponsor_id:
                queryobj["sponsor_id"] = self.sponsor_id
            querystr = urllib.parse.urlencode(queryobj, doseq=True)
            if self.state:
                return f"/{self.state}/bills/?{querystr}"
            else:
                return f"/search/?{querystr}"
        elif self.subscription_type == "bill":
            return pretty_url(self.bill)
        elif self.subscription_type == "sponsor":
            return pretty_url(self.sponsor)

    def __str__(self):
        return f"{self.user}: {self.pretty}"


def _str_uuid():
    return base62.encode(uuid.uuid4().int)


class Notification(models.Model):
    id = models.CharField(
        primary_key=True, default=_str_uuid, max_length=22, editable=False
    )
    # store email instead of link to user, since emails can change and users can be deleted
    email = models.EmailField(editable=False)
    sent = models.DateTimeField(editable=False)
    num_query_updates = models.PositiveIntegerField(editable=False)
    num_bill_updates = models.PositiveIntegerField(editable=False)
