import sys, traceback
import datetime
import subprocess
import json
import logging
from bs4 import BeautifulSoup
import stats
import downloader_common
import concurrent.futures

def run():
    rootPath = downloader_common.rootPath
    downloader = Downloader(rootPath)
    logging.basicConfig(filename='downloader_champion.log',level=logging.INFO,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    downloader.load('01.01.2018', '01.09.2018')

def test():
    rootPath = downloader_common.rootPath
    downloader = Downloader(rootPath)

    logging.basicConfig(filename='downloader_champion.log',level=logging.DEBUG,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    article = downloader.loadArticle('https://champion.com.ua/football/2018/03/31/703170/vlasnik-ruhu-priviz-do-lvova-peris-hilton-na-vidkrittya-svogo-gotelyu-foto')
    print(article.info())


class Article(object):
  def __init__(self, url, j):
    self.url = ''
    if url is not None:
      self.url = url

    self.dtStr = ''
    val = None
    if len(j) > 0:
      val = j[0]

    if val is not None:
      if isinstance(val, str):
        self.dtStr = downloader_common.relpaceHtmlEntities(val)
      elif isinstance(val, list):
        self.dtStr = downloader_common.relpaceHtmlEntities(' '.join(val))
    if  len(self.dtStr) > 4:
      self.timeStr = self.dtStr[-5:] # extract time (last five char)
    else:
      self.timeStr = '00:00'

    self.title = ''
    val = None
    if len(j) > 1:
      val = j[1]
    if val is not None:
      if isinstance(val, str):
        self.title = downloader_common.relpaceHtmlEntities(val)
      elif isinstance(val, list):
        self.title = downloader_common.relpaceHtmlEntities(' '.join(val))

    self.summary = ''
    val = None
    if len(j) > 2:
      val = j[2]
    if val is not None:
      if isinstance(val, str):
        self.summary = downloader_common.relpaceHtmlEntities(val)
      elif isinstance(val, list):
        self.summary = downloader_common.relpaceHtmlEntities(' '.join(val))

    self.body = list()
    val = None
    if len(j) > 3:
      val = j[3]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        locText = val
      elif isinstance(val, list):
        locText = '\n'.join(val)
      if len(self.title) > 0 and len(locText) > 0:
        locText = locText.replace(self.title,'',1).strip() # remove title from the body, trim
      if len(self.summary) > 0 and len(locText) > 0:
        locText = locText.replace(self.summary,'',2).strip() # remove summary from the body, trim
      text = locText.strip() # trim

      #remove empty lines
      for line in text.split('\n'):
        proLine = downloader_common.relpaceHtmlEntities(line.strip()).strip()
        if len(proLine) > 0:
          self.body.append(proLine)

    self.author = ''
    if len(j) > 4:
      val = j[4]
      if val is not None:
        self.author = val.strip()

  def info(self):
    print('dtStr: '+self.dtStr)
    print('timeStr: '+self.timeStr)
    print('url: '+self.url)
    print('title: '+str(self.title))
    print('author: '+str(self.author))
    print('summary: '+str(self.summary))
    print('body: ' + "\n".join(self.body))

  def fb2(self):
    ret = '<section><title><p>' + downloader_common.escapeXml(self.title) + '</p></title>'
    ret += '\n <p>' + self.timeStr + '</p>'
    if len(self.summary) > 0:
        ret += '\n <p><strong>' + downloader_common.escapeXml(self.summary) + '</strong></p>'
    ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + downloader_common.escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret

class Downloader(object):

  def __init__(self, rootPath):
    self.baseUrl = 'https://www.champion.com.ua'
    self.getLinksCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@class="listing listing-light mb-3"]//div[@class="listing__itm"]//a/@href\''
    self.rootPath = rootPath #'/home/vlad/Dokumente/python/news_lib'
    self.maxDownloadThreads = 30


  def getNewsForDate(self, date):
    print('get news for ' + date.strftime('%d.%m.%Y'))
    url = self.baseUrl + '/archives/date_'+date.strftime('%d%m%Y')+'/'
    print('url: ' +url)
    # replace {0} with url
    articleList = list()
    downloadedUrls = set()
    cmd = self.getLinksCmd.format(url)
    #print('cmd: ' +cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for ln in p.stdout:
      line = ln.decode('utf-8').strip()
      if len(line) > 0 and not line.startswith('http') and line.startswith('/') and line not in downloadedUrls:
        print ('load article: '+self.baseUrl + line)
        try:
          article = self.loadArticle(self.baseUrl + line)
          if article is not None:
            bAddToList = True
            text = " ".join(article.body)
            text = text.strip()
            if len(text) > 0:
              textStats = stats.TextStats(text)
              if textStats.isUkr() and textStats.isRus():
                bAddToList = False
                logging.warning("IGNORE: Article is Ukr and Rus. URL: "+ line)
                logging.info("   stats: "+str(textStats.common_text_20))
              elif textStats.isRus():
                bAddToList = False
                logging.warning("IGNORE: Article is Rus. URL: "+ line)
              elif textStats.isEng():
                bAddToList = False
                logging.warning("IGNORE: Article is Eng. URL: "+ line)
              elif textStats.isUkr():
                bAddToList = True
              elif not (textStats.isUkr() or textStats.isRus() or textStats.isEng()):
                  if textStats.hasUkrLetter():
                      bAddToList = True
                  else:
                      bAddToList = False
                      logging.warning("IGNORE: Article language not detected. Has no only-ukr chars. URL: "+ line)
              else:
                  logging.warn("WARNING: Article language not detected (check manually). URL: "+ line)
                  logging.info("   text length: "+ str(len(text)))
                  bAddToList = True
            else:
                bAddToList = False
                logging.error("IGNORE: Article is empty. URL: "+self.baseUrl + line)
            if bAddToList:
              articleList.append(article)
              downloadedUrls.add(line)
          else:
            #exit
            logging.error("Article can not be loaded from URL: "+self.baseUrl + line)
            #sys.exit("Article can not be loaded from URL: "+self.baseUrl + line)
        except SystemExit:
          raise
        except:
          exc_type, exc_value, exc_traceback = sys.exc_info()
          print ("Unexpected error: ", exc_type)
          traceback.print_exception(exc_type, exc_value, exc_traceback)
      else:
        print ('ignore url: '+ line)
    # order articles by time
    return sorted(articleList, key=lambda x: x.timeStr)

  def loadArticle(self, url):
    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//article[@class="article"]//div[@class="listing__itm__meta"]/span[@class="listing__itm__date"]\'' #datetime
           ' --xpath \'//article[@class="article"]//h1[@class="article__title" or @class="main"]\'' #title
           ' --xpath \'//article[@class="article"]//div[@class="subtitle"]\'' #summary
           ' --xpath \'//article[@class="article"]//div[@class="dummy"]\'' #article text
           ' --output-format=json-wrapped' #output as json
           ' --output-encoding=utf-8')  

    #xidel http://www.champion.com.ua/basketball/2000/09/29/90601/ -q --xpath '//div[@class="tt41 white"]//div[@class="tit3"]'
    #print('cmd: '+cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    #print(result)
    jsonArt = json.loads(result)

    if len(jsonArt) == 0:
      return None

    aTextCmd = (downloader_common.XIDEL_CMD.format(url) +
       # ' --xpath \'//div[@class="tt6" or @class="tt41 white"]//div[@class="mtext _ga1_on_"]/node()[not(h1[@class="dop3"] and h1[@class="main"] and div[@class="subtitle"])]\'' #article text with title
       ' --xpath \'//article[@class="article"]//div[@class="article__content"]/node()[not(self::table[@class="tb_center"] '
       '       or self::iframe[@class="instagram-media instagram-media-rendered"]'
       '       or self::blockquote[@class="instagram-media"]'
       '       or self::blockquote[@class="twitter-tweet"])]\'' #article text with title
       ' --output-format=html' #output as html
       ' --output-encoding=utf-8')  
    jsonArt[3] = self.loadArticleTextFromHtml(aTextCmd)

    article = None
    try:
      article = Article(url, jsonArt)
    except:
      exc_type, exc_value, exc_traceback = sys.exc_info()
      print ("Unexpected error: ", exc_type, "In article ", result)
      traceback.print_exception(exc_type, exc_value, exc_traceback)
    #article.info()

    return article

  def loadArticleTextFromHtml(self, xidelCmd):
    p = subprocess.Popen(xidelCmd, shell=True, stdout=subprocess.PIPE)
    origHtml = p.communicate()[0].decode('utf-8')
    logging.debug(">> loadArticleTextFromHtml()")
    logging.debug(origHtml)
    #print(result)
    html = origHtml.replace('<br>', '[br]').replace('</br>', '').replace('<br/>', '[br]').replace('</p>', '[br]</p>').replace('<div>', '<div>[br]').replace('</div>', '[br]</div>').replace('<br />', '[br]')
    html = html.replace('<BR>', '[br]').replace('</BR>', '').replace('</P>', '[br]</P>').replace('<BR />', '[br]')
    #html = html.replace('<b>', '[strong]').replace('</b>', '[/strong]')
    #html = html.replace('<strong>', '[strong]').replace('</strong>', '[/strong]')
    #html = html.replace('<i>', '[emphasis]').replace('</i>', '[/emphasis]')
    logging.debug(">> replace with [br]")
    logging.debug(html)
    soup = BeautifulSoup(html, 'html.parser')
    #remove scripts
    [s.extract() for s in soup('script')]
    return soup.get_text().replace('[br]', '\n')

  def fb2(self, date):
    today = datetime.date.today()
    url = self.baseUrl + '/archives/date_'+date.strftime('%d%m%Y')+'/'
    articleList = self.getNewsForDate(date)
    if len(articleList) < 1:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Українська правда</last-name></author>'
    ret += '\n  <book-title>Чемпіон. Новини ' + date.strftime('%d.%m.%Y') + '</book-title>'
    ret += '\n  <date>' + str(date) + '</date>'
    ret += '\n  <lang>uk</lang>'
    ret += '\n </title-info>'
    ret += '\n <document-info>'
    ret += '\n  <author><nickname>V.Vlad</nickname></author>'
    ret += '\n  <date value="' + str(today) + '">' + str(today) + '</date>'
    ret += '\n  <version>1.0</version>'
    ret += '\n  <src-url>' + url + '</src-url>'
    ret += '\n </document-info>'
    ret += '\n</description>'
    ret += '\n<body>'
    for article in articleList:
      try:
        ret += '\n' + article.fb2()
      except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print ("Unexpected error: ", exc_type)
        traceback.print_exception(exc_type, exc_value, exc_traceback)
    ret += '\n</body>'
    ret += '\n</FictionBook>'
    return ret

  def load(self, sDateFrom, sDateTo):
    date = datetime.datetime.strptime(sDateFrom, '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime(sDateTo, '%d.%m.%Y').date()
    logging.info("Job %s started" % ("downloader_champion"))

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
            outFileName = '%s/champion/%s/champion_%s.fb2' % (self.rootPath, str(curDate.year), str(curDate))
            print("Write to file: " + outFileName)
            with open(outFileName, "w") as fb2_file:
              fb2_file.write(content)
        except SystemExit:
          raise
        except BaseException:
          exc_type, exc_value, exc_traceback = sys.exc_info()
          print("Unexpected error: ", exc_type)
          traceback.print_exception(exc_type, exc_value, exc_traceback)

    logging.info("Job %s completed" % ("downloader_champion"))


if __name__ == '__main__':
  run()
