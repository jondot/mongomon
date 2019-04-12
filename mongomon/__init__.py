from attr import attrs, attrib, asdict
import colored
import re
from toolz.curried import pipe, map, filter, groupby, first, identity, take
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter
from pprint import pformat
import traceback
from six import print_


from pymongo import monitoring


def pretty(t):
    return highlight(t, PythonLexer(), TerminalFormatter())


def trim_last(s):
    return s[:-1]


@attrs(hash=True)
class StackEntry(object):
    file_capture_regex = attrib()
    file = attrib()
    pos = attrib()
    parent_func = attrib()
    line = attrib()

    def file_capture(self):
        cap = re.match(self.file_capture_regex, self.file)
        if not cap:
            return None

        return cap.groups()[0]


@attrs
class Config(object):
    # cleans up stack trace with uninteresting things. Usually packages, standard library, etc.
    ignores = attrib(
        default=[
            ".*/site-packages/.*",
            ".*traceback.format_stack.*",
            r".*/lib/python\d\.\d+/.*",
        ]
    )
    # shows a file, cleans up absolute path to a file
    file_capture = attrib(default="(.*)")
    # above this value mongomon starts working
    low_watermark_us = attrib(default=5000)
    # above this value mongomon flags as alert
    high_watermark_us = attrib(default=40000)
    # customize how mongodb query looks like before printing to screen
    query_filter = attrib(default=identity)
    # want to print to something else? replace this
    print_fn = attrib(default=print_)
    # want shorter stack traces? customize this
    stack_preprocess = attrib(default=trim_last)


class Monitor(monitoring.CommandListener):
    def __init__(self, config=Config()):
        super(Monitor, self).__init__()
        self.config = config
        self.started_cmds = {}

    def render_cmd(self, cmd, duration, q):
        is_over_hwm = duration > self.config.high_watermark_us
        fmt_duration = (
            colored.stylize(
                "{}us (HWM: {}us)".format(duration, self.config.high_watermark_us),
                colored.bg("red") + colored.fg("black"),
            )
            if is_over_hwm
            else colored.stylize(
                "{}us (LWM: {}us)".format(duration, self.config.low_watermark_us),
                colored.bg("yellow") + colored.fg("black"),
            )
        )

        self.config.print_fn(
            colored.stylize(
                "{} {}: {} in {}\n{}".format(
                    colored.stylize(
                        "mongomon", colored.fg("black") + colored.bg("magenta")
                    ),
                    colored.stylize(cmd[0], colored.fg("yellow")),
                    colored.stylize(cmd[1], colored.fg("magenta")),
                    fmt_duration,
                    pretty(pformat(self.config.query_filter(dict([q])))),
                ),
                colored.attr("underlined"),
            )
        )

    def render_stack(self, ents):
        for group in ents:
            ent = first(ents[group])
            self.config.print_fn(
                "{}".format(colored.stylize(ent.file_capture(), colored.fg("green")))
            )

            for i, ent in enumerate(ents[group]):
                maybe_dotdot = "" if i == 0 else "\t:\n"
                self.config.print_fn(
                    "{}{}\t{}".format(
                        colored.stylize(maybe_dotdot, colored.fg("dark_gray")),
                        colored.stylize(ent.pos, colored.fg("dark_gray")),
                        pretty(ent.line).strip(),
                    )
                )
            self.config.print_fn("")

    def is_below_lwm(self, duration):
        return duration < self.config.low_watermark_us

    def started(self, event):
        self.started_cmds[event.request_id] = event.command

    def succeeded(self, event):
        command = self.started_cmds[event.request_id]
        if not command:
            return

        self.started_cmds.pop(event.request_id)

        duration = event.duration_micros
        if self.is_below_lwm(duration):
            return

        [cmd, q, meta] = take(3, command.items())
        self.render_cmd(cmd, duration, q)

        ents = pipe(
            traceback.extract_stack(),
            self.config.stack_preprocess,
            map(lambda rec: StackEntry(self.config.file_capture, *rec)),
            filter(lambda ent: ent.file_capture()),
            filter(
                lambda ent: len(
                    list(
                        filter(
                            lambda p: re.match(p, ent.file, re.M), self.config.ignores
                        )
                    )
                )
                == 0
            ),
            groupby(lambda ent: ent.file),
        )
        self.render_stack(ents)

    def failed(self, event):
        pass

    def monitor(self):
        monitoring.register(self)
        self.config.print_fn(
            "\n\t{} {}.\n".format(
                colored.stylize(
                    "mongomon", colored.fg("black") + colored.bg("magenta")
                ),
                colored.stylize("active", colored.fg("green")),
            )
        )
        for (k, v) in asdict(self.config).items():
            self.config.print_fn(
                "\t{}: {}".format(
                    colored.stylize(k, colored.fg("magenta")),
                    pretty(pformat(v)).strip(),
                )
            )
        self.config.print_fn("")

