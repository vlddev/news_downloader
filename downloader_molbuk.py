import sys, traceback
import datetime
import subprocess
import json
import logging
import stats
from bs4 import BeautifulSoup
import downloader_common

class Article(object):
  def __init__(self, url, j):
    self.url = ''
    if url is not None:
      self.url = url

    self.dtStr = ''
    self.timeStr = '00:00'

    self.title = ''
    val = j[0]
    if val is not None:
      if isinstance(val, str):
        self.title = downloader_common.relpaceHtmlEntities(val)
      elif isinstance(val, list):
        self.title = downloader_common.relpaceHtmlEntities(val[0])
      if len(self.title) > 1000:
        self.title = self.title[:self.title.find('\n')] # get first line in long title

    self.summary = ''

    self.body = list()
    cutStr = 'Підписуйтесь на новини "МБ" у соцмережах'
    cutStr1 = 'Приєднуйтесь до "МБ" у соцмережах'
    cutStr2 = '\nРейтинг:\n'
    if len(j) > 1:
        val = j[1]
        if val is not None:
          locText = ''
          if isinstance(val, str):
            locText = val
          elif isinstance(val, list):
            locText = '\n'.join(val)

          text = locText.strip() # trim
          if cutStr in text:
            text = text[:text.find(cutStr)]
          elif cutStr1 in text:
            text = text[:text.find(cutStr1)]
          elif cutStr2 in text:
            text = text[:text.find(cutStr2)]

          #remove empty lines
          for line in text.split('\n'):
            proLine = downloader_common.relpaceHtmlEntities(line.strip())
            if len(proLine) > 0:
              self.body.append(proLine)

    self.author = ''

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
    if len(self.summary) > 0:
      ret += '\n <p><strong>' + downloader_common.escapeXml(self.summary) + '</strong></p>'
    ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + downloader_common.escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret

class Downloader(object):

  def __init__(self, rootPath):
    self.rootPath = rootPath
    self.todayStr = 'Сьогодні'
    self.yesterdayStr = 'Вчора'
    self.baseUrl = 'http://molbuk.ua'
    self.getLinksCmd = (downloader_common.XIDEL_CMD + ' --xpath \'//table[@class="main-table"]//td[@class="td-for-content"]//div[@class="short-1"]//div[@class="short-1-title"]//@href\' '  #href
            ' --xpath \'//table[@class="main-table"]//td[@class="td-for-content"]//div[@class="short-1"]//div[@class="short-1-more"]//span\' ' #time
            ' --output-format=json-wrapped --output-encoding=windows-1251') #output as json

    #xidel "http://molbuk.ua/vnomer/page/3" --xpath '//table[@class="main-table"]//td[@class="td-for-content"]//div[@class="short-1"]//div[@class="short-1-title"]//@href'

  def getNewsPerPage(self, startPage, stopDate):
    today = datetime.date.today()
    pageNum = startPage
    articleList = list()
    downloadedUrls = set()
    curDateStr = self.todayStr
    bDone = False

    while not bDone: #loop over pages
        url = self.baseUrl + '/vnomer/page/'+str(pageNum)
        print('page {0} url: {1}'.format(pageNum, url))
        # replace {0} with url
        cmd = self.getLinksCmd.format(url)
        #print('cmd: ' +cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        jsonObj = json.loads(p.communicate()[0].decode('windows-1251'))

        if len(jsonObj) > 0:
            urlList = jsonObj[0]
            timeList = jsonObj[1]

            if urlList is None or timeList is None:
                logging.warn('No articles for page '+str(pageNum))
                print('No articles for page '+str(pageNum))
                break

            if isinstance(urlList, str) and isinstance(timeList, str):
                urlList = [jsonObj[0]]
                timeList = [jsonObj[1]]

            if len(urlList) != len(timeList):
                print('jsonObj: ' +str(jsonObj))
                print('urlList: ' +str(jsonObj[0]))
                print('timeList: ' +str(jsonObj[1]))
                sys.exit("len(urlList) != len(timeList). STOP.")

            for i in range(0, len(urlList)): #loop over all articles on page
                line = urlList[i].strip()
                articleUrl = line
                if len(line) > 0 and articleUrl not in downloadedUrls:
                  print ('load article: ' + articleUrl)
                  try:
                    article = self.loadArticle(articleUrl)
                    tryCount = 3
                    while article is None and tryCount > 0:
                        print ('WARNING: retry load article (attempt '+str(4-tryCount)+'): ' + articleUrl)
                        logging.warn('retry load article (attempt '+str(4-tryCount)+'): ' + articleUrl)
                        article = self.loadArticle(articleUrl)
                        tryCount -= 1
                    if article is not None:
                      bAddToList = True
                      text = " ".join(article.body)
                      text = text.strip()
                      if len(text) > 0 or len(article.summary) > 0:
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
                        if len(article.body) == 1 and len(text) > 1000:
                          logging.warning("Article (length = "+str(len(text))+") has one paragraph. URL: "+ articleUrl)
                        article.dtStr = timeList[i]
                        articleDateStr = article.dtStr.split(',',1)[0].strip()
                        article.timeStr = article.dtStr.split(',',1)[1].strip()
                        if curDateStr != articleDateStr:
                            curDate = None
                            if curDateStr == self.todayStr:
                                curDate = datetime.date.today()
                            elif curDateStr == self.yesterdayStr:
                                curDate = datetime.date.today() - datetime.timedelta(days=1)
                            else:
                                curDate = datetime.datetime.strptime(curDateStr, '%d-%m-%Y').date()
                            #store list for curDate
                            print ('store articles for: ' + str(curDate))
                            articleList.reverse()
                            content = self.fb2(curDate, articleList)
                            if len(content) > 0:
                                #with open('molbuk/'+str(curDate.year)+'/molbuk'+str(curDate)+'.fb2', "w") as fb2_file:
                                with open(self.rootPath+'/molbuk/'+str(curDate.year)+'/molbuk'+str(curDate)+'.fb2', "w") as fb2_file:
                                    fb2_file.write(content)
                            #clear all lists
                            del articleList[:]
                            downloadedUrls.clear
                            curDateStr = articleDateStr
                            if stopDate >= curDate:
                                print ('download done')
                                bDone = True
                                break
                        articleList.append(article)
                        downloadedUrls.add(articleUrl)
                    else:
                      #exit
                      logging.error("Article can not be loaded from URL: "+ articleUrl)
                      #sys.exit("Article can not be loaded from URL: "+ articleUrl)
                  except SystemExit:
                    raise
                  except:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    print ("Unexpected error: ", exc_type)
                    traceback.print_exception(exc_type, exc_value, exc_traceback)
                    sys.exit()
                else:
                  print ('ignore url: '+ articleUrl)
            #end for (loop over all articles on page)

            pageNum += 1
        else:
            logging.error("No articles on page. URL: "+ url)

  #end of getNewsPerPage

  def loadArticle(self, url):
    #xidel "http://molbuk.ua/chernovtsy_news/117957-take-yak-ty-ne-tone-radnyk-mera-chernivciv-rizko-vidpovila-deputatu-beshleyu.html" -q --xpath '//article/p'

    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//table[@class="main-table"]//td[@class="td-for-content"]//div[@class="short-block"]//h1\'' #title
           #' --xpath \'//table[@class="main-table"]//td[@class="td-for-content"]//div[@class="short-block"]//div[@class="shot-text"]\'' #article text
           #' --xpath \'//div[@class="article_wrap no_m_right"]//a[@class="author_name"]\'' #author
           ' --output-format=json-wrapped --output-encoding=windows-1251') #output as json
    #print('cmd: '+cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('windows-1251')
    #print(result)
    jsonArt = json.loads(result)

    article = None
    try:
      if len(jsonArt) > 0 :
        if len(jsonArt) == 1:
            jsonArt.append("")
        cmdContent = (downloader_common.XIDEL_CMD.format(url) +
               ' --xpath \'//table[@class="main-table"]//td[@class="td-for-content"]//div[@class="short-block"]//div[@class="shot-text"]\'' #article text
               ' --output-format=html --output-encoding=windows-1251') #output as html
        jsonArt[1] = self.loadArticleTextFromHtml(cmdContent)
        article = Article(url, jsonArt)
      else:
        #logging.warning("Nothing can be load from: "+url)
        print("Nothing can be load from: "+url)
        return None
    except:
      exc_type, exc_value, exc_traceback = sys.exc_info()
      print ("Unexpected error: ", exc_type, "In article ", result)
      traceback.print_exception(exc_type, exc_value, exc_traceback)
    #article.info()
    return article

  def loadArticleTextFromHtml(self, xidelCmd):
    p = subprocess.Popen(xidelCmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('windows-1251')
    logging.debug(">> loadArticleTextFromHtml()")
    logging.debug(result)
    #print(result)
    txt = result.replace('<br>', '[br]').replace('</br>', '').replace('<p>', '[br]').replace('</p>', '').replace('<br />', '[br]')
    txt = txt.replace('<BR>', '[br]').replace('</BR>', '').replace('<P>', '[br]').replace('</P>', '').replace('<BR />', '[br]')
    txt = txt.replace('&amp;#', '&#')
    logging.debug(">> replace with [br]")
    logging.debug(txt)
    soup = BeautifulSoup(txt, 'html.parser')
    logging.debug(">> soap.text")
    logging.debug(soup.get_text())
    return soup.get_text().replace('[br]', '\n')

  def fb2(self, date, articleList):
    today = datetime.date.today()
    url = self.baseUrl
    if len(articleList) < 1:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>molbuk.ua</last-name></author>'
    ret += '\n  <book-title>Молодий буковинець. Новини. ' + date.strftime('%d.%m.%Y') + '</book-title>'
    ret += '\n  <date>' + str(date) + '</date>'
    ret += '\n  <lang>uk</lang>'
    ret += '\n </title-info>'
    ret += '\n <document-info>'
    ret += '\n  <author><nickname>V.Vlad</nickname></author>'
    ret += '\n  <date value="' + str(today) + '">' + str(today) + '</date>'
    ret += '\n  <version>1.0</version>'
    ret += '\n  <src-url>' + downloader_common.escapeXml(url) + '</src-url>'
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

downloader = Downloader(downloader_common.rootPath)
logging.basicConfig(filename='downloader_molbuk.log',level=logging.INFO,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

dateTo = datetime.datetime.strptime('01.06.2017', '%d.%m.%Y').date()

# download articles from today until dateTo
downloader.getNewsPerPage(1, dateTo)

"""
logging.basicConfig(filename='downloader_molbuk_debug.log',level=logging.DEBUG)
downloader = Downloader()
#downloader.getNewsForDate('21.01.2011')
article = downloader.loadArticle('http://molbuk.ua/chernovtsy_news/118147-u-cherniveckiy-filarmoniyi-vystupyt-vidomyy-avstriyskyy-pianist.html')
print(article.info())
"""
