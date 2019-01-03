import sys
import traceback
import os
import os.path
import datetime
import subprocess
import json
import re
import logging
import downloader_common

#
# Завантажувач архіву газет "Дзеркало тижня"
# https://dt.ua/gazeta/archive/
# починаючи з "Дзеркало тижня. Україна" №22 10 ЧЕРВНЯ-16 ЧЕРВНЯ 2017 (https://dt.ua/gazeta/issue/1110)
#    номери газети до цієї дати завантажувалися за допомогою downloader_dtp.py
#

def run():
    downloader = Downloader()

    logging.basicConfig(filename='downloader_dt_gazeta.log',level=logging.INFO,
            format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    # get last downloaded number
    num = downloader.getLastDownloadedIssueNr() + 1

    # get current issue number (https://dt.ua/gazeta/issue/1129)
    currentIssueNum = downloader.getCurrentIssueNr()
    print ("download issues from {0} to {1}".format(num, currentIssueNum))
    logging.info("download issues from {0} to {1}".format(num, currentIssueNum))

    while (num <= currentIssueNum):
      content = downloader.fb2(num)
      if len(content) > 0:
        with open(downloader_common.rootPath+'/dt_gazeta/2018/dt_gazeta_'+str(num)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      num += 1

def test():
    downloader = Downloader()

    logging.basicConfig(filename='downloader_dt_gazeta_test.log',level=logging.INFO,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    article = downloader.loadArticle('http://gazeta.dt.ua/EDUCATION/ctatus-chi-viznannya-_.html')
    print(article.info())

class Article(object):
  def __init__(self, url, j):
    self.url = ''
    if url is not None:
      self.url = url

    self.dtStr = ''
    val = j[0]
    if val is not None:
      self.dtStr = val

    self.author = ''
    val = j[1]
    if val is not None:
      if isinstance(val, str):
        self.author = val
      elif isinstance(val, list):
        self.author = ', '.join(val)

    self.title = ''
    val = j[2]
    if val is not None:
      if isinstance(val, str):
        self.title = downloader_common.relpaceHtmlEntities(val)
    elif isinstance(val, list):
        self.title = downloader_common.relpaceHtmlEntities(val[0])

    self.summary = ''

    self.body = list()
    val = j[3]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        locText = val
      elif isinstance(val, list):
        locText = '\n'.join(val)

      text = locText.strip()

      #remove empty lines
      for line in text.split('\n'):
        proLine = downloader_common.relpaceHtmlEntities(line.strip())
        if len(proLine) > 0:
          self.body.append(proLine)

  def info(self):
    print('dtStr: '+self.dtStr)
    print('author: '+self.author)
    print('url: '+self.url)
    print('title: '+str(self.title))
    print('body: ' + "\n".join(self.body))

  def fb2(self):
    ret = '<section><title><p>' + downloader_common.escapeXml(self.title) + '</p></title>'
    if len(self.author) > 0:
      ret += '\n <p><strong>' + downloader_common.escapeXml(self.author) + '</strong></p>'
    ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + downloader_common.escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret

class Downloader(object):

  def __init__(self):
    self.baseUrl = 'https://dt.ua'
    self.baseUrl1 = '//dt.ua'
    self.getLinksCmd = downloader_common.XIDEL_CMD + ' --xpath \'//ul[@class="index_news_list wide issue active"]//a[@class="news_anounce"]/@href\''
    self.getTitleCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@class="issue_head"]/span[@class="right_text"]/span[@class="text_line"]\' --output-format=json-wrapped'
    self.replDict = {'января':'січня', 'февраля':'лютого', 'марта':'березня', 'апреля':'квітня', 'мая':'травня', 'июня':'червня', 'июля':'липня',
                     'августа':'серпня', 'сентября':'вересня', 'октября':'жовтня', 'ноября':'листопада', 'декабря':'грудня', 'Зміст':''}
    #xidel "https://dt.ua/gazeta/issue/1110" --xpath '//div[@class="issue_head"]/span[@class="right_text"]/span[@class="text_line"]'


  def getTitleForNumber(self, num):
    url = self.baseUrl + '/gazeta/issue/%d' % (num)
    # replace {0} with url
    cmd = self.getTitleCmd.format(url)
    #print('cmd: ' +cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    jsonRes = json.loads(result)
    title = 'Дзеркало тижня. Україна Nr %d' % (num)
    if jsonRes is not None and len(jsonRes) > 0:
      title = 'Дзеркало тижня. '+" ".join(jsonRes[0])
      # replace russian months
      pattern = re.compile(r'\b(' + '|'.join(self.replDict.keys()) + r')\b')
      title = pattern.sub(lambda x: self.replDict[x.group()], title)

    return title.strip()

  def getNewsForNumber(self, num):
    print('get news for %d' % (num))
    url = self.baseUrl + '/gazeta/issue/%d' % (num)
    print('url: ' +url)
    # replace {0} with url
    articleList = list()
    cmd = self.getLinksCmd.format(url)
    # print('cmd: ' +cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for ln in p.stdout:
      line = ln.decode('utf-8').strip()
      if len(line) > 0 and (line.startswith('/')) and not line.startswith(self.baseUrl+'/sitemap'):
        line = self.baseUrl+line
        print ('load article: '+line)
        try:
          article = self.loadArticle(line)
          if article is not None:
            articleList.append(article)
          else:
            #exit
            sys.exit("Article can not be loaded from URL: "+ line)
        except SystemExit:
          raise
        except:
          print ("Unexpected error: ", sys.exc_info()[0])
    return articleList

  def loadArticle(self, url):
    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//div[@class="central_article"]//span[@class="date"]\'' #date and time
           ' --xpath \'//div[@class="central_article"]//ul[@class="auth_list"]//span[@class="name"]\'' #author(s)
           ' --xpath \'//div[@class="central_article"]//h1[@class="title"]/text()[1]\'' #title
           ' --xpath \'//div[@class="article_body"]//div[@class="text"]/node()[not(self::script)]\'' #text
           ' --output-format=json-wrapped') #output as json
    #xidel "https://dt.ua/internal/bilshe-yevropi-v-ukrayini-i-bilshe-ukrayini-v-yevropi-245095_.html" --xpath '//div[@class="central_article"]//ul[@class="auth_list"]//span[@class="name"]'
    #print('cmd: '+cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    #print(result)
    jsonArt = json.loads(result)
    article = None
    try:
      article = Article(url, jsonArt)
    except SystemExit:
      raise
    except:
      exc_type, exc_value, exc_traceback = sys.exc_info()
      print ("Unexpected error: ", exc_type, "In article ", result)
      traceback.print_exception(exc_type, exc_value, exc_traceback)
    #article.info()
    return article

  def fb2(self, num):
    today = datetime.date.today()
    url = self.baseUrl + '/gazeta/issue/%d' % (num)
    title = self.getTitleForNumber(num)
    print('get news for ', title)
    articleList = self.getNewsForNumber(num)
    if len(articleList) < 1:
      print('No articles for ', url)
      logging.warning("No articles for: "+ url)
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Дзеркало тижня</last-name></author>'
    ret += '\n  <book-title>' + title + '</book-title>'
    ret += '\n  <date>' + articleList[0].dtStr + '</date>'
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

  def getCurrentIssueNr(self):
    curIssueNr = -1
    url = self.baseUrl + '/archives'
    curIssueCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@id="footer"]//div[@class="bottom_menu"]//a[@class="link"]/@href\''
    cmd = curIssueCmd.format(url)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for ln in p.stdout:
      line = ln.decode('utf-8').strip()
      if len(line) > 0 and line.startswith('/gazeta/issue/'):
          curIssueNr = int(''.join(ele for ele in line if ele.isdigit()))

    return curIssueNr

  def getLastDownloadedIssueNr(self):
    now = datetime.datetime.now()
    curYearFolder = downloader_common.rootPath+'/dt_gazeta/'+str(now.year)
    prevYearFolder = downloader_common.rootPath+'/dt_gazeta/'+str(now.year-1)
    lastIssueFolder = downloader_common.rootPath+'/dt_gazeta'
    if os.path.isdir(curYearFolder): #folder for current year exists
        lastIssueFolder = curYearFolder
    elif os.path.isdir(prevYearFolder): #folder for previous year exists:
        lastIssueFolder = prevYearFolder
    else:
        return 1

    lastIssueNr = 1
    for issueFile in os.listdir(lastIssueFolder):
        if issueFile.endswith(".fb2"):
            curIssueNr = int(''.join(ele for ele in issueFile[:-3] if ele.isdigit()))
            if curIssueNr > lastIssueNr:
                lastIssueNr = curIssueNr

    return lastIssueNr

  def load(self):
    # get last downloaded number
    num = self.getLastDownloadedIssueNr() + 1

    # get current issue number (https://dt.ua/gazeta/issue/1129)
    currentIssueNum = self.getCurrentIssueNr()
    print ("download issues from {0} to {1}".format(num, currentIssueNum))
    logging.info("download issues from {0} to {1}".format(num, currentIssueNum))

    now = datetime.datetime.now()
    year = now.year

    #for num in strNumList
    while (num <= currentIssueNum):
      try:
        content = self.fb2(num)
        if len(content) > 0:
            with open((downloader_common.rootPath+'/dt_gazeta/'+"%d/dt_gazeta_%03d.fb2" % (year, num)), "w") as fb2_file:
                fb2_file.write(content)
        else:
            print("No content for num %d, year %d." % (num, year))
            logging.warning("No content for num %d, year %d." % (num, year))
      except KeyboardInterrupt:
        sys.exit("Download interrrupted.")
      except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        sys.exit("Unexpected error:  "+ str(exc_type))
      num += 1
    logging.info("Job completed")

if __name__ == '__main__':
    run()
