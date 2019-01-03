import sys
import traceback
import datetime
import subprocess
import logging
import json
import re
import concurrent.futures
from bs4 import BeautifulSoup
import downloader_common

def run():
    downloader = Downloader()

    logging.basicConfig(filename='downloader_unian.log', level=logging.INFO,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    downloader.loadThreaded('18.12.2018', '01.01.2019')


def run_old():
    rootPath = downloader_common.rootPath
    downloader = Downloader()
    logging.basicConfig(filename='downloader_unian.log', level=logging.INFO)

    strdate = '01.04.2018'
    date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
    # dateTo = datetime.datetime.strptime('17.09.2000', '%d.%m.%Y').date()
    dateTo = datetime.datetime.strptime('02.04.2018', '%d.%m.%Y').date()

    while (date < dateTo):
        content = downloader.fb2(date)
        if len(content) > 0:
            with open(rootPath + '/unian/' + str(date.year) + '/unian_' +
                      str(date) + '.fb2', "w") as fb2_file:
                fb2_file.write(content)
        date += datetime.timedelta(days=1)

def test():
    rootPath = downloader_common.rootPath
    downloader = Downloader()

    logging.basicConfig(filename='downloader_unian.log',level=logging.DEBUG,
        format='%(asctime)s %(levelname)s\t%(module)s\t%(message)s', datefmt='%d.%m.%Y %H:%M:%S')

    article = downloader.loadArticle('https://www.unian.ua/incidents/10064507-u-hmelnickomu-suditimut-bandu-shcho-trujila-lyudey-zaradi-nazhivi.html')
    print(article.info())


def runUrl():
    rootPath = '/home/vlad/Dokumente/python/news_lib'
    downloader = Downloader()
    article = downloader.loadArticle('https://sport.unian.ua/hockey/2137881-kremenchuk-zakinuv-vovkam-7-shayb-i-rozgromiv-brovarsku-komandu.html')
    print(article.info())

class Article(object):
    def __init__(self, url, j):
        self.url = ''
        if url is not None:
            self.url = url

        self.dtStr = ''
        if j[0] is not None:
            self.dtStr = j[0]
        if len(self.dtStr) > 7:
            if re.match(r'^\d{1,2}:\d{1,2}.*$', self.dtStr, re.MULTILINE) is not None:
                self.timeStr = self.dtStr[0:5] + ':00'  # extract time (first 5 char)
            else:
                self.timeStr = self.dtStr[-8:]  # extract time (last 8 char)
        else:
            logging.warning("Time not set in article. URL: " + self.url)
            self.timeStr = '00:00:00'

        self.title = ''
        if j[1] is not None:
            if isinstance(j[1], str):
                self.title = j[1]
            elif isinstance(j[1], list):
                self.title = j[1][0]

        self.summary = ''
        if j[2] is not None:
            if isinstance(j[2], str):
                self.summary = j[2]
            elif isinstance(j[2], list):
                self.summary = j[2][0]

        self.body = list()
        val = j[3]
        if val is not None:
            locText = ''
            if isinstance(val, str):
                locText = val
            elif isinstance(val, list):
                locText = '\n'.join(val)

            text = locText.strip()  # trim

            if 'Якщо ви знайшли помилку' in text:
                text = text[:text.find('Якщо ви знайшли помилку')]

            # remove empty lines
            for line in text.split('\n'):
                proLine = line.strip()
                if len(proLine) > 0:
                    self.body.append(proLine)

    def info(self):
        print('dtStr: ' + self.dtStr)
        print('timeStr: ' + self.timeStr)
        print('url: ' + self.url)
        print('title: ' + str(self.title))
        print('summary: ' + str(self.summary))
        print('body: ' + "\n".join(self.body))

    def fb2(self):
        ret = '<section><title><p>' + downloader_common.escapeXml(
            self.title) + '</p></title>'
        ret += '\n <p>' + self.timeStr + '</p>'
        if len(self.summary) > 0:
            ret += '\n <p><strong>' + downloader_common.escapeXml(
                self.summary) + '</strong></p>'
        ret += '\n <empty-line/>'
        for line in self.body:
            ret += '\n <p>' + downloader_common.escapeXml(line) + '</p>'
        ret += '\n</section>'
        return ret


class Downloader(downloader_common.AbstractDownloader):
    def __init__(self, rootPath=''):
        self.baseUrl = 'https://www.unian.ua'
        self.getLinksCmd = downloader_common.XIDEL_CMD + ' --xpath \'//div[@class="publications-archive"]//div[@class="gallery-item news-inline-item"]//a[@class="publication-title"]/@href\''
        # http://www.unian.ua/news/archive/20060319
        # self.rootPath = rootPath  # '/home/vlad/Dokumente/python/news_lib'
        super().__init__('unian')

    def getUrlsForDate(self, date):
        url = self.baseUrl + '/news/archive/' + date.strftime('%Y%m%d')
        print('url: ' + url)
        urlList = list()
        # replace {0} with url
        cmd = self.getLinksCmd.format(url)
        # print('cmd: ' +cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        for ln in p.stdout:
            line = ln.decode('utf-8').strip()
            line = line.replace("http://culture.unian.net/",
                                "http://culture.unian.ua/")
            line = line.replace("http://crimea.unian.net/",
                                "http://crimea.unian.ua/")
            if line.startswith("//"):
                line = 'https:' + line
            if line in urlList:
                print('ignore url (already known): ' + line)
                continue

            if len(line) > 0 and (line.startswith("http://")
                                  or line.startswith("https://")) and (
                                      ".unian.ua/" in line
                                      or "unian.net/ukr" in line):
                urlList.append(line)
            else:
                print('ignore url: ' + line)
                logging.warning('ignore url (not unian): ' + line)
        return urlList

    def getNewsForDate(self, date):
        articleList = list()
        urls = self.getUrlsForDate(date)
        for line in urls:
            print('load article: ' + line)
            try:
                article = self.loadArticle(line)
                if article is not None:
                    bAddToList = True
                    text = " ".join(article.body)
                    text = text.strip()
                    if len(text) < 1:
                        if line in ['']:
                            bAddToList = False
                            logging.error(
                                "IGNORE: Article is empty. URL: " + line)
                        elif len(article.timeStr) > 0 and len(
                                article.title) > 0:
                            bAddToList = False
                            logging.error(
                                "IGNORE: Empty article with title and time. URL: "
                                + line)
                        else:
                            bAddToList = False
                            logging.error("Article is empty. URL: " + line)
                            article.info()
                            # sys.exit("Article is empty. URL: "+ line)
                    if bAddToList:
                        if len(article.body) == 1:
                            logging.warning(
                                "Article (length = " + str(len(text)) +
                                ") has one paragraph. URL: " + line)
                        articleList.append(article)
                else:
                    # exit
                    logging.warning("Article can not be loaded from URL: " + line)
                    # sys.exit("Article can not be loaded from URL: "+ line)
            except SystemExit:
                raise
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print("Unexpected error: ", exc_type)
                traceback.print_exception(exc_type, exc_value,
                                          exc_traceback)
        # order articles by time
        return sorted(articleList, key=lambda x: x.timeStr)

    def getNewsForDateThreaded(self, date):
        articleList = list()
        urls = self.getUrlsForDate(date)
        print("Found {0} articles. Start downloading.".format(len(urls)))
        # use a with statement to ensure threads are cleaned up promptly
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Start the load operations and mark each future with its URL
            futureToUrl = {executor.submit(self.loadArticle, url): url for url in urls}
            for future in concurrent.futures.as_completed(futureToUrl):
                url = futureToUrl[future]
                try:
                    article = future.result()
                    if article is not None:
                        bAddToList = True
                        text = " ".join(article.body)
                        text = text.strip()
                        if len(text) < 1:
                            if url in ['']:
                                bAddToList = False
                                logging.error(
                                    "IGNORE: Article is empty. URL: " + url)
                            elif len(article.timeStr) > 0 and len(
                                    article.title) > 0:
                                bAddToList = False
                                logging.error(
                                    "IGNORE: Empty article with title and time. URL: "
                                    + url)
                            else:
                                bAddToList = False
                                logging.error("Article is empty. URL: " + url)
                                article.info()
                                # sys.exit("Article is empty. URL: "+ line)
                        if bAddToList:
                            if len(article.body) == 1:
                                logging.warning(
                                    "Article (length = " + str(len(text)) +
                                    ") has one paragraph. URL: " + url)
                            articleList.append(article)
                    else:
                        # exit
                        logging.warning("Article can not be loaded from URL: " + url)
                        # sys.exit("Article can not be loaded from URL: "+ line)
                except SystemExit:
                    raise
                except BaseException:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    print("Unexpected error: ", exc_type)
                    traceback.print_exception(exc_type, exc_value, exc_traceback)
        # order articles by time
        return sorted(articleList, key=lambda x: x.timeStr)

    def loadArticle(self, url):
        cmd = (
            downloader_common.XIDEL_CMD.format(url) +
            ' --xpath \'//div[@class="article-text"]//div[@class="item time no-padding"]\''  # datetime in format hh:mi, dd Month yyyy
            ' --xpath \'//div[@class="article-text"]//h1\''  # title
            ' --xpath \'//div[@class="article-text"]//h2\''  # summary
            # ' --xpath \'//div[@class="article-text"]//span[@itemprop="articleBody"]\'' # article body
            ' --output-format=json-wrapped')  # output as json
        if 'pogoda.unian.ua/' in url:
            cmd = (
                downloader_common.XIDEL_CMD.format(url) +
                ' --xpath \'//div[@class="news-details__info newsDetailsInfo news-container"]//div[@class="newsDetailsInfo__dateTime time"]\''  # datetime in format hh:mi, dd Month yyyy
                ' --xpath \'//div[@class="news-details__info newsDetailsInfo news-container"]//h1[@class="news-details__title"]\''  # title
                ' --xpath \'//div[@class="news-details__info newsDetailsInfo news-container"]//div[@class="newsDetailsInfo__main"]//h2\''  # summary
                ' --xpath \'//div[@class="news-details__info newsDetailsInfo news-container"]//div[@class="newsDetailsInfo__main"]//p\''  # article body
                ' --output-format=json-wrapped')  # output as json
        # print('cmd: '+cmd)
        # xidel http://www.unian.ua/society/46-ninishni-studenti-jitimut-pri-komunizmi.html -q --xpath '//section[@class="article-column"]//div[@class="meta"]//time[@itemprop="datePublished"]/@content'
        # xidel http://www.unian.ua/society/46-ninishni-studenti-jitimut-pri-komunizmi.html -q --xpath '//div[@class="article-text"]//span[@itemprop="articleBody"]//p'
        # xidel https://pogoda.unian.ua/news/2327629-2-sichnya-temperatura-v-ukrajini-zalishitsya-plyusovoyu-sinoptik.html -q --xpath '//div[@class="news-details__info newsDetailsInfo news-container"]//div[@class="newsDetailsInfo__dateTime"]'

        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        result = p.communicate()[0].decode('utf-8')
        # print(result)
        jsonArt = json.loads(result)

        if len(jsonArt) > 0 and 'pogoda.unian.ua/' not in url:
            cmd = (
                downloader_common.XIDEL_CMD.format(url) +
                ' --xpath \'//div[@class="article-text"]//span[@itemprop="articleBody"]//p\''
            )  # article text
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            result = p.communicate()[0].decode('utf-8')
            jsonArt.append('')
            jsonArt[3] = result

        article = None
        try:
            if len(jsonArt) > 0:
                article = Article(url, jsonArt)
            else:
                # logging.warning("Nothing can be load from: "+url)
                print("Nothing can be load from: " + url)
                return None

            if len(article.body
                   ) <= 1:  # article has only one row, download as html
                logging.debug("article has only one row, reload article body")
                text = " ".join(article.body)
                text = text.strip()
                bodyRead = False
                """
          if 'economics.unian.ua' in url:
              cmd = ('xidel '+url+' -q '
                 ' --xpath \'//div[@class="article-text"]/*[not(self::div[@class="article-meta"] or self::div[@class="newsfeed-box embed-code mobile-banner"])]\'') # article text
              p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
              result = p.communicate()[0].decode('utf-8')
              resultStr = str(result)
              if text in resultStr:
                  moreText = resultStr
                  if len(text) > 0:
                      moreText = resultStr.split(text,1)[1]
                  if len(moreText.strip()) > 0:
                      jsonArt[3] = result
                      bodyRead = True
          """

                if not bodyRead:
                    if len(text) > 0:  # article is not empty
                        cmd = (
                            downloader_common.XIDEL_CMD.format(url) +
                            ' --xpath \'//div[@class="article-text"]//span[@itemprop="articleBody"]//p\''  # article text
                            ' --output-format=html')  # output as html
                        jsonArt[3] = self.loadArticleTextFromHtml(cmd)
                    else:
                        cmd = (
                            downloader_common.XIDEL_CMD.format(url) +
                            ' --xpath \'//div[@class="article-text"]//span[@itemprop="articleBody"]//div\''
                        )  # article text
                        p = subprocess.Popen(
                            cmd, shell=True, stdout=subprocess.PIPE)
                        result = p.communicate()[0].decode('utf-8')
                        if len(str(result).strip()) == 0:
                            cmd = (
                                downloader_common.XIDEL_CMD.format(url) +
                                ' --xpath \'//div[@class="article-text"]//p\''
                            )  # article text
                            p = subprocess.Popen(
                                cmd, shell=True, stdout=subprocess.PIPE)
                            result = p.communicate()[0].decode('utf-8')
                        jsonArt[3] = result

                article2 = None
                try:
                    article2 = Article(url, jsonArt)
                except:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    print("Unexpected error: ", exc_type, "In article ",
                          result)
                    traceback.print_exception(exc_type, exc_value,
                                              exc_traceback)

                if article2 is not None and len(article.body) < len(
                        article2.body):
                    return article2
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print("Unexpected error: ", exc_type, "In article ", result)
            traceback.print_exception(exc_type, exc_value, exc_traceback)

        return article

    def loadArticleTextFromHtml(self, xidelCmd):
        p = subprocess.Popen(xidelCmd, shell=True, stdout=subprocess.PIPE)
        origHtml = p.communicate()[0].decode('utf-8')
        logging.debug(">> loadArticleTextFromHtml()")
        logging.debug(origHtml)
        # print(result)
        html = origHtml.replace('<br>', '[br]').replace('</br>', '').replace(
            '<br/>', '[br]').replace('</p>', '[br]</p>').replace(
                '<div>', '<div>[br]').replace('</div>', '[br]</div>').replace(
                    '<br />', '[br]')
        html = html.replace('<BR>', '[br]').replace('</BR>', '').replace(
            '</P>', '[br]</P>').replace('<BR />', '[br]')
        logging.debug(">> replace with [br]")
        logging.debug(html)
        soup = BeautifulSoup(html, 'html.parser')
        # remove scripts
        [s.extract() for s in soup('script')]
        txt = soup.get_text()
        return txt.replace('[br]', '\n')

    def fb2(self, date):
        # strdate = '%d.%d.%d' % (date.day, date.month, date.year)
        today = datetime.date.today()
        url = self.baseUrl + '/news/archive/' + date.strftime('%Y%m%d')
        articleList = self.getNewsForDate(date)
        if len(articleList) < 1:
            return ''
        ret = '<?xml version="1.0" encoding="utf-8"?>'
        ret += '\n<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">'
        ret += '\n<description>'
        ret += '\n <title-info>'
        ret += '\n  <genre>nonfiction</genre>'
        ret += '\n  <author><last-name>УНІАН</last-name></author>'
        ret += '\n  <book-title>УНІАН. Новини ' + date.strftime(
            '%d.%m.%Y') + '</book-title>'
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
            except Exception:
                print("Article ", article.info(), "Unexpected error: ", sys.exc_info()[0])
        ret += '\n</body>'
        ret += '\n</FictionBook>'
        return ret

"""
    def load(self, sDateFrom, sDateTo):
        logging.basicConfig(
            filename='downloader_unian.log', level=logging.INFO)
        date = datetime.datetime.strptime(sDateFrom, '%d.%m.%Y').date()
        dateTo = datetime.datetime.strptime(sDateTo, '%d.%m.%Y').date()

        while (date < dateTo):
            content = self.fb2(date)
            if len(content) > 0:
                with open(self.rootPath + '/unian/' + str(date.year) +
                          '/unian_' + str(date) + '.fb2', "w") as fb2_file:
                    fb2_file.write(content)
            date += datetime.timedelta(days=1)
        logging.info("Job completed")
"""

"""
strdate = '12.04.2012'
date = datetime.datetime.strptime(strdate, '%d.%m.%Y').date()
downloader.getNewsForDate(date)

downloader = Downloader(".")
logging.basicConfig(filename='downloader_unian_debug.log',level=logging.DEBUG)
article = downloader.loadArticle('https://pogoda.unian.ua/news/2327629-2-sichnya-temperatura-v-ukrajini-zalishitsya-plyusovoyu-sinoptik.html')
print(article.info())

"""
if __name__ == '__main__':
    run()
