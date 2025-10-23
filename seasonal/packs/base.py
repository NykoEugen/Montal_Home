from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, Optional

from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils import timezone

StaticBundleMap = Dict[str, Iterable[str]]


@dataclass
class Pack(ABC):
    slug: str
    name: str
    version: str
    priority: int = 0
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    campaign: Optional["SeasonalCampaign"] = field(default=None, repr=False)
    _request_bound: bool = field(default=False, init=False, repr=False)

    def bind(self, campaign: "SeasonalCampaign") -> "Pack":
        bound = copy.deepcopy(self)
        bound.campaign = campaign
        bound._request_bound = False
        return bound

    def is_enabled(self) -> bool:
        return True

    def is_active(self, now: Optional[datetime] = None) -> bool:
        if not self.is_enabled():
            return False

        now = now or timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    def render(
        self,
        region: str,
        *,
        request=None,
        extra_context: Optional[Dict[str, object]] = None,
    ) -> str:
        template_name = self.get_partial_template(region)
        if not template_name:
            return ""

        try:
            template = get_template(template_name)
        except TemplateDoesNotExist:
            return ""

        context: Dict[str, object] = {}
        if request is not None:
            context["request"] = request
        if self.campaign is not None:
            context["campaign"] = self.campaign
        context.update(self.get_context(request))
        if extra_context:
            context.update(extra_context)
        return template.render(context)

    def ensure_request(self, request) -> None:
        if not self._request_bound:
            self.on_request(request)
            self._request_bound = True

    @abstractmethod
    def get_context(self, request) -> Dict[str, object]:
        ...

    @abstractmethod
    def get_static_bundles(self) -> StaticBundleMap:
        ...

    @abstractmethod
    def get_partial_template(self, region: str) -> Optional[str]:
        ...

    def on_request(self, request) -> None:
        return None


from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from seasonal.models import SeasonalCampaign
