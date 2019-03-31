from redbot.core.commands import BadArgument


def convert_time(value):
    if not value:
        return None
    value[1] = value[1].lower()
    passing = int(value[0])
    if value[1].startswith("second"):
        pass
    elif value[1].startswith("minute"):
        passing *= 60
    elif value[1].startswith("hour"):
        passing *= 3600
    elif value[1].startswith("day"):
        passing *= 86400
    else:
        raise BadArgument()
    return passing
