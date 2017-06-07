import sys
import os
import requests
import datetime
import subprocess
import logging
import json
import const_gazpu
import downloader_common

class Article(object):
  def __init__(self, url, j):
    self.url = ''
    if url is not None:
      self.url = url

    self.dtStr = ''
    self.timeStr = '00:00:00'
    if j[0] is not None:
      if isinstance(j[0], str):
        self.dtStr = j[0]
      elif isinstance(j[0], list):
        s = str(j[0][0])
        self.dtStr = s[s.find(',')+1:].strip() + ', ' + j[0][1]
        self.timeStr = str(j[0][1]).strip()

    self.title = ''
    if j[1] is not None:
      if isinstance(j[1], str):
        self.title = downloader_common.relpaceHtmlEntities(j[1])
      elif isinstance(j[1], list):
        self.title = downloader_common.relpaceHtmlEntities(j[1][0])

    self.body = list()
    if j[2] is not None:
      locText = ''
      if isinstance(j[2], str):
        locText = j[2]
      elif isinstance(j[2], list):
        locText = j[2][0]

      text = locText.strip() # trim

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
    #print('summary: '+str(self.summary));
    print('body: ' + "\n".join(self.body));

  def fb2(self):
    ret = '<section><title><p>' + downloader_common.escapeXml(self.title) + '</p></title>'
    ret += '\n <p>' + self.dtStr + '</p>'
    #if len(self.summary) > 0:
    #  ret += '\n <p><strong>' + downloader_common.escapeXml(self.summary) + '</strong></p>'
    ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + downloader_common.escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret

class Downloader(object):

  def __init__(self):
    self.baseUrl = 'http://gazeta.ua'
    self.getLinksCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div//a/@href\''
    self.const = const_gazpu.GazpuConst()

    #http://www.unian.ua/news/archive/20060319

  def getNewsForNumber(self, num):
    print("get news for №" + str(num))
    logging.info('Nr. ' + str(num))
    url = 'http://api.gazeta.ua/api/section/stream?page=1&limit=1000&type=newspaper&lang=uk&number=' + str(num)
    print('url: ' +url)
    articleList = list()
    urlList = list()
    downloadedUrls = set()

    #read url to file
    r = requests.get(url)
    strJson = r.text.replace("(RESTful.newsJsonpHandler(","").replace("\"success\":true}));","\"success\":true}")
    if len(strJson) < 10:
      return articleList
    data = json.loads(strJson)
    with open("gua.html", "w") as text_file:
        text_file.write(data['html'])

    # replace {0} with url
    cmd = self.getLinksCmd.format("gua.html")
    #print('cmd: ' +cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for ln in p.stdout:
      line = ln.decode('utf-8').strip()
      articleUrl = self.baseUrl + line
      if len(line) > 0 and '#comments' not in line and articleUrl not in urlList:
        urlList.append(articleUrl)

    os.remove("gua.html")

    for articleUrl in reversed(urlList):
      if articleUrl not in downloadedUrls:
        print ('load article: ' + articleUrl)
        try:
          article = self.loadArticle(articleUrl)
          if article is not None:
            bAddToList = True
            text = " ".join(article.body)
            text = text.strip()
            if len(text) < 1:
              if len(article.timeStr) > 0 and len(article.title) > 0:
                bAddToList = False
                logging.error("IGNORE: Empty article with title and time. URL: "+ articleUrl)
              else:
                bAddToList = False
                logging.error("Article is empty. URL: "+ articleUrl)
                article.info()
                #sys.exit("Article is empty. URL: "+ line)
            if bAddToList:
              if len(article.body) == 1:
                logging.warning("Article (length = "+str(len(text))+") has one paragraph. URL: "+ articleUrl)
              articleList.append(article)
              downloadedUrls.add(articleUrl)
          else:
            #exit
            logging.warning("Article can not be loaded from URL: "+ articleUrl)
            #sys.exit("Article can not be loaded from URL: "+ line)
        except SystemExit:
          raise
        except:
          exc_type, exc_value, exc_traceback = sys.exc_info()
          print ("Unexpected error: ", exc_type)
          traceback.print_exception(exc_type, exc_value, exc_traceback)
      else:
        print ('ignore url: '+ articleUrl)
        logging.warning('ignore url: '+ articleUrl)

    return articleList

  def loadArticle(self, url):
    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//div[@class="w double article"]//div[@class="clearfix"]//div[@class="pull-right news-date"]/span\'' #date in first line (hh:mm) and time in second line
           ' --xpath \'//div[@class="w double article"]//article//h1\'' #title
           #' --xpath \'//div[@class="article-text"]//h2\'' #summary
           ' --xpath \'//section[@class="article-content clearfix"]//article\'' #article body
           ' --output-format=json-wrapped') #output as json
    #print('cmd: '+cmd)
    #xidel http://www.unian.ua/society/46-ninishni-studenti-jitimut-pri-komunizmi.html -q -e "css('section[class=article-column] div[class=meta] time[itemprop=datePublished] attr(content) ')"

    #xidel http://www.unian.ua/society/46-ninishni-studenti-jitimut-pri-komunizmi.html -q --xpath '//section[@class="article-column"]//div[@class="meta"]//time[@itemprop="datePublished"]/@content'
    #xidel http://www.unian.ua/society/46-ninishni-studenti-jitimut-pri-komunizmi.html -q --xpath '//div[@class="article-text"]//span[@itemprop="articleBody"]//p'

    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    #print(result)
    jsonArt = json.loads(result)
    #print(jsonArt)

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

    return article

  def fb2(self, num):
    today = datetime.date.today()
    numUrl = '/newspaper/%d' % (num)
    url = self.baseUrl + numUrl
    articleList = self.getNewsForNumber(num)
    if len(articleList) < 1:
      return ''
    self.numDate = datetime.datetime.strptime(self.const.getDateByNumber(num), '%d.%m.%Y').date()
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Газета по-українськи</last-name></author>'
    if self.numDate is not None:
      ret += '\n  <book-title>Газета по-українськи. № ' + str(num) + ' за ' + self.numDate.strftime('%d.%m.%Y') + '</book-title>'
      ret += '\n  <date>' + str(self.numDate) + '</date>'
    else:
      ret += '\n  <book-title>Газета по-українськи. № ' + str(num) + '</book-title>'
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
        print ("Article ", article.info() ,"Unexpected error: ", sys.exc_info()[0])
    ret += '\n</body>'
    ret += '\n</FictionBook>'
    return ret


downloader = Downloader()

logging.basicConfig(filename='downloader_gaz_po_ukr.log',level=logging.INFO,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

num = 1981 #2016 - 1937

while (num < 2007):
  content = downloader.fb2(num)
  if len(content) > 0:
    with open(downloader_common.rootPath+'/gaz_po_ukr/'+str(downloader.numDate.year)+'/gaz_po_ukr_'+str(num)+'.fb2', "w") as fb2_file:
      fb2_file.write(content)
  num += 1
"""
#downloader.getNewsForNumber(1)
article = downloader.loadArticle('http://gazeta.ua/articles/comments-newspaper/_soyuznik-moskvi-perejde-na-storonu-kiyeva/100056')
#logging.basicConfig(filename='downloader_gaz_po_ukr_debug.log',level=logging.DEBUG)
print(article.info())
"""
