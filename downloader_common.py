import functools

USER_AGENT="Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1"
XIDEL_CMD='xidel "{0}" -q --user-agent="'+USER_AGENT+'"'
rootPath = '/home/vlad/Dokumente/python/news_lib'

def relpaceHtmlEntities(val):
  if val is not None and isinstance(val, str):
    repls = (('&#39;', '\''), ('&quot;', '"'), ('&hellip;', '…'), ('&nbsp;', ' '), ('&ndash;', '–'),
        ('&mdash;', '–'), ('&rsquo;', '\''), ('&lsquo;', '\''), ('&apos;', '\''), ('&acute;', '\''),
        ('', '\''), ('&#8203;', ''), ('&bdquo;', '"'), ('&amp;', '&')
    )
    #return val.replace('&#39;', '\'').replace('&quot;', '"').replace('&hellip;', '…').replace('&nbsp;', ' ').replace('&ndash;', '–').replace('&mdash;', '–').
    #        replace('&rsquo;', '\'').replace('&apos;','\'').replace('','\'')
    return functools.reduce(lambda a, kv: a.replace(*kv), repls, val)
  else:
    return val

def escapeXml(val):
  if val is not None and isinstance(val, str):
      repls = (('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'), ('\a', ''))
      #val.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\a', '')
      return functools.reduce(lambda a, kv: a.replace(*kv), repls, val)
  else:
    return val
