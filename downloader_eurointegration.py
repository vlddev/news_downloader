import sys
import traceback
import datetime
import subprocess
import json
import logging
from bs4 import BeautifulSoup
import stats
import downloader_common


def run():
    rootPath = downloader_common.rootPath
    downloader = Downloader(rootPath)

    logging.basicConfig(filename='downloader_eurointegration.log', level=logging.INFO,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    strdate = '28.12.2017'
    date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime('01.01.2018', '%d.%m.%Y').date()

    while (date < dateTo):
      content = downloader.fb2(date)
      if len(content) > 0:
        with open(rootPath+'/eurointegration/'+str(date.year)+'/eurointegration_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)


def test():
    rootPath = downloader_common.rootPath
    downloader = Downloader(rootPath)

    logging.basicConfig(filename='downloader_eurointegration.log', level=logging.INFO,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    article = downloader.loadArticle('http://www.eurointegration.com.ua/articles/2014/05/27/7023100/')
    print(article.info())

    """

    article = downloader.loadArticle('http://www.epravda.com.ua/publications/2017/03/2/622180/')
    print(article.info())
    """


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
      self.dtStr = val
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

    self.body = list()
    val = None
    if len(j) > 2:
      val = j[2]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        locText = val
      elif isinstance(val, list):
        locText = '\n'.join(val)
      text = locText.strip() # trim

      #remove empty lines
      for line in text.split('\n'):
        proLine = downloader_common.relpaceHtmlEntities(line.strip())
        if len(proLine) > 0:
          self.body.append(proLine)

    self.author = ''
    if len(j) > 3:
      val = j[3]
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
    if len(self.author) > 0:
      ret += '\n <p>' + downloader_common.escapeXml(self.author) + '</p>'
    ret += '\n <p>' + self.timeStr + '</p>'
    #ret += '\n <p><strong>' + self.summary + '</strong></p>'
    ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + downloader_common.escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret


class Downloader(object):

  def __init__(self, rootPath):
    self.baseUrl = 'http://www.eurointegration.com.ua'
    self.getLinksCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@class="fblock"]//div[@class="rpad"]//p//a/@href\''
    self.rootPath = rootPath #'/home/vlad/Dokumente/python/news_lib'

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
    # xpath for articles
    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//div[@class="rpad"]//span[@class="dt2"]\'' #time
           ' --xpath \'//div[@class="rpad"]//h1[@class="title"]\'' #title
           ' --xpath \'//div[@class="rpad"]//div[@class="dummy text"]\'' #article  text
           ' --output-format=json-wrapped' #output as json
           ' --output-encoding=windows-1251')  #pravda.com.ua uses encoding=windows-1251
    #print('cmd: '+cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('windows-1251')
    #print(result)
    jsonArt = json.loads(result)

    if len(jsonArt) == 0:
      return None

    aTextCmd = (downloader_common.XIDEL_CMD.format(url) +
       ' --xpath \'//div[@class="rpad"]//div[@class="text"]\'' #article text
       ' --output-format=html' #output as html
       ' --output-encoding=windows-1251')  #pravda.com.ua uses encoding=windows-1251

    jsonArt[2] = self.loadArticleTextFromHtml(aTextCmd)

    """ xpath for articles until 31.12.2015
    # xpath for articles after 31.12.2015
    aTextCmd = (downloader_common.XIDEL_CMD.format(url) +
       ' --xpath \'//div[@class="block_post"]//div[@class="post__text"]\'' #article text
       ' --output-format=html' #output as html
       ' --output-encoding=windows-1251')  #pravda.com.ua uses encoding=windows-1251
    """

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
    origHtml = p.communicate()[0].decode('windows-1251')
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
    #remove twitter
    for bq in soup('blockquote'):
        if bq.has_attr('class') and bq['class'][0] == 'twitter-tweet':
            bq.extract()
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
    ret += '\n  <book-title>Європейська правда. ' + date.strftime('%d.%m.%Y') + '</book-title>'
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
    logging.basicConfig(filename='downloader_eurointegration.log', level=logging.INFO,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')
    date = datetime.datetime.strptime(sDateFrom, '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime(sDateTo, '%d.%m.%Y').date()

    while (date < dateTo):
      content = self.fb2(date)
      if len(content) > 0:
        with open(self.rootPath+'/eurointegration/'+str(date.year)+'/eurointegration_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)
    logging.info("Job completed")


if __name__ == '__main__':
    run()
