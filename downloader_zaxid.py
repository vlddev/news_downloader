import sys, traceback
import datetime
import subprocess
import json
import logging
import re
import stats
import downloader_common

def run():
    rootPath = '/home/vlad/Dokumente/python/news_lib'
    downloader = Downloader(rootPath)
    #logging.basicConfig(filename='downloader_debug.log',level=logging.DEBUG)

    logging.basicConfig(filename='downloader_zaxid.log',level=logging.INFO)

    strdate = '01.01.2017'
    date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
    #dateTo = datetime.datetime.strptime('17.09.2000', '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime('03.01.2017', '%d.%m.%Y').date()

    while (date < dateTo):
      content = downloader.fb2(date)
      if len(content) > 0:
        with open(rootPath+'/zaxid/'+str(date.year)+'/zaxid_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)

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
    val = j[1]
    if val is not None:
      self.summary = val.strip()

    self.body = list()
    val = j[2]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        locText = val
      elif isinstance(val, list):
        locText = '\n'.join(val)

      text = locText.strip() # trim

      #remove empty lines
      for line in text.split('\n'):
        proLine = downloader_common.relpaceHtmlEntities(line.strip())
        if len(proLine) > 0:
          self.body.append(proLine)

    self.author = ''
    val = j[3]
    if val is not None:
      if isinstance(val, str) and len(str(val).strip())>0:
        self.author = str(val).strip()
        if (self.author.endswith(",")):
            self.author = self.author[:len(self.author)-1]

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
    self.baseUrl = 'http://zaxid.net'
    self.getLinksCmd = (downloader_common.XIDEL_CMD + ' --xpath \'//ul[@class="list search_list"]//div[@class="title"]//@href\' '  #href
            ' --xpath \'//ul[@class="list search_list"]//span[@class="time"]\' ' #time
            ' --output-format=json-wrapped') #output as json
    self.getNextPageCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@class="b_center_pager"]//li[@class="arrow"]//@href\''
    self.rootPath = rootPath #'/home/vlad/Dokumente/python/news_lib'

    #xidel "http://zaxid.net/search/search.do?searchValue=%D0%B0&dateOrder=true&from=2008-05-01&to=2008-05-01&startRow=30" --xpath '//div[@class="advanced_search"]//@href' --xpath \'//div[@class="advanced_search"]//span[@class="time"]'
    #xidel "http://zaxid.net/search/search.do?searchValue=%D0%B0&dateOrder=true&from=2008-05-01&to=2008-05-01" --xpath '//div[@class="b_pager"]//li[@class="arrow"]//@href'


  def getNewsForDate(self, date):
    print('get news for ' + date.strftime('%d.%m.%Y'))
    articleList = list()
    downloadedUrls = set()
    pageNum = 1
    while True: #loop over pages
      url = self.baseUrl + '/search/search.do?searchValue=а&dateOrder=true&from='+date.strftime('%Y-%m-%d')+'&to='+date.strftime('%Y-%m-%d')+'&startRow='+str((pageNum-1)*10)
      print('page {0} url: {1}'.format(pageNum, url))
      # replace {0} with url
      cmd = self.getLinksCmd.format(url)
      #print('cmd: ' +cmd)
      p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
      jsonObj = json.loads(p.communicate()[0].decode('utf-8'))
      if len(jsonObj) > 0:
          urlList = jsonObj[0]
          timeList = jsonObj[1]

          if urlList is None or timeList is None:
            logging.warn('No articles for '+date.strftime('%d.%m.%Y'))
            print('No articles for '+date.strftime('%d.%m.%Y'))
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
            articleUrl = self.baseUrl + '/' + line
            if len(line) > 0 and articleUrl not in downloadedUrls:
              print ('load article: ' + articleUrl)
              try:
                retryCount = 0
                article = None
                while article is None and retryCount < 4:
                    article = self.loadArticle(articleUrl)
                    retryCount += 1
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
                    article.dtStr = date.strftime('%d.%m.%Y')
                    article.timeStr = timeList[i]
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

          #get link(s) to prev and next page
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
          expectedNextPageLink = '&startRow='+str((pageNum-1)*10)
          #print('expected page: ' +expectedNextPageLink)
          if all(expectedNextPageLink not in s for s in pgList):
            # expectedNextPageLink is not marked as next page (must be last page)
            break
      else:
          logging.error("No articles on page. URL: "+ url)
          pageNum += 1

    # end while (loop over pages)
    # order articles by time
    return sorted(articleList, key=lambda x: x.timeStr)

  def loadArticle(self, url):
    #xidel "http://zik.ua/news/2015/07/17/torgy_na_fondovomu_rynku_v_ssha_zavershylysya_zrostannyam_indeksiv_608090" -q --xpath '//article/p'
    #xidel "http://zik.ua/news/2006/05/22/u_chernivtsyah_prezentovano_molodizhnu_programu_dyskontnoi_merezhi_39953" -q --xpath '//article/p'

    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//div[@class="article_wrap no_m_right"]//h1[@class="title"]\'' #title
           ' --xpath \'//div[@class="article_wrap no_m_right"]//h2[@class="desc"]\'' #description
           ' --xpath \'//div[@class="col-9 w50"]//div[@id="newsSummary"]//p\'' #article text
           ' --xpath \'//div[@class="article_wrap no_m_right"]//a[@class="author_name"]\'' #author
           ' --output-format=json-wrapped') #output as json
    #print('cmd: '+cmd)
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
    #article.info()
    return article

  def fb2(self, date):
    today = datetime.date.today()
    url = self.baseUrl + '/search/search.do?dateOrder=true&from='+date.strftime('%Y-%m-%d')+'&to='+date.strftime('%Y-%m-%d')
    articleList = self.getNewsForDate(date)
    if len(articleList) < 1:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Zaxid.NET</last-name></author>'
    ret += '\n  <book-title>Zaxid.NET. Новини ' + date.strftime('%d.%m.%Y') + '</book-title>'
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

  def load(self, sDateFrom, sDateTo):
    logging.basicConfig(filename='downloader_zaxid.log',level=logging.INFO)
    date = datetime.datetime.strptime(sDateFrom, '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime(sDateTo, '%d.%m.%Y').date()

    while (date < dateTo):
      content = self.fb2(date)
      if len(content) > 0:
        with open(self.rootPath+'/zaxid/'+str(date.year)+'/zaxid_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)
    logging.info("Job completed")

"""
downloader = Downloader()
logging.basicConfig(filename='downloader_zaxid.log',level=logging.INFO)
rootPath = '/home/vlad/Dokumente/python/news_lib'

strdate = '17.12.2016'
date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
dateTo = datetime.datetime.strptime('01.01.2017', '%d.%m.%Y').date()

strDateList = ['2007-02-04','2007-02-06','2007-02-07','2007-02-15','2007-05-15','2007-05-16','2007-06-27','2007-07-06','2007-07-18'
              ,'2007-08-15','2007-08-20','2007-09-03','2007-11-14','2007-11-20', '']

dateList = []

while (date < dateTo):
  dateList.append(date)
  date += datetime.timedelta(days=1)

#for strDate in strDateList:
#  dateList.append(datetime.datetime.strptime(strDate, '%Y-%m-%d').date())

#print(dateList)

for date in dateList:
  content = downloader.fb2(date)
  if len(content) > 0:
    with open(rootPath+'/zaxid/'+str(date.year)+'/zaxid_'+str(date)+'.fb2', "w") as fb2_file:
      fb2_file.write(content)
"""
"""
logging.basicConfig(filename='downloader_zaxid_debug.log',level=logging.DEBUG)
#downloader.getNewsForDate('21.01.2011')
article = downloader.loadArticle('http://zaxid.net/news/showNews.do?sutinki_lvova&objectId=1037437')
print(article.info())
"""
