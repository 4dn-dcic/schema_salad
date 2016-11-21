import ruamel.yaml
import ruamel.yaml.comments
import re
import os

lineno_re = re.compile("^(.*?:[0-9]+:[0-9]+: )(( *)(.*))")

def _add_lc_filename(r, source):
    if isinstance(r, ruamel.yaml.comments.CommentedBase):
        r.lc.filename = source
    if isinstance(r, list):
        for d in r:
            _add_lc_filename(d, source)
    elif isinstance(r, dict):
        for d in r.itervalues():
            _add_lc_filename(d, source)

def relname(source):
    if source.startswith("file://"):
        source = source[7:]
        source = os.path.relpath(source)
    return source

def add_lc_filename(r, source):
    return _add_lc_filename(r, relname(source))

def reflow(text, maxline, shift=""):
    if maxline < 20:
        maxline = 20
    if len(text) > maxline:
        sp = text.rfind(' ', 0, maxline)
        if sp < 1:
            sp = text.find(' ', sp+1)
            if sp == -1:
                sp = len(text)
        if sp < len(text):
            return "%s\n%s%s" % (text[0:sp], shift, reflow(text[sp+1:], maxline, shift))
    return text

def indent(v, nolead=False, shift=u"  ", bullet=u"  "):  # type: (Union[str, unicode], bool) -> unicode
    if nolead:
        return v.splitlines()[0] + u"\n".join([shift + l for l in v.splitlines()[1:]])
    else:
        def lineno(i, l):
            r = lineno_re.match(l)
            if r:
                return r.group(1) + (bullet if i == 0 else shift) + r.group(2)
            else:
                return (bullet if i == 0 else shift) + l

        return u"\n".join([lineno(i, l) for i, l in enumerate(v.splitlines())])

def bullets(textlist, bul):
    if len(textlist) == 1:
        return textlist[0]
    else:
        return "\n".join(indent(t, bullet=bul) for t in textlist)

def strip_dup_lineno(text, maxline=None):
    if maxline is None:
        maxline = int(os.environ.get("COLUMNS", 100))
    pre = None
    msg = []
    for l in text.splitlines():
        g = lineno_re.match(l)
        if not g:
            msg.append(l)
            continue
        shift = len(g.group(1)) + len(g.group(3))
        g2 = reflow(g.group(2), maxline-shift, " " * shift)
        if g.group(1) != pre:
            pre = g.group(1)
            msg.append(pre + g2)
        else:
            g2 = reflow(g.group(2), maxline-len(g.group(1)), " " * (len(g.group(1))+len(g.group(3))))
            msg.append(" " * len(g.group(1)) + g2)
    return "\n".join(msg)

class SourceLine(object):
    def __init__(self, item, key=None, raise_type=unicode):
        self.item = item
        self.key = key
        self.raise_type = raise_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_value:
            return
        raise self.makeError(unicode(exc_value))

    def makeError(self, msg):
        if not isinstance(self.item, ruamel.yaml.comments.CommentedBase):
            return self.raise_type(msg)
        errs = []
        if self.key is None:
            lead = "%s:%i:%i:" % (self.item.lc.filename,
                                  self.item.lc.line+1,
                                  self.item.lc.col+1)
        else:
            lead = "%s:%i:%i:" % (self.item.lc.filename,
                                  self.item.lc.data[self.key][0]+1,
                                  self.item.lc.data[self.key][1]+1)
        for m in msg.splitlines():
            if lineno_re.match(m):
                errs.append(m)
            else:
                errs.append("%s %s" % (lead, m))
        return self.raise_type("\n".join(errs))
