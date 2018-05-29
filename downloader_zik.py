import sys
import traceback
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
    # logging.basicConfig(filename='downloader_debug.log',level=logging.DEBUG)

    logging.basicConfig(filename='downloader_zik.log',level=logging.INFO)

    strdate = '20.11.2017'
    date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
    #dateTo = datetime.datetime.strptime('17.09.2000', '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime('01.01.2018', '%d.%m.%Y').date()

    while (date < dateTo):
      content = downloader.fb2(date)
      if len(content) > 0:
        with open(rootPath+'/zik/'+str(date.year)+'/zik_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)

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
      m = re.search('(\d{1,2}:\d{2})', self.dtStr)
      if m is not None:
        self.timeStr = m.group(0)
        if len(self.timeStr) == 4:
          self.timeStr = '0'+self.timeStr

    self.title = ''
    val = j[1]
    if val is not None:
      if isinstance(val, str):
        self.title = downloader_common.relpaceHtmlEntities(val)
      elif isinstance(val, list):
        self.title = downloader_common.relpaceHtmlEntities(val[0])
      if len(self.title) > 1000:
        self.title = self.title[:self.title.find('\n')] # get first line in long title

    self.summary = ''
    val = j[2]
    if val is not None:
      if isinstance(val, str):
        self.summary = val.strip()
      elif isinstance(val, list):
        self.summary = val[0].strip()

    self.author = ''

    self.body = list()
    val = j[3]
    if val is not None:
      locText = ''
      if isinstance(val, str):
        locText = val
      elif isinstance(val, list):
        locText = '\n'.join(val)
      if len(self.summary) > 0 and len(locText) > 0:
        locText = locText.replace(self.summary,'',1).strip() # remove summary from the body, trim
      text = locText.strip() # trim

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
    #if len(self.author) > 0:
    #  ret += '\n <p>' + self.author + '</p>'
    ret += '\n <p>' + self.timeStr + '</p>'
    ret += '\n <p><strong>' + downloader_common.escapeXml(self.summary) + '</strong></p>'
    ret += '\n <empty-line/>'
    for line in self.body:
      ret += '\n <p>' + downloader_common.escapeXml(line) + '</p>'
    ret += '\n</section>'
    return ret

class Downloader(object):

  def __init__(self, rootPath):
    self.baseUrl = 'http://zik.ua'
    self.getLinksCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@class="archive_list"]//@href\''
    self.getNextPageCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@class="b_pager"]//li[@class="arrow"]//@href\''
    self.rootPath = rootPath #'/home/vlad/Dokumente/python/news_lib'

    #xidel "http://zik.ua/archive/all/2015/7/17?pg=1" --xpath '//div[@class="archive_list"]//@href'
    #xidel "http://zik.ua/archive/all/2015/7/17?pg=8" --xpath '//div[@class="b_pager"]//li[@class="arrow"]//@href'


  def getNewsForDate(self, date):
    print('get news for ' + date.strftime('%d.%m.%Y'))
    articleList = list()
    downloadedUrls = set()
    pageNum = 1
    while True: #loop over pages
      url = self.baseUrl + '/archive/all/'+str(date.year)+'/'+str(date.month)+'/'+str(date.day)+'?pg='+str(pageNum)
      print('url: ' +url)
      # replace {0} with url
      cmd = self.getLinksCmd.format(url)
      #print('cmd: ' +cmd)
      p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
      for ln in p.stdout: #loop over all articles on page
        line = ln.decode('utf-8').strip()
        articleUrl = self.baseUrl + line
        if len(line) > 0 and line not in downloadedUrls:
          print ('load article: ' + line)
          try:
            article = self.loadArticle(articleUrl)
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
                articleList.append(article)
                downloadedUrls.add(line)
            else:
              #exit
              logging.error("Article can not be loaded from URL: "+ articleUrl)
              sys.exit("Article can not be loaded from URL: "+ articleUrl)
          except SystemExit:
            raise
          except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print ("Unexpected error: ", exc_type)
            traceback.print_exception(exc_type, exc_value, exc_traceback)
        else:
          print ('ignore url: '+ line)
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
      expectedNextPageLink = '/archive/all/'+str(date.year)+'/'+str(date.month)+'/'+str(date.day)+'?pg='+str(pageNum)
      #print('expected page: ' +expectedNextPageLink)
      if expectedNextPageLink not in pgList:
        break
    # end while (loop over pages)
    # order articles by time
    return sorted(articleList, key=lambda x: x.timeStr)

  def loadArticle(self, url):
    #xidel "http://zik.ua/news/2015/07/17/torgy_na_fondovomu_rynku_v_ssha_zavershylysya_zrostannyam_indeksiv_608090" -q --xpath '//article/p'
    #xidel "http://zik.ua/news/2006/05/22/u_chernivtsyah_prezentovano_molodizhnu_programu_dyskontnoi_merezhi_39953" -q --xpath '//article/p'

    cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//article//div[@class="publication_date"]\'' #date
           ' --xpath \'//article//div[@class="title"]\'' #title
           ' --xpath \'//article//p[@class="description"]\'' #description
           ' --xpath \'//article//p\'' #article text with description
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

  def fb2(self, date):
    today = datetime.date.today()
    url = self.baseUrl + '/archive/all/'+str(date.year)+'/'+str(date.month)+'/'+str(date.day)
    articleList = self.getNewsForDate(date)
    if len(articleList) < 1:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Західна інформаційна корпорація</last-name></author>'
    ret += '\n  <book-title>ІА ZIK. Новини ' + date.strftime('%d.%m.%Y') + '</book-title>'
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
    logging.basicConfig(filename='downloader_zik.log',level=logging.INFO)
    date = datetime.datetime.strptime(sDateFrom, '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime(sDateTo, '%d.%m.%Y').date()

    while (date < dateTo):
      content = self.fb2(date)
      if len(content) > 0:
        with open(self.rootPath+'/zik/'+str(date.year)+'/zik_'+str(date)+'.fb2', "w") as fb2_file:
          fb2_file.write(content)
      date += datetime.timedelta(days=1)
    logging.info("Job completed")

"""
downloader = Downloader()
#logging.basicConfig(filename='downloader_um_debug.log',level=logging.DEBUG)

logging.basicConfig(filename='downloader_zik.log',level=logging.INFO)
rootPath = '/home/vlad/Dokumente/python/news_lib'

strdate = '27.11.2016'
date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
dateTo = datetime.datetime.strptime('01.01.2017', '%d.%m.%Y').date()

strDateList = ['2007-02-04','2007-02-06','2007-02-07','2007-02-15','2007-05-15','2007-05-16','2007-06-27','2007-07-06','2007-07-18'
              ,'2007-08-15','2007-08-20','2007-09-03','2007-11-14','2007-11-20', '']

dateList = []

while (date < dateTo):
  dateList.append(date)
  date += datetime.timedelta(days=1)
"""
"""
for strDate in strDateList:
  dateList.append(datetime.datetime.strptime(strDate, '%Y-%m-%d').date())
"""
"""
#print(dateList)

for date in dateList:
  content = downloader.fb2(date)
  if len(content) > 0:
    with open(rootPath+'/zik/'+str(date.year)+'/zik_'+str(date)+'.fb2', "w") as fb2_file:
      fb2_file.write(content)
"""
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

if __name__ == '__main__':
    run()
