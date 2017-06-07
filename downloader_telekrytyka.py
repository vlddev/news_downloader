import sys, traceback
import datetime
import subprocess
import json
import logging
import re
from bs4 import BeautifulSoup
import stats
import downloader_common

class Article(object):
  def __init__(self, url, j):
    self.url = ''
    if url is not None:
      self.url = url

    self.dtStr = ''
    val = j[0]
    if val is not None:
      self.dtStr = val
    if  len(self.dtStr) > 4:
      self.timeStr = self.dtStr[-5:] # extract time (last five char)
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

    self.body = list()
    val = j[2]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        locText = val
      elif isinstance(val, list):
        locText = val[0]
      text = locText.strip() # trim

      # remove html comments
      text = re.subn("(<!--.*?-->)", "", text, flags=re.MULTILINE|re.DOTALL)[0]

      if 'Версія для друку' in text:
        text = text[:text.find('Версія для друку')]

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

  def __init__(self):
    self.baseUrl = 'http://old.telekritika.ua'
    self.getLinksCmd = 'xidel "{0}" --xpath \'//div[@class="news authorsarch"]//a[@target="_top"]/@href\' -q'

    #xidel "http://www.telekritika.ua/archivedate.php?AYear=2001&AMonth=10&ADay=10" --xpath '//div[@class="news authorsarch"]//a[@target="_top"]/@href'


  def getNewsForDate(self, date):
    print('get news for ' + date.strftime('%d.%m.%Y'))
    url = self.baseUrl + '/archivedate.php?AYear='+str(date.year)+'&AMonth='+str(date.month)+'&ADay='+str(date.day)
    print('url: ' +url)
    articleList = list()
    downloadedUrls = set()
    # replace {0} with url
    cmd = self.getLinksCmd.format(url)
    #print('cmd: ' +cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for ln in p.stdout:
      line = ln.decode('utf-8').strip()
      if len(line) > 0 and line.startswith(self.baseUrl) and line not in downloadedUrls:
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
              elif not (textStats.isUkr() or textStats.isRus() or textStats.isEng()):
                if textStats.hasRusLetter():
                  bAddToList = False
                  logging.warning("IGNORE: Article (language not detected) has Rus letters. URL: "+ line)
                elif len(text) < 450: #ignore article
                  bAddToList = False
                  logging.warning("IGNORE: Article language not detected. URL: "+ line)
                  logging.info("   text length: "+ str(len(text)))
                  logging.info("   stats: "+str(textStats.common_text_20))
                elif textStats.hasUkrLetter():
                  bAddToList = True
                else:
                  logging.error("Article language not detected. URL: "+ line)
                  logging.info("   text length: "+ str(len(text)))
                  logging.info("   stats: "+str(textStats.common_text_20))
                  bAddToList = False
                  #sys.exit("Article language not detected. URL: "+ line)
            else:
              if line in ['http://www.telekritika.ua/knigi-tk/2009-06-17/46263','http://www.telekritika.ua/medialiteracy/2010-10-01/56304',
                          'http://www.telekritika.ua/medialiteracy/2010-10-07/56435','http://www.telekritika.ua/notices/2010-10-08/56475',
                          'http://www.telekritika.ua/medialiteracy/2010-10-12/56540','http://www.telekritika.ua/tel/2010-10-22/56827',
                          'http://www.telekritika.ua/news/2010-11-05/57249', 'http://www.telekritika.ua/news/2010-11-08/57319',
                          'http://www.telekritika.ua/tel/2010-11-22/57742', 'http://www.telekritika.ua/profesiya/2010-11-29/57931']:
                bAddToList = False
                logging.error("IGNORE: Article is empty. URL: "+ line)
              elif len(article.timeStr) > 0 and len(article.title) > 0:
                bAddToList = False
                logging.error("IGNORE: Empty article with title and time. URL: "+ line)
              else:
                bAddToList = False
                logging.error("Article is empty. URL: "+ line)
                article.info()
                #sys.exit("Article is empty. URL: "+ line)
            if bAddToList:
              if len(article.body) == 1:
                logging.warning("Article (length = "+str(len(text))+") has one paragraph. URL: "+ line)
              articleList.append(article)
              downloadedUrls.add(line)
          else:
            #exit
            logging.error("Article can not be loaded from URL: "+ line)
            sys.exit("Article can not be loaded from URL: "+ line)
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
    cmd = ('xidel '+url+' -q '
           ' --xpath \'//div[@class="article"]//div[@class="art_date"]\'' #date
           ' --xpath \'//div[@class="article"]//div[@class="art_title"]\'' #title
           ' --xpath \'//div[@class="article"]//div[@class="art_content"]\'' #article text
           ' --output-format=json-wrapped') #output as json
    #print('cmd: '+cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    #print(result)
    jsonArt = json.loads(result)

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
      if len(text) > 0: #article is not empty
        cmd = ('xidel '+url+' -q '
           ' --xpath \'//div[@class="article"]//div[@class="art_content"]\'' #article text
           ' --output-format=html') #output as html
        jsonArt[2] = self.loadArticleTextFromHtml(cmd)

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
    logging.debug(">> replace with [br]")
    logging.debug(html)
    soup = BeautifulSoup(html, 'html.parser')
    txt = soup.get_text()
    #if len(txt) > 1000 and txt.count('[br]') == 0:
    return txt.replace('[br]', '\n')

  def loadJsonArticle1(self, url):
    cmd = ('xidel '+url+' -q '
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
    cmd = ('xidel '+url+' -q '
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
    url = self.baseUrl + '/archivedate.php?AYear='+str(date.year)+'&AMonth='+str(date.month)+'&ADay='+str(date.day)
    articleList = self.getNewsForDate(date)
    if len(articleList) < 1:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Телекритика</last-name></author>'
    ret += '\n  <book-title>Телекритика. Новини ' + date.strftime('%d.%m.%Y') + '</book-title>'
    ret += '\n  <date>' + str(date) + '</date>'
    ret += '\n  <lang>uk</lang>'
    ret += '\n </title-info>'
    ret += '\n <document-info>'
    ret += '\n  <author><nickname>V.Vlad</nickname></author>'
    ret += '\n  <date value="' + str(today) + '">' + str(today) + '</date>'
    ret += '\n  <version>1.0</version>'
    ret += '\n  <src-url>' + url.replace('&', '&amp;') + '</src-url>'
    ret += '\n </document-info>'
    ret += '\n</description>'
    ret += '\n<body>'
    for article in articleList:
      try:
        if 'тексти новин телеканалів' not in article.title.lower():
          ret += '\n' + article.fb2()
      except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print ("Unexpected error: ", exc_type)
        traceback.print_exception(exc_type, exc_value, exc_traceback)
    ret += '\n</body>'
    ret += '\n</FictionBook>'
    return ret

  def fb2TeleNews(self, date):
    today = datetime.date.today()
    url = self.baseUrl + '/archivedate.php?AYear='+str(date.year)+'&AMonth='+str(date.month)+'&ADay='+str(date.day)
    articleList = self.getNewsForDate(date)
    hasTeleNews = False
    for article in articleList:
      if 'тексти новин телеканалів' in article.title.lower():
        hasTeleNews = True
        break
    if not hasTeleNews:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Телекритика</last-name></author>'
    ret += '\n  <book-title>Телекритика. Тексти новин телеканалів: ' + date.strftime('%d.%m.%Y') + '</book-title>'
    ret += '\n  <date>' + str(date) + '</date>'
    ret += '\n  <lang>uk</lang>'
    ret += '\n </title-info>'
    ret += '\n <document-info>'
    ret += '\n  <author><nickname>V.Vlad</nickname></author>'
    ret += '\n  <date value="' + str(today) + '">' + str(today) + '</date>'
    ret += '\n  <version>1.0</version>'
    ret += '\n  <src-url>' + url.replace('&', '&amp;') + '</src-url>'
    ret += '\n </document-info>'
    ret += '\n</description>'
    ret += '\n<body>'
    for article in articleList:
      try:
        if 'тексти новин телеканалів' in article.title.lower():
          ret += '\n' + article.fb2()
      except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print ("Unexpected error: ", exc_type)
        traceback.print_exception(exc_type, exc_value, exc_traceback)
    ret += '\n</body>'
    ret += '\n</FictionBook>'
    return ret

downloader = Downloader()
#logging.basicConfig(filename='downloader_tk_debug.log',level=logging.DEBUG)

logging.basicConfig(filename='downloader_tk.log',level=logging.INFO)


strdate = '31.10.2016'
date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
dateTo = datetime.datetime.strptime('01.01.2017', '%d.%m.%Y').date()

#strDateList = ['2007-02-04','2007-02-06','2007-02-07','2007-02-15','2007-05-15','2007-05-16','2007-06-27','2007-07-06','2007-07-18'
#              ,'2007-08-15','2007-08-20','2007-09-03','2007-11-14','2007-11-20', '']

dateList = []

while (date < dateTo):
  dateList.append(date)
  date += datetime.timedelta(days=1)

"""
for strDate in strDateList:
  dateList.append(datetime.datetime.strptime(strDate, '%Y-%m-%d').date())
"""

#print(dateList)

for date in dateList:
  content = downloader.fb2(date)
  if len(content) > 0:
    with open('telekritika/'+str(date.year)+'/telekrytyka_'+str(date)+'.fb2', "w") as fb2_file:
      fb2_file.write(content)
  content = downloader.fb2TeleNews(date)
  if len(content) > 0:
    with open('telekritika/'+str(date.year)+'/telekrytyka_tvnews_'+str(date)+'.fb2', "w") as fb2_file:
      fb2_file.write(content)

"""
#downloader.getNewsForDate('21.01.2011')
article = downloader.loadArticle('http://www.telekritika.ua/news/2008-12-12/42616')
print(article.info())

textStats = stats.TextStats(" ".join(article.body))
print(textStats.common_text_20)
if textStats.isUkr():
  print("this is Ukrainian text")
if textStats.isRus():
  print("this is Rusian text")

"""
