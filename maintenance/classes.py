import time


class ScheduledMaintenance:
    def __init__(self, start=0, end=0, after=True, whitelist=None):
        if not whitelist:
            whitelist = []
        self.start = start + time.time()
        if end:
            if after:
                self.end = end + self.start
            else:
                self.end = time.time() + end
        else:
            self.end = 0
        self.whitelist = whitelist

    def to_dict(self):
        return self.__dict__

    def to_conf(self):
        active = (self.start == 0) or (time.time() >= self.start)
        return [active, self.end, self.whitelist]

    def to_scheduled(self):
        return [self.start, self.end, self.whitelist]
