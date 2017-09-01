import re
from collections import Counter

# TODO use https://bitbucket.org/spirit/guess_language
#      for language detection

class TextStats(object):
  def __init__(self, text):
    self.text = text
    self.text_lower = text.lower()
    self.words = re.findall('\w+', text.lower())
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
