import pdb
import sys, traceback
import datetime
import subprocess
import json
import re
import logging
from bs4 import BeautifulSoup
import stats
import downloader_common

def run():
    downloader = Downloader()

    logging.basicConfig(filename='downloader_tyzhden.log', level=logging.INFO,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    downloader.load(529, 570)


def test():
    downloader = Downloader()

    logging.basicConfig(filename='downloader_tyzhden.log', level=logging.DEBUG,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    article = downloader.loadArticle('http://tyzhden.ua/Columns/50/220779')
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
      text = re.sub("(<!--.*?-->)", "", text, flags=re.MULTILINE|re.DOTALL)

      #remove empty lines and "Читайте також:"
      for line in text.split('\n'):
        proLine = downloader_common.relpaceHtmlEntities(line.strip())
        if len(proLine) > 0 and not proLine.startswith('Читайте також:'):
          if (proLine.startswith('Відповідно до угоди, статті the Economist')):
            self.body.append('content deleted')
          else:
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
        if isinstance(val, list):
          val = '; '.join(val)
        
        if 'Версія для друку' not in val:
          self.author = val.strip()

    if len(j) > 5 and len(self.author) < 1:
      val = j[5]
      if val is not None:
        if isinstance(val, list):
          val = '; '.join(val)
        self.author = val.strip()


class Downloader(object):

  def __init__(self):
    self.baseUrl = 'http://tyzhden.ua'
    self.getLinksCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@class="ap2"]//div[@class="bf2 ap6"]//@href\''
    self.getNumDateCmd = downloader_common.XIDEL_CMD + ' --xpath \'//h1[@class="ap1"]//span[@class="bf2 ap1"]\''
    self.numDate = None
    self.dict = {" січня, ":".01.", " лютого, ":".02.", " березня, ":".03.",
                 " квітня, ":".04.", " травня, ":".05.", " червня, ":".06.",
                 " липня, ":".07.", " серпня, ":".08.", " вересня, ":".09.",
                 " жовтня, ":".10.", " листопада, ":".11.", " грудня, ":".12."}

    #xidel "http://tyzhden.ua/Magazine/10" --xpath '//div[@class="ap3"]//div[@class="ap2"]//@href'
    #xidel "http://tyzhden.ua/Magazine/10" --xpath '//div[@class="ap3"]//h1[@class="ap1"]//span[@class="bf2 ap1"]'


  def getNewsForNumber(self, num):
    numUrl = '/Magazine/%d' % (num)
    url = self.baseUrl + numUrl
    print('url: ' +url)
    articleList = list()
    downloadedUrls = set()
    cmd = self.getNumDateCmd.format(url)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    result = result[result.find('від')+3:].strip()
    if len(result) < 1: #no such URL
      return None
    if not result[-4:].isdigit(): #last 4 chars are not digits -> add current year
      result += (', '+str(datetime.date.today().year)) #get current year
    # replace month
    for key in self.dict.keys() :
      if key in result:
        result = result.replace(key, self.dict[key])
        break
    print ("date: "+result)
    # get date from result
    self.numDate = datetime.datetime.strptime(result, '%d.%m.%Y').date()

    # replace {0} with url
    cmd = self.getLinksCmd.format(url)
    #print('cmd: ' +cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for ln in p.stdout:
      line = ln.decode('utf-8').strip()
      articleUrl = line
      if '//' in line[10:] :
        articleUrl = line[:10] + line[10:].replace("//", "/Columns/50/")
        print("strange URL: "+line+" trying "+articleUrl)
      if len(articleUrl) > 0 and articleUrl.startswith(self.baseUrl) and articleUrl not in downloadedUrls:
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
                  articleList.append(article)
                  downloadedUrls.add(articleUrl)
              else:
                #exit
                logging.warning("Article can not be loaded from URL: "+ articleUrl)
                #try to fix url
                if '/Almost/' in line :
                  articleUrl = line.replace("/Almost/", "/Society/")
                  print("change URL: "+line+" with "+articleUrl)
                  retry = True
              if not retry :
                break
        except SystemExit:
          raise
        except:
          exc_type, exc_value, exc_traceback = sys.exc_info()
          print ("Unexpected error: ", exc_type)
          traceback.print_exception(exc_type, exc_value, exc_traceback)
      else:
        if articleUrl not in downloadedUrls:
          print ('ignore url: '+ articleUrl)
    return articleList

  def loadArticle(self, url):
    if ('Columns/50' in url):
      cmd = (downloader_common.XIDEL_CMD.format(url) +
          ' --xpath \'//table[@class="ap6"]//div[@class="bf4"]/span[1]\'' #date
          ' --xpath \'//h1[@class="ap5"]\'' #title
          ' --xpath \'//div[@class="bf3 ap1 _ga1_on_" or @class="bf3 ap2 _ga1_on_" or @class="bf3 ap1 _ga1_on_ io-article-body" or @class="bf3 ap2 _ga1_on_ io-article-body"]\'' #article text
          ' --xpath \'//div[@class="bf1"]\'' #article summary
          ' --xpath \'//table[@class="ap6"]//div[@class="bf4"]/span[3]\'' #author [optional]
          ' --xpath \'//table[@class="ap6"]//div[@class="bf3 ap4"]/a\'' #author 2 [optional]
          ' --output-format=json-wrapped') #output as json
    else:
      cmd =  (downloader_common.XIDEL_CMD.format(url) +
          ' --xpath \'//article[@class="Cheat orphan"]//div[@class="CheatHeader__top"]//span[@class="PublicationTime__date"]\'' #date
          ' --xpath \'//article[@class="Cheat orphan"]//h1[@class="CheatHeader__title"]\'' #title
          ' --xpath \'//div[@class="CheatBody io-article-body"]/div[1]/node()[not(self::blockquote)]\'' #article text
          ' --xpath \'//div[@class="bf1"]\'' #article summary
          ' --xpath \'//article[@class="Cheat orphan"]//div[@class="CheatHeader__top"]//a[@class="io-author"]\'' #author [optional]
          ' --output-format=json-wrapped') #output as json

    #xidel http://tyzhden.ua/Publication/1254 -q --xpath '//table[@class="ap6"]//div[@class="bf4"]/span[1]'
    #xidel http://tyzhden.ua/Publication/1254 -q --xpath '//div[@class="bf3 ap1 _ga1_on_" or @class="bf3 ap2 _ga1_on_"]'
    #print('cmd: '+cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = p.communicate()[0].decode('utf-8')
    jsonArt = json.loads(result)

    article = None
    try:
      if len(jsonArt) > 0 :
        article = Article(url, jsonArt)
      else:
        logging.warning("Nothing can be load from: "+url)
        print("Nothing can be load from: "+url)
        return None
    except:
      exc_type, exc_value, exc_traceback = sys.exc_info()
      print ("Unexpected error: ", exc_type, "In article ", result)
      logging.error("Unexpected error: {}. In article {}".format(exc_type, result))
      traceback.print_exception(exc_type, exc_value, exc_traceback)
    #article.info()
    print ("len(article.body) = " + str(len(article.body)))

    if len(article.body) <= 2 : #article has only one row, download as html
      #xidel http://tyzhden.ua/Columns/50/6881 -q --xpath '//div[@class="bf3 ap1 _ga1_on_" or @class="bf3 ap2 _ga1_on_"]//div'
      print ("article has <= 2 row(s), reload it")
      logging.debug("article has<= 2 row(s), download as html")
      text = " ".join(article.body)
      text = text.strip()
      if len(text) > 0: #article is not empty
        cmd = (downloader_common.XIDEL_CMD.format(url) +
           ' --xpath \'//div[@class="bf3 ap1 _ga1_on_" or @class="bf3 ap2 _ga1_on_"]//div | //div[@class="bf3 ap1 _ga1_on_" or @class="bf3 ap2 _ga1_on_"]//p\'') #article text
           #' --output-format=json-wrapped') #output as json
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        result = p.communicate()[0].decode('utf-8')
        if len(str(result).strip()) == 0 :
            cmd = (downloader_common.XIDEL_CMD.format(url) +
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

    return article

  def fb2(self, num):
    today = datetime.date.today()
    numUrl = '/Magazine/%d' % (num)
    url = self.baseUrl + numUrl
    articleList = self.getNewsForNumber(num)
    if articleList is None:
      return ''
    ret = '<?xml version="1.0" encoding="utf-8"?>'
    ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
    ret += '\n<description>'
    ret += '\n <title-info>'
    ret += '\n  <genre>nonfiction</genre>'
    ret += '\n  <author><last-name>Український тиждень</last-name></author>'
    if self.numDate is not None:
      ret += '\n  <book-title>Український тиждень № ' + str(num) + ' від ' + self.numDate.strftime('%d.%m.%Y') + '</book-title>'
      ret += '\n  <date>' + str(self.numDate) + '</date>'
    else:
      ret += '\n  <book-title>Український тиждень № ' + str(num) + '</book-title>'
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

  def load(self, numFrom, numTo):

    num = numFrom

    while (num < numTo):
      try:
        content = self.fb2(num)
        if len(content) > 0:
          with open(str(self.numDate.year)+'/tyzhden_'+str(num)+'.fb2', "w") as fb2_file:
            fb2_file.write(content)
        else:
          msg = "No content for number {0}.".format(num)
          print(msg)
          logging.warning(msg)
      except KeyboardInterrupt:
        sys.exit("Download interrupted.")
      except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        sys.exit("Unexpected error:  "+ exc_type)
      num += 1
    logging.info("Job completed")


if __name__ == '__main__':
    run()