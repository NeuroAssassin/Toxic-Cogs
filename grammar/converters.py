import argparse

from redbot.core.commands import BadArgument, Converter


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()


class Gargs(Converter):
    async def convert(self, ctx, argument):
        argument = argument.replace("—", "--")
        parser = NoExitParser(description="Grammar argument parser", add_help=False)

        parser.add_argument("--meaning-like", "--ml", nargs="*", dest="ml", default=[])
        parser.add_argument("--spelled-like", "--sp", nargs="?", dest="sp", default=[])
        parser.add_argument("--sounds-like", "--sl", nargs="?", dest="sl", default=[])
        parser.add_argument("--rhymes-with", "--rw", nargs="?", dest="rw", default=[])
        parser.add_argument("--adjectives-for", "--af", nargs="?", dest="af", default=[])
        parser.add_argument("--nouns-for", "--nf", nargs="?", dest="nf", default=[])
        parser.add_argument("--comes-before", "--cb", nargs="*", dest="ca", default=[])
        parser.add_argument("--comes-after", "--ca", nargs="*", dest="cb", default=[])
        parser.add_argument("--topics", "--t", nargs="*", dest="t", default=[])
        parser.add_argument("--synonyms-for", "--sf", nargs="*", dest="sf", default=[])
        parser.add_argument("--antonyms-for", "--anf", nargs="*", dest="anf", default=[])
        parser.add_argument("--kind-of", "--ko", nargs="?", dest="ko", default=[])
        parser.add_argument("--more-specific-than", "--mst", nargs="?", dest="mso", default=[])
        parser.add_argument("--homophones", "--h", nargs="?", dest="h", default=[])

        try:
            vals = vars(parser.parse_args(argument.split(" ")))
        except Exception as error:
            raise BadArgument() from error

        data = {}
        if vals["ml"]:
            data["ml"] = " ".join(vals["ml"])
        if vals["sp"]:
            data["sp"] = vals["sp"]
        if vals["sl"]:
            data["sl"] = vals["sl"]
        if vals["rw"]:
            data["rel_rhy"] = vals["rw"]
        if vals["af"]:
            data["rel_jjb"] = vals["af"]
        if vals["nf"]:
            data["rel_jja"] = vals["nf"]
        if vals["ca"]:
            data["lc"] = " ".join(vals["ca"])
        if vals["cb"]:
            data["rc"] = " ".join(vals["cb"])
        if vals["t"]:
            if len(vals["t"]) > 5:
                raise BadArgument("Topic can only be five words")
            data["topics"] = " ".join(vals["t"])
        if vals["sf"]:
            data["rel_syn"] = " ".join(vals["sf"])
        if vals["anf"]:
            data["rel_ant"] = " ".join(vals["anf"])
        if vals["ko"]:
            data["rel_spc"] = vals["ko"]
        if vals["mso"]:
            data["rel_gen"] = vals["mso"]
        if vals["h"]:
            data["rel_hom"] = vals["h"]

        data["max"] = 10

        return data
