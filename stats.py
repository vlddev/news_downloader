import re
import sys
import logging
from collections import Counter

# TODO use https://bitbucket.org/spirit/guess_language
#      for language detection

class TextStats(object):
  def __init__(self, text):
    self.text = text
    self.text_lower = text.lower()
    self.words = re.findall(r'\w+', text.lower())
    self.stats = Counter(self.words)
    self.common_text_20 = self.stats.most_common(20)
    self.dict_20 = dict(self.common_text_20)

  def isUkr(self):
    #common_words = ['і','не','на','що','я','в','з','а','у','й']
    common_words = ['і','що','з','у','й','та','від','але','це','про','або','як','чи']
    commonInText = 0
    #print(common_text)
    for word in common_words:
      if word in self.dict_20:
        commonInText += 1
    #print('isUkr(): commonInText = '+str(commonInText))
    if commonInText > 2:
      return True
    else:
      return False

  def isRus(self):
    common_words = ['и','с','что','по','к','от','из','ни','как']
    commonInText = 0
    #print(common_text)
    for word in common_words:
      if word in self.dict_20:
        commonInText += 1
    #print('isRus(): commonInText = '+str(commonInText))
    if commonInText > 2:
      return True
    else:
      return False

  def hasRusLetter(self):
    if 'э' in self.text_lower or 'ы' in self.text_lower or 'ъ' in self.text_lower:
      return True
    else:
      return False

  def hasUkrLetter(self):
    if 'і' in self.text_lower or 'ї' in self.text_lower or 'є' in self.text_lower:
      return True
    else:
      return False

  def countRusLetters(self):
    ret = self.text_lower.count('э')
    ret += self.text_lower.count('ы')
    ret += self.text_lower.count('ъ')
    return ret

  def countUkrLetters(self):
    ret = self.text_lower.count('і')
    ret += self.text_lower.count('ї')
    ret += self.text_lower.count('є')
    return ret

  def isEng(self):
    common_words = ['the','of','to','and','that','in']
    commonInText = 0
    for word in common_words:
      if word in self.dict_20:
        commonInText += 1
    if commonInText > 2:
      return True
    else:
      return False

  def isStoreText(self):
    ret = True
    retMsg = ''
    if len(self.text) > 0:
      if self.isUkr() and self.isRus():
        ret = False
        retMsg = "IGNORE: Article is Ukr and Rus."
        logging.info("   stats: "+str(self.common_text_20))
      elif self.isRus():
        ret = False
        retMsg = "IGNORE: Article is Rus."
      elif self.isEng():
        ret = False
        retMsg = "IGNORE: Article is Eng."
      elif not (self.isUkr() or self.isRus() or self.isEng()):
        if self.hasRusLetter() and self.hasUkrLetter():
          cntUkr = self.countUkrLetters()
          cntRus = self.countRusLetters()
          if cntUkr > cntRus :
            ret = True
          else:
            ret = False
            retMsg = "IGNORE: Article (language not detected) has %d Rus and %d Ukr letters." % (cntRus, cntUkr)
        elif self.hasRusLetter():
          ret = False
          retMsg = "IGNORE: Article (language not detected) has Rus letters."
        elif self.hasUkrLetter():
          ret = True
        elif len(self.text) < 450: #ignore article
          ret = False
          retMsg = "IGNORE: Article language is not detected."
          logging.info("   text length: "+ str(len(self.text)))
          logging.info("   stats: "+str(self.common_text_20))
        else:
          ret = False
          retMsg = "IGNORE: Article language is not detected."
          logging.error("Article language not detected.")
          logging.info("   text length: "+ str(len(self.text)))
          logging.info("   stats: "+str(self.common_text_20))
          sys.exit("Article language not detected.")
    else:
      retMsg = "IGNORE: Empty article."
      ret = False
    return (ret, retMsg)