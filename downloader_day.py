import pdb
import sys, traceback
import datetime
import subprocess
import json
import re
import logging
import os.path
from bs4 import BeautifulSoup
import stats
import downloader_common

class Article(object):
  def __init__(self, url, j):
    self.url = ''
    if url is not None:
      self.url = url

    self.dtStr = ''
    self.timeStr = '00:00'
    val = j[0]
    if val is not None:
      self.dtStr = val
      self.timeStr = val[-5:]

    self.title = ''
    val = j[1]
    if val is not None:
      if isinstance(val, str):
        self.title = downloader_common.relpaceHtmlEntities(val)
      elif isinstance(val, list):
        self.title = downloader_common.relpaceHtmlEntities(val[0])

    self.body = list()
    val = j[2]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        locText = val
      elif isinstance(val, list):
        locText = '\n'.join(val)
      text = locText.strip() # trim

      #remove HTML comments
      #text = re.sub("(<!--.*?-->)", "", text, flags=re.MULTILINE|re.DOTALL)

      #remove empty lines
      for line in text.split('\n'):
        proLine = downloader_common.relpaceHtmlEntities(line.strip())
        if len(proLine) > 0:
          self.body.append(proLine)

    self.summary = ''
    if len(j) > 3:
      val = j[3]
      if val is not None:
        self.summary = val.strip()

    self.author = ''
    if len(j) > 4:
      val = j[4]
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
    if len(self.summary) > 0:
      ret += '\n <p><strong>' + downloader_common.escapeXml(self.summary) + '</strong></p>'
    if len(self.author) > 0:
      ret += '\n <p>' + downloader_common.escapeXml(self.author) + '</p>'
    if '00:00' != self.timeStr:
      ret += '\n <p>' + self.timeStr + '</p>'
    ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + downloader_common.escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret

class Downloader(object):

  def __init__(self):
    self.baseUrl = 'https://day.kyiv.ua'
    self.getLinksCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@class="view-content"]//div[@class="taxrow"]//@href\''
    self.getNumDateCmd = downloader_common.XIDEL_CMD + ' --xpath \'(//div[@class="view-content"]//div[@class="taxrow"]//div[@class="date"])[1]\''
    self.numDate = None
    self.dict = {" січня, ":".01.", " лютого, ":".02.", " березня, ":".03.",
                 " квітня, ":".04.", " травня, ":".05.", " червня, ":".06.",
                 " липня, ":".07.", " серпня, ":".08.", " вересня, ":".09.",
                 " жовтня, ":".10.", " листопада, ":".11.", " грудня, ":".12."}

    #xidel "https://day.kyiv.ua/uk/arhiv/no35-1997?page=0" --xpath '//div[@class="view-content"]//div[@class="taxrow"]//@href'
    #xidel "https://day.kyiv.ua/uk/arhiv/no35-1997?page=0" --xpath '//div[@class="view-content"]//div[@class="taxrow"]//div[@class="date"]'


  def getNewsForNumber(self, num, year):
    self.numUrl = '/uk/arhiv/no%d-%d' % (num,year)
    url = self.baseUrl + self.numUrl + '?page=0'
    print('url: ' +url)
    articleList = list()
    downloadedUrls = set()

    cmd = self.getNumDateCmd.format(url)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    result = result[:10].strip() # date in format mm/dd/yyyy
    urlNum = 0
    while len(result) < 1 and urlNum < 3: #no such URL or no articles
        self.numUrl = '/uk/arhiv/no%d-%d-%d' % (num,year,urlNum)
        url = self.baseUrl + self.numUrl + '?page=0'
        print('url: ' +url)
        articleList = list()
        downloadedUrls = set()

        cmd = self.getNumDateCmd.format(url)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        result = p.communicate()[0].decode('utf-8')
        result = result[:10].strip() # date in format mm/dd/yyyy
        urlNum += 1
    #several nums in one newspaper
    deltaNum = 1
    while len(result) < 1 and deltaNum < 3: #no such URL or no articles
        self.numUrl = '/uk/arhiv/no%d-%d-%d' % (num,num+deltaNum,year)
        url = self.baseUrl + self.numUrl + '?page=0'
        print('url: ' +url)
        articleList = list()
        downloadedUrls = set()

        cmd = self.getNumDateCmd.format(url)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        result = p.communicate()[0].decode('utf-8')
        result = result[:10].strip() # date in format mm/dd/yyyy
        deltaNum += 1
    if len(result) < 1: #no such URL or no articles
        return None
    # get date from result
    self.numDate = datetime.datetime.strptime(result, '%m/%d/%Y').date()

    for pageNum in range(0, 3):
        # replace {0} with url
        url = self.baseUrl + self.numUrl + '?page='+str(pageNum)
        cmd = self.getLinksCmd.format(url)
        print('url: ' +url)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        for ln in p.stdout:
          line = ln.decode('utf-8').strip()
          articleUrl = self.baseUrl + line
          if articleUrl not in downloadedUrls:
            print ('load article: ' + articleUrl)
            try:
              while True:
                  retry = False
                  article = self.loadArticle(articleUrl)
                  if article is not None:
                    bAddToList = True
                    text = " ".join(article.body)
                    text = text.strip()
                    if len(text) > 0:
                      bAddToList = True
                    else:
                      if line in ['']:
                        bAddToList = False
                        logging.error("IGNORE: Article is empty. URL: "+ articleUrl)
                      else:
                        bAddToList = False
                        logging.error("Article is empty. URL: "+ articleUrl)
                        article.info()
                        #sys.exit("Article is empty. URL: "+ line)
                        logging.error("IGNORE: Article is empty. URL: "+ articleUrl)
                    if bAddToList:
                      if len(article.body) == 1:
                        logging.warning("Article (length = "+str(len(text))+") has one paragraph. URL: "+ articleUrl)
                      logging.debug("Article added to list. URL: "+ articleUrl)
                      articleList.append(article)
                      downloadedUrls.add(articleUrl)
                  else:
                    #exit
                    logging.warning("Article can not be loaded from URL: "+ articleUrl)
                    #try to fix url
                  if not retry :
                    break
            except (SystemExit, KeyboardInterrupt):
              raise
            except:
              exc_type, exc_value, exc_traceback = sys.exc_info()
              print ("Unexpected error: ", exc_type)
              traceback.print_exception(exc_type, exc_value, exc_traceback)
          else:
              print ('ignore url (already loaded): '+ articleUrl)
    #articleList.reverse()
    return sorted(articleList, key=lambda x: x.timeStr)

  def getNewsForUrl(self, noUrlPart):
    self.numUrl = '/uk/arhiv/%s' % (noUrlPart)
    url = self.baseUrl + self.numUrl + '?page=0'
    print('url: ' +url)
    articleList = list()
    downloadedUrls = set()

    cmd = self.getNumDateCmd.format(url)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    result = result[:10].strip() # date in format mm/dd/yyyy
    if len(result) < 1: #no such URL or no articles
        return None
    # get date from result
    self.numDate = datetime.datetime.strptime(result, '%m/%d/%Y').date()

    for pageNum in range(0, 3):
        # replace {0} with url
        url = self.baseUrl + self.numUrl + '?page='+str(pageNum)
        cmd = self.getLinksCmd.format(url)
        print('url: ' +url)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        for ln in p.stdout:
          line = ln.decode('utf-8').strip()
          articleUrl = self.baseUrl + line
          if articleUrl not in downloadedUrls:
            print ('load article: ' + articleUrl)
            try:
              while True:
                  retry = False
                  article = self.loadArticle(articleUrl)
                  if article is not None:
                    bAddToList = True
                    text = " ".join(article.body)
                    text = text.strip()
                    if len(text) > 0:
                      bAddToList = True
                    else:
                      if line in ['']:
                        bAddToList = False
                        logging.error("IGNORE: Article is empty. URL: "+ articleUrl)
                      else:
                        bAddToList = False
                        logging.error("Article is empty. URL: "+ articleUrl)
                        article.info()
                        #sys.exit("Article is empty. URL: "+ line)
                        logging.error("IGNORE: Article is empty. URL: "+ articleUrl)
                    if bAddToList:
                      if len(article.body) == 1:
                        logging.warning("Article (length = "+str(len(text))+") has one paragraph. URL: "+ articleUrl)
                      logging.debug("Article added to list. URL: "+ articleUrl)
                      articleList.append(article)
                      downloadedUrls.add(articleUrl)
                  else:
                    #exit
                    logging.warning("Article can not be loaded from URL: "+ articleUrl)
                    #try to fix url
                  if not retry :
                    break
            except (SystemExit, KeyboardInterrupt):
              raise
            except:
              exc_type, exc_value, exc_traceback = sys.exc_info()
              print ("Unexpected error: ", exc_type)
              traceback.print_exception(exc_type, exc_value, exc_traceback)
          else:
              print ('ignore url (already loaded): '+ articleUrl)
    articleList.reverse()
    return articleList

  def loadArticle(self, url):
    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//div[@class="pagetop"]//div[@class="node_date"]\'' #date time
           ' --xpath \'//h1[@class="title"]\'' #title
           ' --xpath \'//div[@class="pagetop"]//div[@class="field field-name-body field-type-text-with-summary field-label-hidden"]//div[@class="field-item even"]/p\'' #article text
           ' --xpath \'//div[@class="pagetop"]//div[@class="field field-name-field-subtitle field-type-text field-label-hidden"]\'' #article summary
           ' --xpath \'//div[@class="pagetop"]//div[@class="field field-name-field-op-author field-type-node-reference field-label-hidden"]\'' #author
           ' --output-format=json-wrapped') #output as json

    #xidel https://day.kyiv.ua/uk/article/cuspilstvo/pidlitkove-zlochinne-ugrupovannya-zatrimano-na-volini -q --xpath '//div[@class="pagetop"]//div[@class="node_date"]'
    #xidel https://day.kyiv.ua/uk/article/den-ukrayini-14 -q --xpath '//div[@class="pagetop"]//div[@class="field field-name-field-op-author field-type-node-reference field-label-hidden"]'
    #xidel https://day.kyiv.ua/uk/article/den-ukrayini-14 -q --xpath '//div[@class="pagetop"]//div[@class="field field-name-body field-type-text-with-summary field-label-hidden"]//div[@class="field-item even"]/p'
    #print('cmd: '+cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    jsonArt = json.loads(result)

    article = None
    try:
      if len(jsonArt) > 0 :
        text = ''
        if jsonArt[2] is not None :
            text = " ".join(jsonArt[2])
            text = text.strip()
        if len(text) == 0:
            #load as html
            cmdContent = (downloader_common.XIDEL_CMD.format(url) +
                   #' --xpath \'//div[@class="pagetop"]//div[@class="field field-name-body field-type-text-with-summary field-label-hidden"]//div[@class="field-item even"]\'' #article text
                   ' --xpath \'//div[@class="pagetop"]//div[@class="field-items"]\'' #article text
                   ' --output-format=html') #output as html
            jsonArt[2] = self.loadArticleTextFromHtml(cmdContent)
        article = Article(url, jsonArt)
      else:
        logging.warning("Nothing can be load from: "+url)
        print("Nothing can be load from: "+url)
        return None
    except:
      exc_type, exc_value, exc_traceback = sys.exc_info()
      print ("Unexpected error: ", exc_type, "In article ", result)
      traceback.print_exception(exc_type, exc_value, exc_traceback)
    #article.info()
    #print ("len(article.body) = " + str(len(article.body)))


    """
    if len(article.body) <= 2 : #article has only one row, download as html
      #xidel http://tyzhden.ua/Columns/50/6881 -q --xpath '//div[@class="bf3 ap1 _ga1_on_" or @class="bf3 ap2 _ga1_on_"]//div'
      print ("article has <= 2 row(s), reload it")
      logging.debug("article has<= 2 row(s), download as html")
      text = " ".join(article.body)
      text = text.strip()
      if len(text) > 0: #article is not empty
        cmd = ('xidel '+url+' -q '
           ' --xpath \'//div[@class="bf3 ap1 _ga1_on_" or @class="bf3 ap2 _ga1_on_"]//div | //div[@class="bf3 ap1 _ga1_on_" or @class="bf3 ap2 _ga1_on_"]//p\'') #article text
           #' --output-format=json-wrapped') #output as json
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        result = p.communicate()[0].decode('utf-8')
        if len(str(result).strip()) == 0 :
            cmd = ('xidel '+url+' -q '
               ' --xpath \'//div[@class="bf3 ap1 _ga1_on_" or @class="bf3 ap2 _ga1_on_"]\'') #article text
               #' --output-format=json-wrapped') #output as json
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            result = p.communicate()[0].decode('utf-8')
        logging.debug("new content len:" + str(len(str(result).strip())))
        logging.debug("new content:" + str(result))
        jsonArt[2] = result

        article2 = None
        try:
          if len(jsonArt) > 0 :
            article2 = Article(url, jsonArt)
          else:
            logging.warning("Nothing can be load from: "+url)
            print("Nothing can be load from: "+url)
        except:
          exc_type, exc_value, exc_traceback = sys.exc_info()
          print ("Unexpected error: ", exc_type, "In article ", result)
          traceback.print_exception(exc_type, exc_value, exc_traceback)

        if article2 is not None and len(article.body) < len(article2.body):
          return article2
    """
    return article

  def loadArticleTextFromHtml(self, xidelCmd):
    p = subprocess.Popen(xidelCmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    logging.debug(">> loadArticleTextFromHtml()")
    logging.debug(result)
    #print(result)
    txt = result.replace('<br>', '[br]').replace('</br>', '').replace('<p>', '[br]').replace('</p>', '').replace('<br />', '[br]')
    txt = txt.replace('<BR>', '[br]').replace('</BR>', '').replace('<P>', '[br]').replace('</P>', '').replace('<BR />', '[br]')
    txt = txt.replace('&amp;#', '&#')
    logging.debug(">> replace with [br]")
    logging.debug(txt)
    soup = BeautifulSoup(txt, 'html.parser')
    #remove scripts
    [s.extract() for s in soup('script')]
    logging.debug(">> soap.text")
    logging.debug(soup.get_text())
    return soup.get_text().replace('[br]', '\n')

  def fb2ForUrl(self, noUrlPart):
    today = datetime.date.today()
    self.numUrl = '/uk/arhiv/%s' % (noUrlPart)
    articleList = self.getNewsForUrl(noUrlPart)
    url = self.baseUrl + self.numUrl
    if articleList is None:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Газета «День»</last-name></author>'
    if self.numDate is not None:
      ret += '\n  <book-title>Газета «День» № ' + noUrlPart + ' від ' + self.numDate.strftime('%d.%m.%Y') + '</book-title>'
      ret += '\n  <date>' + str(self.numDate) + '</date>'
    else:
      ret += '\n  <book-title>Газета «День» № ' + noUrlPart + '</book-title>'
      ret += '\n  <date></date>'
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

  def fb2(self, num, year):
    today = datetime.date.today()
    self.numUrl = '/uk/arhiv/no%d-%d' % (num, year)
    articleList = self.getNewsForNumber(num, year)
    url = self.baseUrl + self.numUrl
    if articleList is None:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Газета «День»</last-name></author>'
    if self.numDate is not None:
      ret += '\n  <book-title>Газета «День» № ' + str(num) + ' від ' + self.numDate.strftime('%d.%m.%Y') + '</book-title>'
      ret += '\n  <date>' + str(self.numDate) + '</date>'
    else:
      ret += '\n  <book-title>Газета «День» № ' + str(num) + ', ' + str(year) + '</book-title>'
      ret += '\n  <date></date>'
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

def run():
    downloader = Downloader()

    #2017 40 95
    year = int(sys.argv[1])
    num = int(sys.argv[2]) #2016 -
    lastNum = int(sys.argv[3])+1

    #while (num < lastNum): #253
    #    strNumList.append(str(num))
    #    num += 1

    #strNumList = ['238-240','235-236','230-231','225-226','220-221','215-216','210-211','205-206','200-201','195-196','190-191','185-186',
    #    '181-182','176-177','171-172','166-167','161-162','156-157','151-152','148-149','143-144','138-139','133-134']

    logging.basicConfig(filename='downloader_day_'+str(year)+'.log',level=logging.INFO,
            format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    #for num in strNumList
    while (num < lastNum): #253
      try:
        fname = ("%d/day_%03d.fb2" % (year, num))
        if os.path.isfile(fname):
            print ("File %s exists, get next." % fname)
        else:
            content = downloader.fb2(num, year)
            if len(content) > 0:
                with open((downloader_common.rootPath+'/day/'+"%d/day_%03d.fb2" % (year, num)), "w") as fb2_file:
                    fb2_file.write(content)
            else:
                print("No content for num %d, year %d." % (num, year))
                logging.warning("No content for num %d, year %d." % (num, year))
      except KeyboardInterrupt:
        sys.exit("Download interrrupted.")
      except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        sys.exit("Unexpected error:  "+ exc_type)
      num += 1

def runUrl():
    downloader = Downloader()

    logging.basicConfig(filename='downloader_day.log',level=logging.INFO,
            format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    noUrlPart = 'no65-2016-0'
    content = downloader.fb2ForUrl(noUrlPart)
    if len(content) > 0:
        with open(("2017/%s.fb2" % (noUrlPart)), "w") as fb2_file:
            fb2_file.write(content)
    else:
        print("No content for num %d, year %d." % (num, year))
        logging.warning("No content for num %d, year %d." % (num, year))

run()

"""
logging.basicConfig(filename='downloader_day_debug.log',level=logging.DEBUG)
#downloader.getNewsForNumber(35,1997)
article = downloader.loadArticle('https://day.kyiv.ua/uk/article/media/mafiya-bezsmertna-y-na-ekrani')
print(article.info())
"""
