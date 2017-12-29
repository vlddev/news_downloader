import sys
import datetime
import subprocess
import json
import logging
from bs4 import BeautifulSoup
import re
import time
import downloader_common

# TODO fix xpath, remove script, reload  2014 - 2016

class Article(object):
  def __init__(self, url, j):
    self.url = ''
    if url is not None:
      self.url = url

    self.dtStr = ''
    if j[0] is not None:
      self.dtStr = j[0]
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
        self.summary = downloader_common.relpaceHtmlEntities(val).strip()
      elif isinstance(val, list):
        self.summary = downloader_common.relpaceHtmlEntities(' '.join(val)).strip()

    self.body = list()
    val = None
    if len(j) > 3:
      val = j[3]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        locText = val
      elif isinstance(val, list):
        for line in val:
            if 'За матеріалами:' in line:
                line = line.replace('\n','')
                line = ' '.join(line.split()) #substitute multiple whitespace with single whitespace
                line = '@@@ '+line
            locText = locText + '\n' + line

      if len(self.summary) > 0 and len(locText) > 0:
        text = locText.replace(self.summary,'',1).strip() # remove summary from the body, trim
      else:
        #no summary
        text = locText.strip() # trim

      #remove empty lines
      for line in text.split('\n'):
        proLine = line.strip()
        if len(proLine) > 0:
          self.body.append(downloader_common.relpaceHtmlEntities(proLine))

  def info(self):
    print('dtStr: '+self.dtStr);
    print('timeStr: '+self.timeStr);
    print('url: '+self.url);
    print('title: '+str(self.title));
    print('summary: '+str(self.summary));
    print('body: ' + "\n".join(self.body));

  def fb2(self):
    ret = '<section><title><p>' + downloader_common.escapeXml(self.title) + '</p></title>'
    ret += '\n <p>' + self.timeStr + '</p>'
    ret += '\n <p><strong>' + downloader_common.escapeXml(self.summary) + '</strong></p>'
    ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + downloader_common.escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret

class Downloader(object):

  def __init__(self, rootPath):
    self.baseUrl = 'http://dt.ua'
    self.getLinksCmd = downloader_common.XIDEL_CMD + ' --xpath \'//a/@href\''
    self.rootPath = rootPath

  def getNewsForDate(self, date):
    print('get news for %d.%d.%d' % (date.day, date.month, date.year))
    url = self.baseUrl + '/sitemap/text/%d/%d/%d/index.html' % (date.year, date.month, date.day)
    print('[%d.%d.%d] ' % (date.day, date.month, date.year) + 'url: ' +url)
    # replace {0} with url
    articleList = list()
    cmd = self.getLinksCmd.format(url)
    #print('cmd: ' +cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for ln in p.stdout:
      line = ln.decode('utf-8').strip()
      if len(line) > 0 and not line.startswith('/sitemap/text'):
        try:
          retryCount = 0
          while True:
              print ('[%d.%d.%d] ' % (date.day, date.month, date.year) + 'load article: '+self.baseUrl + line)
              article = self.loadArticle(self.baseUrl + line)
              if article is not None:
                  if isinstance(article, str):
                      if article == 'reload':
                          # reload article
                          if retryCount > 4:
                              #exit
                              sys.exit("Timeout: Article can not be loaded from URL: "+self.baseUrl + line)
                          retryCount += 1
                          print ('[%d.%d.%d] ' % (date.day, date.month, date.year) + 'Timeout, try to reload article. RetryCount = '+str(retryCount))
                          continue
                  elif isinstance(article, Article):
                      articleList.append(article)
                      break
                  else:
                      #exit
                      sys.exit("Unknown article type : "+str(article))
              else:
                  #exit
                  sys.exit("Article can not be loaded from URL: "+self.baseUrl + line)
        except (SystemExit, KeyboardInterrupt):
          raise
        except:
          exc_type, exc_value, exc_traceback = sys.exc_info()
          print ("Unexpected error: ", exc_type)
          traceback.print_exception(exc_type, exc_value, exc_traceback)
    # order articles by time
    return sorted(articleList, key=lambda x: x.timeStr)

  def loadArticle(self, url):
    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//div[@class="central_article"]//div[@class="date"]\'' #date
           ' --xpath \'//div[@class="central_article"]//h1[@class="title"]/text()\'' #title
           ' --xpath \'//div[@class="central_article"]//div[@class="article_body"]//div[@class="summary"]\'' #summary
           ' --xpath \'//div[@class="central_article"]//div[@class="article_body_dummy"]\'' #empty text
           ' --output-format=json-wrapped') #output as json
    #print('cmd: '+cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    #print(result)
    jsonArt = json.loads(result)

    if len(jsonArt) < 3:
        print("result: "+str(result))
        logging.error("result: "+str(result))
        print("json: "+str(jsonArt))
        logging.error("json: "+str(jsonArt))
        # todo: if timeout, retry
        return 'reload'
    aTextCmd = (downloader_common.XIDEL_CMD.format(url) +
       ' --xpath \'//div[@class="central_article"]//div[@class="article_body"]/node()[not(self::script or self::div[@class="picture aright"]  or self::div[@class="fb-post fb_iframe_widget"])]\''
       ' --output-format=html') #output as html
    jsonArt[3] = self.loadArticleTextFromHtml(aTextCmd)

    article = None
    try:
      article = Article(url, jsonArt)
    except:
      print ("Unexpected error: ", sys.exc_info()[0], "In article ", result)
    #article.info()
    return article

  def loadArticleTextFromHtml(self, xidelCmd):
    p = subprocess.Popen(xidelCmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
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
    logging.debug(">> replace with [br]")
    logging.debug(txt)
    soup = BeautifulSoup(txt, 'html.parser')
    #remove scripts
    [s.extract() for s in soup('script')]
    #remove pics blocks
    for bq in soup('div'):
        if bq.has_attr('class') and bq['class'][0] in ('photo_content','g_box'):
            bq.extract()

    logging.debug(">> soap.text")
    logging.debug(soup.get_text())
    return soup.get_text().replace('[br]', '\n')

  def fb2(self, date):
    strdate = '%d.%d.%d' % (date.day, date.month, date.year)
    today = datetime.date.today()
    url = self.baseUrl + '/sitemap/text/%d/%d/%d/index.html' % (date.year, date.month, date.day)
    articleList = self.getNewsForDate(date)
    if len(articleList) < 1:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Дзеркало тижня</last-name></author>'
    ret += '\n  <book-title>Дзеркало тижня. Новини ' + strdate + '</book-title>'
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

  def load(self, sDateFrom, sDateTo):
    logging.basicConfig(filename='downloader_dt_news.log',level=logging.INFO)
    date = datetime.datetime.strptime(sDateFrom, '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime(sDateTo, '%d.%m.%Y').date()

    while (date < dateTo):
      content = self.fb2(date)
      if len(content) > 0:
        with open(self.rootPath+'/dt_news/'+str(date.year)+'/dt_news_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)
    logging.info("Job completed")

"""
def getFile(date, rootPath):
  downloader = Downloader()
  content = downloader.fb2(date)
  if len(content) > 0:
    with open(rootPath+'/dt_news/'+str(date.year)+'/dt_news_'+str(date)+'.fb2', "w") as fb2_file:
      fb2_file.write(content)


maxThreads = 6
logging.basicConfig(filename='downloader_dt_news.log',level=logging.INFO)

rootPath = '/home/vlad/Dokumente/python/news_lib'
strdate = '24.08.2014'
date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
dateTo = datetime.datetime.strptime('01.01.2017', '%d.%m.%Y').date()


while (date < dateTo):
  #wait until free thread
  while threading.active_count() > maxThreads :
      time.sleep(1)
  #downloader = Downloader()
  #content = downloader.fb2(date)
  #if len(content) > 0:
  #  with open(rootPath+'/dt_news/'+str(date.year)+'/dt_news_'+str(date)+'.fb2', "w") as fb2_file:
  #    fb2_file.write(content)
  job = threading.Thread(target=getFile, args=(date, rootPath))
  job.start()
  #job.join()
  date += datetime.timedelta(days=1)

#downloader.getNewsForDate('31.12.2014')
article = downloader.loadArticle('http://dt.ua/ECONOMICS/nacionalizaciya-privatbanku-v-fotozhabah-zanepokoyennya-pro-vkladi-chergi-bilya-bankomativ-i-podarunok-do-19-grudnya-227933_.html')
article.info()

#TODO check rest of javascript in dt_news_2015/dt_news_2015-12-21.fb2; dt_news_2015/dt_news_2015-09-30.fb2; check also news 2014
"""
