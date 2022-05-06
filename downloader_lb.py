import sys
import traceback
import datetime
import subprocess
import logging
import json
import re
from bs4 import BeautifulSoup
import stats
import downloader_common

def run():
    downloader = Downloader()

    logging.basicConfig(filename='downloader_lb.log', level=logging.INFO,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    downloader.loadThreaded('12.01.2022', '01.05.2022')

def run_old():
    rootPath = 'news_lib'
    downloader = Downloader(rootPath)
    #logging.basicConfig(filename='downloader_debug.log',level=logging.DEBUG)

    logging.basicConfig(filename='downloader_lb.log',level=logging.INFO)

    strdate = '01.01.2018'
    date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
    #dateTo = datetime.datetime.strptime('17.09.2000', '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime('01.04.2018', '%d.%m.%Y').date()

    while (date < dateTo):
      content = downloader.fb2(date)
      if len(content) > 0:
        with open(rootPath+'/lb/'+str(date.year)+'/lb_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)

class Article(object):
  def __init__(self, url, j):
    self.url = ''
    if url is not None:
      self.url = url

    self.dtStr = ''
    val = j[0]
    if val is not None:
      self.dtStr = val.strip()
    if  len(self.dtStr) > 4:
      self.timeStr = self.dtStr[-5:] # extract time (last 5 char)
    else:
      self.timeStr = '00:00'

    self.title = ''
    val = j[1]
    if val is not None:
      if isinstance(val, str):
        self.title = downloader_common.relpaceHtmlEntities(val)
      elif isinstance(val, list):
        self.title = downloader_common.relpaceHtmlEntities(val[0])

    self.summary = ''
    val = j[2]
    if val is not None:
      if isinstance(val, str):
        self.summary = downloader_common.relpaceHtmlEntities(val)
      elif isinstance(val, list):
        self.summary = downloader_common.relpaceHtmlEntities('\n'.join(val))

    self.body = list()
    val = j[3]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        locText = downloader_common.relpaceHtmlEntities(val)
      elif isinstance(val, list):
        locText = downloader_common.relpaceHtmlEntities('\n'.join(val))

      text = locText.strip() # trim

      # remove html comments
      text = re.subn("(<!--.*?-->)", "", text, flags=re.MULTILINE|re.DOTALL)[0]

      #remove empty lines
      for line in text.split('\n'):
        proLine = line.strip()
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
    if len(self.author) > 0:
      ret += '\n <p>' + downloader_common.escapeXml(self.author) + '</p>'
    if len(self.summary) > 0:
      ret += '\n <p><strong>' + downloader_common.escapeXml(self.summary) + '</strong></p>'
    ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + downloader_common.escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret

class Downloader(downloader_common.AbstractDownloader):

  def __init__(self, rootPath=''):
    self.baseUrl = 'https://lb.ua'
    self.getLinksCmd = downloader_common.XIDEL_CMD +' --xpath \'//ul[@class="lenta"]/li/div[@class="title"]/a/@href\''
    super().__init__('lb',maxDownloadThreads=1)

  def getNewsForDate(self, date):
    print('get news for ' + date.strftime('%d.%m.%Y'))
    logging.info(date.strftime('%d.%m.%Y'))
    url = self.baseUrl + '/archive/' + date.strftime('%Y/%m/%d')
    print('url: ' +url)
    articleList = list()
    downloadedUrls = set()
    # replace {0} with url
    cmd = self.getLinksCmd.format(url)
    #print('cmd: ' +cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for ln in p.stdout:
      line = ln.decode('utf-8').strip()
      if line in downloadedUrls:
        print ('ignore url (already loaded): '+ line)
        continue

      if len(line) > 0 and line.startswith("https://lb.ua/"):
        print ('load article: ' + line)
        try:
          article = self.loadArticle(line)
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
                logging.error("IGNORE: Article is empty. URL: "+ line)
                article.info()
            if bAddToList:
              if len(article.body) == 1:
                logging.warning("Article (length = "+str(len(text))+") has one paragraph. URL: "+ line)
              articleList.append(article)
              downloadedUrls.add(line)
          else:
            #exit
            logging.warning("Article can not be loaded from URL: "+ line)
            #sys.exit("Article can not be loaded from URL: "+ line)
        except SystemExit:
          raise
        except:
          exc_type, exc_value, exc_traceback = sys.exc_info()
          print ("Unexpected error: ", exc_type)
          traceback.print_exception(exc_type, exc_value, exc_traceback)
      else:
        print ('ignore url: '+ line)
        logging.warning('ignore url (not unian): '+ line)
    # order articles by time
    return sorted(articleList, key=lambda x: x.timeStr)

  def loadArticle(self, url):
    """cmd = ('xidel '+url+' -q '
           ' --xpath \'//article[@class="material clearfix"]//div[@class="header"]/div[@class="date"]/time\'' #datetime in format dd month yyyy, hh:mi
           ' --xpath \'//article[@class="material clearfix"]//div[@class="header"]/h1\'' #title
           ' --xpath \'//article[@class="material clearfix"]//div[@class="header"]/h2\'' #summary
           ' --xpath \'//article[@class="material clearfix"]/*[self::p or self::h4]\'' #article body
           ' --xpath \'//article[@class="material clearfix"]//div[@class="header"]/div[@class="authors"]\'' #authors
           ' --output-format=json-wrapped') #output as json
    """
    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//article[@class="material"]//div[@class="header"]/div[@class="date"]/time\'' #datetime in format dd month yyyy, hh:mi
           ' --xpath \'//article[@class="material"]//div[@class="header"]/h1\'' #title
           ' --xpath \'//article[@class="material"]//div[@class="header"]/h2\'' #summary
           ' --xpath \'//article[@class="material"]//div[@itemprop="articleBody"]/*[self::p or self::h4]\'' #article body
           ' --xpath \'//article[@class="material"]//div[@class="header"]/div[@class="authors"]\'' #authors
           ' --output-format=json-wrapped') #output as json
    #print('cmd: '+cmd)
    #xidel http://ukr.lb.ua/blog/vitaliy_skotsyk/355817_persha_dekada_roku_kudi_pryamuie.html -q --xpath '//div[@class="article-text"]//span[@itemprop="articleBody"]//p'
    # http://ukr.lb.ua/world/2012/03/27/142868_aeroportah_germanii_zavtra_proydut.html

    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    #print(result)
    jsonArt = json.loads(result)

    article = None
    try:
      if len(jsonArt) > 0 :
        article = Article(url, jsonArt)
      else:
        #logging.warning("Nothing can be load from: "+url)
        print("Nothing can be load from: "+url)
        return None

    except:
      exc_type, exc_value, exc_traceback = sys.exc_info()
      print ("Unexpected error: ", exc_type, "In article ", result)
      traceback.print_exception(exc_type, exc_value, exc_traceback)

    return article

  def loadArticleTextFromHtml(self, xidelCmd):
    p = subprocess.Popen(xidelCmd, shell=True, stdout=subprocess.PIPE)
    origHtml = p.communicate()[0].decode('utf-8')
    logging.debug(">> loadArticleTextFromHtml()")
    logging.debug(origHtml)
    #print(result)
    html = origHtml.replace('<br>', '[br]').replace('</br>', '').replace('<br/>', '[br]').replace('</p>', '[br]</p>').replace('<div>', '<div>[br]').replace('</div>', '[br]</div>').replace('<br />', '[br]')
    html = html.replace('<BR>', '[br]').replace('</BR>', '').replace('</P>', '[br]</P>').replace('<BR />', '[br]')
    logging.debug(">> replace with [br]")
    logging.debug(html)
    soup = BeautifulSoup(html, 'html.parser')
    txt = soup.get_text()
    #if len(txt) > 1000 and txt.count('[br]') == 0:
    return txt.replace('[br]', '\n')

  def fb2(self, date):
    #strdate = '%d.%d.%d' % (date.day, date.month, date.year)
    today = datetime.date.today()
    url = self.baseUrl + '/archive/' + date.strftime('%Y/%m/%d')
    articleList = self.getNewsForDate(date)
    if len(articleList) < 1:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Лівий берег</last-name></author>'
    ret += '\n  <book-title>LB.ua. Новини ' + date.strftime('%d.%m.%Y') + '</book-title>'
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
        print ("Article ", article.info() ,"Unexpected error: ", sys.exc_info()[0])
    ret += '\n</body>'
    ret += '\n</FictionBook>'
    return ret

"""
  def load(self, sDateFrom, sDateTo):
    logging.basicConfig(filename='downloader_lb.log',level=logging.INFO)
    date = datetime.datetime.strptime(sDateFrom, '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime(sDateTo, '%d.%m.%Y').date()

    while (date < dateTo):
      content = self.fb2(date)
      if len(content) > 0:
        with open(self.rootPath+'/lb/'+str(date.year)+'/lb_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)
    logging.info("Job completed")
"""


"""
strdate = '12.04.2012'
date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
downloader.getNewsForDate(date)

downloader = Downloader(".")
logging.basicConfig(filename='downloader_lb_debug.log',level=logging.DEBUG)
article = downloader.loadArticle('https://ukr.lb.ua/world/2018/01/01/386315_12_lyudey_zaginuli_aviakatastrofi.html')
print(article.info())
"""

if __name__ == '__main__':
    run()
