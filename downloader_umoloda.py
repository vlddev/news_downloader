import sys, traceback
import os
import os.path
import datetime
import subprocess
import json
import logging
from bs4 import BeautifulSoup
import stats
import downloader_common


def run():
  downloader = Downloader()

  logging.basicConfig(filename='downloader_um.log', level=logging.INFO,
          format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')
  downloader.load()
"""
  # get last downloaded number
  num = downloader.getLastDownloadedIssueNr() + 1

  # get current issue number (https://dt.ua/gazeta/issue/1129)
  currentIssueNum = downloader.getCurrentIssueNr()
  print ("download issues from {0} to {1}".format(num, currentIssueNum))
  logging.info("download issues from {0} to {1}".format(num, currentIssueNum))

  while (num <= currentIssueNum):
      content = downloader.fb2(num)
      if len(content) > 0:
          with open(downloader_common.rootPath+'/umoloda/'+str(downloader.numDate.year)+'/umoloda_'+str(num)+'.fb2', "w") as fb2_file:
              fb2_file.write(content)
      num += 1
"""

def test():
    downloader = Downloader()

    logging.basicConfig(filename='downloader_um.log', level=logging.DEBUG,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    article = downloader.loadArticle('http://www.telekritika.ua/verhovna-rada/2002-01-17/5098')
    print(article.info())

class Article(downloader_common.BaseArticle):
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

"""
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
"""

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

  def getCurrentIssueNr(self):
    curIssueNr = -1
    url = self.baseUrl
    curIssueCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@id="main"]//div[@class="col-xs-12 col-sm-6 col-md-3 rightsidebarBanner"]//div[@class="titlePdf"]//a/@href\''
    cmd = curIssueCmd.format(url)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for ln in p.stdout:
      line = ln.decode('utf-8').strip()
      if len(line) > 0 and line.startswith('/number/'):
          curIssueNr = int(''.join(ele for ele in line if ele.isdigit())) - 1

    return curIssueNr

  def getLastDownloadedIssueNr(self):
    now = datetime.datetime.now()
    curYearFolder = downloader_common.rootPath+'/umoloda/'+str(now.year)
    prevYearFolder = downloader_common.rootPath+'/umoloda/'+str(now.year-1)
    lastIssueFolder = downloader_common.rootPath+'/umoloda'
    if os.path.isdir(curYearFolder) and len(os.listdir(curYearFolder)) > 0: # folder for current year exists
      lastIssueFolder = curYearFolder
      if len(os.listdir(lastIssueFolder)) == 0: # folder for current year is empty
        lastIssueFolder = prevYearFolder
    elif os.path.isdir(prevYearFolder) and len(os.listdir(prevYearFolder)) > 0: # folder for previous year exists:
      lastIssueFolder = prevYearFolder
    else:
      return 0

    lastIssueNr = 0
    for issueFile in os.listdir(lastIssueFolder):
      if issueFile.endswith(".fb2"):
        curIssueNr = int(''.join(ele for ele in issueFile[:-3] if ele.isdigit()))
        if curIssueNr > lastIssueNr:
          lastIssueNr = curIssueNr

    return lastIssueNr

  def load(self):
    # get last downloaded number
    num = self.getLastDownloadedIssueNr() + 1

    currentIssueNum = self.getCurrentIssueNr()
    print ("download issues from {0} to {1}".format(num, currentIssueNum))
    logging.info("download issues from {0} to {1}".format(num, currentIssueNum))

    now = datetime.datetime.now()
    year = now.year

    # for num in strNumList
    while (num <= currentIssueNum):
      try:
        content = self.fb2(num)
        if len(content) > 0:
            with open((downloader_common.rootPath+'/umoloda/'+"%d/umoloda_%03d.fb2" % (year, num)), "w") as fb2_file:
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
    logging.info("Job completed")


if __name__ == '__main__':
    run()
