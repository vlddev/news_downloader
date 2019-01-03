import sys, traceback
import functools
import datetime
import logging
import concurrent.futures

USER_AGENT="Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1"
XIDEL_CMD='xidel "{0}" -s --user-agent="'+USER_AGENT+'"'
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

class BaseArticle(object):
  def __init__(self):
    self.dtStr = ''
    self.timeStr = ''
    self.url = ''
    self.title = ''
    self.author = ''
    self.summary = ''
    self.source = ''
    self.body = None


  def info(self):
    print('dtStr: '+self.dtStr)
    print('timeStr: '+self.timeStr)
    print('url: '+self.url)
    print('title: '+str(self.title))
    print('author: '+str(self.author))
    print('summary: '+str(self.summary))
    print('source: '+str(self.source))
    print('body: ' + "\n".join(self.body))

  def fb2(self):
    ret = '<section><title><p>' + escapeXml(self.title) + '</p></title>'
    if len(self.author) > 0:
      ret += '\n <p>' + escapeXml(self.author) + '</p>'
      ret += '\n <empty-line/>'
    if len(self.summary) > 0:
      ret += '\n <p><strong>' + escapeXml(self.summary) + '</strong></p>'
      ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret


class AbstractDownloader(object):

  def __init__(self, siteName):
    self.rootPath = rootPath
    self.maxDownloadThreads = 30
    self.siteName = siteName

  def fb2(self, date):
    return ''

  def getFileNameForDate(self, date):
    return '%s/%s/%s/%s_%s.fb2' % (self.rootPath, self.siteName, str(date.year), self.siteName, str(date))

  def load(self, sDateFrom, sDateTo):
    date = datetime.datetime.strptime(sDateFrom, '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime(sDateTo, '%d.%m.%Y').date()

    while (date < dateTo):
      content = self.fb2(date)
      if len(content) > 0:
        outFileName = self.getFileNameForDate(date)
        with open(outFileName, "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)
    logging.info("Job completed")

  def loadThreaded(self, sDateFrom, sDateTo):
    date = datetime.datetime.strptime(sDateFrom, '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime(sDateTo, '%d.%m.%Y').date()
    logging.info("Job started for site %s" % self.siteName)

    dateList = []
    while (date < dateTo):
      dateList.append(date)
      date += datetime.timedelta(days=1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=self.maxDownloadThreads) as executor:
      futureContents = {executor.submit(self.fb2, curDate): curDate for curDate in dateList}
      for future in concurrent.futures.as_completed(futureContents):
        curDate = futureContents[future]
        try:
          content = future.result()
          if len(content) > 0:
            outFileName = self.getFileNameForDate(curDate)
            print("Write to file: " + outFileName)
            with open(outFileName, "w") as fb2_file:
              fb2_file.write(content)
          else:
            logging.info("No content for site %s for %s" % (self.siteName, str(curDate)))
        except SystemExit:
          raise
        except BaseException:
          exc_type, exc_value, exc_traceback = sys.exc_info()
          print("Unexpected error: ", exc_type)
          traceback.print_exception(exc_type, exc_value, exc_traceback)

    logging.info("Job completed for site %s" % self.siteName)
