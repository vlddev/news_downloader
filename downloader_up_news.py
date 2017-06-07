import sys, traceback
import datetime
import subprocess
import json
import logging
from bs4 import BeautifulSoup
import stats
import re
import downloader_common

def run():
    rootPath = '/home/vlad/Dokumente/python/news_lib'
    downloader = Downloader(rootPath)
    #logging.basicConfig(filename='downloader_debug.log',level=logging.DEBUG)

    logging.basicConfig(filename='downloader_up_news.log',level=logging.INFO)

    strdate = '05.03.2017'
    date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
    #dateTo = datetime.datetime.strptime('17.09.2000', '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime('08.03.2017', '%d.%m.%Y').date()

    while (date < dateTo):
      content = downloader.fb2(date)
      if len(content) > 0:
        with open(rootPath+'/pravda_com_ua_sa/'+str(date.year)+'/up_news_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)

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
        self.dtStr = val
      elif isinstance(val, list):
        self.dtStr = val[0]
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
        locText = val[0]
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
    print('dtStr: '+self.dtStr);
    print('timeStr: '+self.timeStr);
    print('url: '+self.url);
    print('title: '+str(self.title));
    print('author: '+str(self.author));
    print('summary: '+str(self.summary));
    print('body: ' + "\n".join(self.body));

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
    self.baseUrl = 'http://www.pravda.com.ua'
    self.getLinksCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@class="block block_news_all"]//a/@href\' '
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
                logging.warning("IGNORE: Article is Ukr and Rus. URL: "+self.baseUrl + line)
                logging.info("   stats: "+str(textStats.common_text_20))
              elif textStats.isRus():
                bAddToList = False
                logging.warning("IGNORE: Article is Rus. URL: "+self.baseUrl + line)
              elif textStats.isEng():
                bAddToList = False
                logging.warning("IGNORE: Article is Eng. URL: "+self.baseUrl + line)
              elif not (textStats.isUkr() or textStats.isRus() or textStats.isEng()):
                if textStats.hasRusLetter():
                  bAddToList = False
                  logging.warning("IGNORE: Article (language not detected) has Rus letters. URL: "+self.baseUrl + line)
                elif textStats.hasUkrLetter():
                  bAddToList = True
                elif len(text) < 450: #ignore article
                  bAddToList = False
                  logging.warning("IGNORE: Article language not detected. URL: "+self.baseUrl + line)
                  logging.info("   text length: "+ str(len(text)))
                  logging.info("   stats: "+str(textStats.common_text_20))
                elif line in ['/articles/2012/10/28/6975576/','/articles/2014/01/23/7011063/','/articles/2014/01/28/7011761/']:
                  bAddToList = False
                  logging.error("IGNORE: Article has not language. URL: "+self.baseUrl + line)
                else:
                  logging.error("Article language not detected. URL: "+self.baseUrl + line)
                  logging.info("   text length: "+ str(len(text)))
                  logging.info("   stats: "+str(textStats.common_text_20))
                  print(article.info())
                  sys.exit("Article language not detected. URL: "+self.baseUrl + line)
            else:
              if line in ['/articles/2005/11/17/3019729/','/articles/2006/02/8/3061761/','/articles/2007/01/31/3203836/',
                          '/articles/2007/03/15/3216901/','/articles/2007/03/28/3221114/','/articles/2007/03/30/3222055/',
                          '/articles/2007/03/31/3222674/','/articles/2007/04/3/3224158/', '/articles/2007/04/3/3224119/',
                          '/articles/2007/04/11/3227795/','/articles/2007/04/11/3227746/', '/articles/2007/09/30/3292450/',
                          '/articles/2008/05/26/3448561/', '/articles/2008/05/26/3448546/', '/articles/2009/01/12/3668969/',
                          '/articles/2009/06/10/4013079/', '/news/2010/01/15/4621064/', '/articles/2010/01/18/4630133/',
                          '/news/2010/05/31/5093418/', '/news/2010/06/18/5152762/', '/news/2010/06/22/5161355/', '/news/2010/07/12/5216065/',
                          '/news/2010/10/12/5471544/', '/news/2011/01/18/5801413/', '/news/2011/01/28/5847095/', '/news/2011/02/8/5893563/',
                          '/articles/2011/02/28/5968537/', '/news/2011/03/23/6044026/', '/news/2011/03/25/6051379/', '/news/2011/06/16/6302922/',
                          '/articles/2011/11/16/6758771/', '/articles/2012/04/5/6962138/', '/articles/2012/04/20/6963082/',
                          '/articles/2012/04/20/6963077/', '/articles/2012/07/30/6969816/', '/articles/2012/07/30/6967948/',
                          '/articles/2012/08/1/6969957/', '/news/2012/08/1/6969973/', '/news/2013/12/3/7004679/',
                          ]:
                bAddToList = False
                logging.error("IGNORE: Article is empty. URL: "+self.baseUrl + line)
              elif len(article.timeStr) > 0 and len(article.title) > 0:
                bAddToList = False
                logging.error("IGNORE: Empty article with title and time. URL: "+self.baseUrl + line)
              else:
                bAddToList = False
                logging.error("Article is empty. URL: "+self.baseUrl + line)
                print(article.info())
                sys.exit("Article is empty. URL: "+self.baseUrl + line)
            if len(article.body) == 1:
                logging.warning("Article has one paragraph. URL: "+self.baseUrl + line)
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
          raise
      else:
        print ('ignore url: '+ line)
    # order articles by time
    return sorted(articleList, key=lambda x: x.timeStr)

  def loadArticle(self, url):
    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//div[@class="post post_news"]//div[@class="post_news__date"]\'' #date
           ' --xpath \'//div[@class="post post_news"]//h1[@class="post_news__title"]\'' #title
           ' --xpath \'//div[@class="post post_news"]//div[@class="post_news__text dummy"]\'' #empty text
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
       ' --xpath \'//div[@class="post post_news"]//div[@class="post_news__text"]\'' #article text
       ' --output-format=html' #output as html
       ' --output-encoding=windows-1251')  #pravda.com.ua uses encoding=windows-1251
    jsonArt[2] = self.loadArticleTextFromHtml(aTextCmd)

    article = None
    try:
      article = Article(url, jsonArt)
    except:
      exc_type, exc_value, exc_traceback = sys.exc_info()
      print ("Unexpected error: ", exc_type, "In article ", result)
      traceback.print_exception(exc_type, exc_value, exc_traceback)
    #article.info()

    if len(article.body) <= 1 : #article has only one row, download as html
      logging.debug("article has only one row, download as html")
      text = " ".join(article.body)
      text = text.strip()
      if len(text) == 0 and len(article.dtStr) == 0 and len(article.title) == 0: #article is empty, try anothe formats
        logging.debug("loadJsonArticle1")
        jsonArt = self.loadJsonArticle1(url)
        if jsonArt[2] is not None and len(jsonArt[2].strip()) > 0: #article is not empty
          aTextCmd = (downloader_common.XIDEL_CMD.format(url) +
             ' --xpath \'//div[@class="post post_news post_article"]//div[@class="post_news__text"]\'' #article text
             ' --output-format=html' #output as html
             ' --output-encoding=windows-1251')  #pravda.com.ua uses encoding=windows-1251
          jsonArt[2] = self.loadArticleTextFromHtml(aTextCmd)
        elif jsonArt[0] is None and jsonArt[1] is None:
          logging.debug("loadJsonArticle2")
          jsonArt = self.loadJsonArticle2(url)
          if jsonArt[2] is not None and len(jsonArt[2].strip()) > 0: #article is not empty
            aTextCmd = (downloader_common.XIDEL_CMD.format(url) +
               ' --xpath \'//div[@class="post post_news post_column"]//div[@class="post_news__text"]\'' #article text
               ' --output-format=html' #output as html
               ' --output-encoding=windows-1251')  #pravda.com.ua uses encoding=windows-1251
            jsonArt[2] = self.loadArticleTextFromHtml(aTextCmd)
        article = None
        try:
          article = Article(url, jsonArt)
        except:
          exc_type, exc_value, exc_traceback = sys.exc_info()
          print ("Unexpected error: ", exc_type, "In article ", result)
          traceback.print_exception(exc_type, exc_value, exc_traceback)
        #article.info()
      else:
        logging.debug("title: "+article.title)
        logging.debug("dtStr: "+article.dtStr)

    return article

  def loadArticleTextFromHtml(self, xidelCmd):
    p = subprocess.Popen(xidelCmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('windows-1251')
    logging.debug(">> loadArticleTextFromHtml()")
    logging.debug(result)
    #print(result)
    txt = re.sub('\<p.*?\>', '[br]', result, flags=re.IGNORECASE)
    txt = re.sub('\<br.*?\>', '[br]', txt, flags=re.IGNORECASE)
    txt = re.sub('\<\/\s*p\s*?\>', '', txt, flags=re.IGNORECASE)
    txt = re.sub('\<\/\s*br\s*?\>', '', txt, flags=re.IGNORECASE)
    #txt = result.replace('<br>', '[br]').replace('</br>', '').replace('<p>', '[br]').replace('</p>', '').replace('<br />', '[br]')
    #txt = txt.replace('<BR>', '[br]').replace('</BR>', '').replace('<P>', '[br]').replace('</P>', '').replace('<BR />', '[br]')
    txt = txt.replace('&amp;#', '&#')
    txt = re.sub('&amp;(\w+?);','&\\1;',txt)
    logging.debug(">> replace with [br]")
    logging.debug(txt)
    soup = BeautifulSoup(txt, 'html.parser')
    #remove scripts
    [s.extract() for s in soup('script')]
    #remove facebook blocks
    for bq in soup('div'):
        if bq.has_attr('class') and bq['class'][0] in ('fb-post fb_iframe_widget'):
            bq.extract()
    return soup.get_text().replace('[br]', '\n')

  def loadJsonArticle1(self, url):
    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//div[@class="article__header"]//div[@class="post_news__date"]\'' #date
           ' --xpath \'//div[@class="article__header"]//h1[@class="post_news__title post_news__title_article"]\'' #title
           ' --xpath \'//div[@class="post post_news post_article"]//div[@class="post_news__text"]\'' #article text
           ' --xpath \'//div[@class="article__header"]//div[@class="post_news__author"]\'' #author
           ' --output-format=json-wrapped' #output as json
           ' --output-encoding=windows-1251')  #pravda.com.ua uses encoding=windows-1251
    #print('cmd: '+cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('windows-1251')
    #print('>>>>>>>>> loadJsonArticle1')
    #print(result)
    return json.loads(result)

  def loadJsonArticle2(self, url):
    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//div[@class="post post_news post_column"]//div[@class="post_news__date"]\'' #date
           ' --xpath \'//div[@class="post post_news post_column"]//h1[@class="post_news__title post_news__title_article"]\'' #title
           ' --xpath \'//div[@class="post post_news post_column"]//div[@class="post_news__text"]\'' #article text
           ' --xpath \'//div[@class="post post_news post_column"]//div[@class="post_news__author"]\'' #author
           ' --output-format=json-wrapped' #output as json
           ' --output-encoding=windows-1251')  #pravda.com.ua uses encoding=windows-1251
    #print('cmd: '+cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('windows-1251')
    #print('>>>>>>>>> loadJsonArticle2')
    #print(result)
    return json.loads(result)

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
    ret += '\n  <book-title>Українська правда. Новини ' + date.strftime('%d.%m.%Y') + '</book-title>'
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
    logging.basicConfig(filename='downloader_up_news.log',level=logging.INFO)
    date = datetime.datetime.strptime(sDateFrom, '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime(sDateTo, '%d.%m.%Y').date()

    while (date < dateTo):
      content = self.fb2(date)
      if len(content) > 0:
        with open(self.rootPath+'/pravda_com_ua/'+str(date.year)+'/up_news_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)
    logging.info("Job completed")


#run()
"""
#downloader.getNewsForDate('21.01.2011')
article = downloader.loadArticle('http://www.pravda.com.ua/rus/columns/2014/01/3/7008997/')
print(article.info())
#article = downloader.loadArticle('http://www.pravda.com.ua/news/2000/04/19/2980668/') #ukr text
#article = downloader.loadArticle('http://www.pravda.com.ua/articles/2012/11/22/6977980/') #rus text

#textStats = stats.TextStats(" ".join(article.body))
print(textStats.common_text_20)
if textStats.isUkr():
  print("this is Ukrainian text")
if textStats.isRus():
  print("this is Rusian text")
"""
