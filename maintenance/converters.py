# Large pieces of the argument parser is taken from Sinbad's cogs.  I based mine off of https://github.com/mikeshardmind/SinbadCogs/blob/d59fd7bc69833dc24f9e74ec59e635ffe593d43f/scheduler/converters.py#L23

import argparse
import time

from redbot.core.commands import BadArgument, Converter

from .classes import ScheduledMaintenance
from .utils import convert_time


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()


class Margs(Converter):
    async def convert(self, ctx, argument):
        argument = argument.replace("—", "--")
        parser = NoExitParser(description="Maintenance Scheduler", add_help=False)
        parser.add_argument("--start-in", nargs="*", dest="start", default=[])
        parser.add_argument("--whitelist", nargs="*", dest="whitelist", default=[])
        _end = parser.add_mutually_exclusive_group()
        _end.add_argument("--end-after", nargs="*", dest="end", default=[])
        _end.add_argument("--end-in", nargs="*", dest="endin", default=[])
        _end.add_argument("--end-after-restart", dest="end_after_restart", action="store_true")
        try:
            vals = vars(parser.parse_args(argument.split(" ")))
        except Exception as exc:
            raise BadArgument() from exc
        start_seconds = convert_time(vals.get("start", None))
        end_seconds = convert_time(vals.get("end", None))
        whitelist = vals.get("whitelist", [])
        whitelist = list(map(int, whitelist))
        after = True
        if end_seconds == None:
            end_seconds = convert_time(vals.get("endin", None))
            after = False
        if vals.get("end_after_restart", False):
            end_seconds = True
        if start_seconds:
            if end_seconds:
                scheduled = ScheduledMaintenance(
                    start=start_seconds, end=end_seconds, after=after, whitelist=whitelist
                )
            else:
                scheduled = ScheduledMaintenance(start=start_seconds, whitelist=whitelist)
        else:
            if end_seconds:
                scheduled = ScheduledMaintenance(end=end_seconds, after=after, whitelist=whitelist)
            else:
                scheduled = ScheduledMaintenance(whitelist=whitelist)
        return scheduled
