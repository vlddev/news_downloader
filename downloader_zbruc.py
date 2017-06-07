import sys, traceback
import datetime
import subprocess
import json
import logging
import re
from bs4 import BeautifulSoup
import downloader_common

def escapeXml(val):
  if val is not None and isinstance(val, str):
    txt = val.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\a', '')
    txt = txt.replace('[strong]', '<strong>').replace('[/strong]', '</strong>')
    return txt
  else:
    return val

class Article(object):
  def __init__(self, url, j):
    self.url = ''
    if url is not None:
      self.url = url

    self.dtStr = ''
    self.timeStr = '00:00'
    val = j[0]
    if val is not None:
      if isinstance(val, str):
        self.dtStr = val
      elif isinstance(val, list):
        self.dtStr = val[0]

    self.title = ''
    val = j[1]
    if val is not None:
      if isinstance(val, str):
        self.title = downloader_common.relpaceHtmlEntities(val)
      elif isinstance(val, list):
        self.title = downloader_common.relpaceHtmlEntities(val[0])
      if len(self.title) > 1000:
        self.title = self.title[:self.title.find('\n')] # get first line in long title

    self.source = ''
    val = j[2]
    if val is not None:
      if isinstance(val, str):
        self.source = val.strip()
      elif isinstance(val, list):
        self.source = val[0].strip()

    self.author = ''

    self.body = list()
    val = j[3]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        locText = val
      elif isinstance(val, list):
        locText = '\n'.join(val)

      #remove empty lines
      for line in locText.split('\n'):
        proLine = downloader_common.relpaceHtmlEntities(line.strip())
        if len(proLine) > 0:
          self.body.append(proLine)

    self.coltype = ''
    val = j[4]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        self.coltype = val
      elif isinstance(val, list):
        self.coltype = val[0].strip()

  def info(self):
    print('dtStr: '+self.dtStr);
    print('timeStr: '+self.timeStr);
    print('url: '+self.url);
    print('title: '+str(self.title));
    print('author: '+str(self.author));
    print('source: '+str(self.source));
    print('body: ' + "\n".join(self.body));

  def fb2(self):
    ret = '<section><title><p>' + escapeXml(self.title) + '</p></title>'
    if len(self.source) > 0:
      ret += '\n <p>' + self.source + '</p>'
    ret += '\n <p>url: ' + self.url + '</p>'
    ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret

class Downloader(object):

  def __init__(self, rootPath):
    self.baseUrl = 'http://zbruc.eu'
    self.getLinksCmd = downloader_common.XIDEL_CMD + 'xidel "{0}" --xpath \'//ol[@class="search-results node-results"]//li[@class="search-result"]//div[@class="title"]//@href\''
    self.getNextPageCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@class="item-list"]//li[@class="pager-next"]//@href\''
    self.downloadedUrls = set()
    self.rootPath = rootPath #'/home/vlad/Dokumente/python/news_lib'

    #xidel "http://zbruc.eu/search/node/04.06.1913" --xpath '//div[@class="archive_list"]//@href'

  def getNewsForDate(self, date):
    print('get news for ' + date.strftime('%d.%m.%Y'))
    articleList = list()
    pageNum = 0
    while True: #loop over pages
      url = self.baseUrl + '/search/node/'+date.strftime('%d.%m.%Y')+'?page='+str(pageNum)
      print('url: ' +url)
      # replace {0} with url
      cmd = self.getLinksCmd.format(url)
      #print('cmd: ' +cmd)
      p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
      for ln in p.stdout: #loop over all articles on page
        line = ln.decode('utf-8').strip()
        articleUrl = line
        if len(line) > 0 and line not in self.downloadedUrls:
          print ('load article: ' + line)
          try:
            article = self.loadArticle(articleUrl)
            if article is not None:
              msg = ''
              bAddToList = True
              # validate
              if date.strftime('%d.%m.%Y') != article.dtStr:
                bAddToList = False
                msg = 'IGNORE: Article date [%s] != queried date [%s]' % (article.dtStr, date.strftime('%d.%m.%Y'))
                logging.warning(msg+" URL: "+ articleUrl)
              if bAddToList and article.coltype in ('1913 зі старорусинів','1913 з поляків','1888 з поляків','1888 зі старорусинів','1938 з поляків'):
                bAddToList = False
                msg = 'IGNORE: Article with coltype [%s]' % (article.coltype)
                logging.warning(msg+" URL: "+ articleUrl)
              text = " ".join(article.body)
              text = text.strip()
              if bAddToList and len(text) == 0:
                msg = 'IGNORE: Article is empty.'
                bAddToList = False
                article.info()
                #sys.exit("Article is empty. URL: "+ line)
                logging.error(msg+" URL: "+ articleUrl)
              if bAddToList:
                if len(article.body) == 1 and len(text) > 1000:
                  logging.warning("Article (length = "+str(len(text))+") has one paragraph. URL: "+ articleUrl)
                articleList.append(article)
                self.downloadedUrls.add(line)
            else:
              #exit
              logging.error("Article can not be loaded from URL: "+ articleUrl)
              sys.exit("Article can not be loaded from URL: "+ articleUrl)
          except (SystemExit,KeyboardInterrupt):
            raise
          except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print ("Unexpected error: ", exc_type)
            traceback.print_exception(exc_type, exc_value, exc_traceback)
        else:
          print ('ignore url: '+ line)
      #end for (loop over all articles on page)
      #get link to the next page
      cmdPg = self.getNextPageCmd.format(url)
      #print('cmd: ' +cmdPg)
      pgList = list()
      pg = subprocess.Popen(cmdPg, shell=True, stdout=subprocess.PIPE)
      for ln in pg.stdout: #loop over all articles on page
        pgline = ln.decode('utf-8').strip()
        pgList.append(pgline)
      # check for next page
      #print('next page list: ' +str(pgList))
      pageNum += 1
      expectedNextPageLink = '/search/node/'+date.strftime('%d.%m.%Y')+'?page='+str(pageNum)
      #print('expected page: ' +expectedNextPageLink)
      if expectedNextPageLink not in pgList:
        break
    # end while (loop over pages)
    # order articles by time
    return articleList

  def loadArticle(self, url):
    #xidel "http://zbruc.eu/node/1332" -q --xpath '//div[@id="main_content"]//div[@class="field field-name-field-depeshi field-type-text-long field-label-hidden"]'

    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//div[@id="main_content"]//span[@class="date-display-single"]\'' #date
           ' --xpath \'//div[@id="main_content"]//div[@id="page-title"]\'' #title
           ' --xpath \'//div[@id="main_content"]//div[@class="field field-name-field-source-link field-type-link-field field-label-hidden"]\'' #source
           ' --xpath \'//div[@id="main_content"]//div[@class="field field-name-field-depeshi field-type-text-long field-label-hidden"]\'' #article text
           ' --xpath \'//div[@id="main_content"]//div[@class="field field-name-field-redakciia-istoria field-type-taxonomy-term-reference field-label-hidden"]\'' #coltype
           ' --output-format=json-wrapped') #output as json
    #print('cmd: '+cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    #print(result)
    jsonArt = json.loads(result)

    # load article text as html
    htmlCmd = (downloader_common.XIDEL_CMD.format(url) +
       ' --xpath \'//div[@id="main_content"]//div[@class="field field-name-field-depeshi field-type-text-long field-label-hidden" or '
       '           @class="field field-name-body field-type-text-with-summary field-label-hidden"]\'' #article text
       ' --output-format=html') #output as html
    jsonArt[3] = self.loadArticleTextFromHtml(htmlCmd)

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
    html = html.replace('<strong>', '[strong]').replace('</strong>', '[/strong]')
    logging.debug(">> replace with [br]")
    logging.debug(html)
    soup = BeautifulSoup(html, 'html.parser')
    #remove scripts
    [s.extract() for s in soup('script')]
    txt = soup.get_text()
    #if len(txt) > 1000 and txt.count('[br]') == 0:
    txt = txt.replace('[br]', '\n')
    logging.debug(">> parsed html")
    logging.debug(txt)
    return txt

  def fb2(self, date):
    today = datetime.date.today()
    url = self.baseUrl + '/search/node/'+date.strftime('%d.%m.%Y')
    articleList = self.getNewsForDate(date)
    if len(articleList) < 1:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Zbruč</last-name></author>'
    ret += '\n  <book-title>Zbruč. Новини ' + date.strftime('%d.%m.%Y') + '</book-title>'
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
    logging.basicConfig(filename='downloader_zbruc.log',level=logging.INFO,
            format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')
    date = datetime.datetime.strptime(sDateFrom, '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime(sDateTo, '%d.%m.%Y').date()

    dateList = []

    #for strDate in strDateList:
    #  dateList.append(datetime.datetime.strptime(strDate, '%Y-%m-%d').date())

    while (date < dateTo):
      dateList.append(date)
      date += datetime.timedelta(days=1)

    for date in dateList:
      content = self.fb2(date)
      if len(content) > 0:
        with open(self.rootPath+'/zbruc/'+str(date.year)+'/zbruc_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      else:
          print ('No articles for ' + date.strftime('%d.%m.%Y'))
          logging.warn('No articles for ' + date.strftime('%d.%m.%Y'))
      date += datetime.timedelta(days=1)
    logging.info("Job completed")
"""
downloader = Downloader()

logging.basicConfig(filename='downloader_zbruc.log',level=logging.INFO,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

strdate = '31.12.1890'
date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
dateTo = datetime.datetime.strptime('01.01.1892', '%d.%m.%Y').date()

strDateList = ['1888-12-31','1889-12-31']

dateList = []

for strDate in strDateList:
  dateList.append(datetime.datetime.strptime(strDate, '%Y-%m-%d').date())

while (date < dateTo):
  dateList.append(date)
  date += datetime.timedelta(days=1)


#print(dateList)

for date in dateList:
  content = downloader.fb2(date)
  if len(content) > 0:
    with open(str(date.year)+'/zbruc_'+str(date)+'.fb2', "w") as fb2_file:
      fb2_file.write(content)
  else:
      print ('No articles for ' + date.strftime('%d.%m.%Y'))


""
logging.basicConfig(filename='downloader_zbruc_debug.log',level=logging.DEBUG)
#downloader.getNewsForDate('21.01.2011')
article = downloader.loadArticle('http://zbruc.eu/node/1332')
print(article.info())
"""
