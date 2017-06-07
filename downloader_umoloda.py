import sys, traceback
import datetime
import subprocess
import json
import logging
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
    self.timeStr = '00:00'

    self.title = ''
    val = j[1]
    if val is not None:
      if isinstance(val, str):
        self.title = downloader_common.relpaceHtmlEntities(val)
      elif isinstance(val, list):
        self.title = downloader_common.relpaceHtmlEntities(val[0])

    self.summary = ''

    self.author = ''
    if len(j) > 3:
      val = j[3]
      if val is not None:
        self.author = val.strip()

    self.body = list()
    val = j[2]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        locText = val
      elif isinstance(val, list):
        locText = val[0]
      text = locText.strip() # trim

      if 'Друкована версія' in text:
        text = text[:text.find('Друкована версія')]

      if len(self.author) > 0:
        text = text.replace(self.author,'')

      #remove empty lines
      for line in text.split('\n'):
        proLine = downloader_common.relpaceHtmlEntities(line.strip())
        if len(proLine) > 0:
          self.body.append(proLine)

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
    #ret += '\n <p>' + self.timeStr + '</p>'
    ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + downloader_common.escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret

class Downloader(object):

  def __init__(self):
    self.baseUrl = 'http://www.umoloda.kiev.ua'
    self.getLinksCmd = downloader_common.XIDEL_CMD + ' --xpath \'//article[@class="post" or @class="mainArticle"]//h3//@href\''
    self.numDate = None

    #xidel "http://www.umoloda.kiev.ua/number/30/" --xpath '//article[@class="post" or @class="mainArticle"]//h3//@href'


  def getNewsForNumber(self, num):
    numUrl = '/number/%d/' % (num)
    url = self.baseUrl + numUrl
    print('url: ' +url)
    articleList = list()
    downloadedUrls = set()
    # replace {0} with url
    cmd = self.getLinksCmd.format(url)
    #print('cmd: ' +cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for ln in p.stdout:
      line = ln.decode('utf-8').strip()
      articleUrl = self.baseUrl + line
      if len(line) > 0 and line.startswith(numUrl) and line not in downloadedUrls:
        print ('load article: ' + line)
        try:
          article = self.loadArticle(articleUrl)
          if article is not None:
            bAddToList = True
            text = " ".join(article.body)
            text = text.strip()
            if len(text) > 0:
              bAddToList = True
            else:
              if line in ['/number/132/116/4298/','/number/134/116/4388/','/number/134/116/4420/']:
                bAddToList = False
                logging.error("IGNORE: Article is empty. URL: "+ articleUrl)
              else:
                bAddToList = False
                logging.error("Article is empty. URL: "+ line)
                article.info()
                #sys.exit("Article is empty. URL: "+ line)
                logging.error("IGNORE: Article is empty. URL: "+ articleUrl)
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
    return articleList

  def loadArticle(self, url):
    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//article[@class="mainArticle"]//div[@class="dateTime"]//span[@class="date"]\'' #date
           ' --xpath \'//article[@class="mainArticle"]//h1[@class="titleMain"]\'' #title
           ' --xpath \'//article[@class="mainArticle"]/div\'' #article text
           ' --xpath \'//article[@class="mainArticle"]//div[@class="author"]\'' #author
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
    return article

  """
    if len(article.body) <= 1 : #article has only one row, download as html
      logging.debug("article has only one row, download as html")
      text = " ".join(article.body)
      text = text.strip()
      if len(text) > 0: #article is not empty
        cmd = ('xidel '+url+' -q '
           ' --xpath \'//article[@class="mainArticle"]/div\'' #article text
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
  """

  def fb2(self, num):
    today = datetime.date.today()
    numUrl = '/number/%d/' % (num)
    url = self.baseUrl + numUrl
    articleList = self.getNewsForNumber(num)
    if len(articleList) < 1:
      return ''
    else:
      self.numDate = datetime.datetime.strptime(articleList[0].dtStr, '%d.%m.%Y').date()
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Україна Молода</last-name></author>'
    if self.numDate is not None:
      ret += '\n  <book-title>Україна Молода. № ' + str(num) + ' за ' + self.numDate.strftime('%d.%m.%Y') + '</book-title>'
      ret += '\n  <date>' + str(self.numDate) + '</date>'
    else:
      ret += '\n  <book-title>Україна Молода. № ' + str(num) + '</book-title>'
      ret += '\n  <date></date>'
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
        ret += '\n' + article.fb2()
      except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print ("Unexpected error: ", exc_type)
        traceback.print_exception(exc_type, exc_value, exc_traceback)
    ret += '\n</body>'
    ret += '\n</FictionBook>'
    return ret

downloader = Downloader()
#logging.basicConfig(filename='downloader_um_debug.log',level=logging.DEBUG)

logging.basicConfig(filename='downloader_um.log',level=logging.INFO,
            format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

num = 3132 #2016 -

while (num < 3170):
  content = downloader.fb2(num)
  if len(content) > 0:
    with open(downloader_common.rootPath+'/umoloda/'+str(downloader.numDate.year)+'/umoloda_'+str(num)+'.fb2', "w") as fb2_file:
      fb2_file.write(content)
  num += 1


"""
#downloader.getNewsForDate('21.01.2011')
article = downloader.loadArticle('http://www.telekritika.ua/verhovna-rada/2002-01-17/5098')
print(article.info())

textStats = stats.TextStats(" ".join(article.body))
print(textStats.common_text_20)
if textStats.isUkr():
  print("this is Ukrainian text")
if textStats.isRus():
  print("this is Rusian text")

"""
