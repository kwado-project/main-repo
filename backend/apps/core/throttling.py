import re

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


class FlexibleRateMixin:
    """Accepts rates like '5/10m', '20/min', '100/2h' (DRF only supports '5/m')."""

    def parse_rate(self, rate):
        if rate is None:
            return None, None
        num, period = rate.split("/")
        m = re.fullmatch(r"(\d*)\s*([smhd])\w*", period.strip())
        mult = int(m.group(1) or 1)
        return int(num), mult * UNITS[m.group(2)]


class FlexAnonThrottle(FlexibleRateMixin, AnonRateThrottle):
    pass


class FlexUserThrottle(FlexibleRateMixin, UserRateThrottle):
    pass
