import re
import operator
from collections import defaultdict
import multiprocessing
import unicodedata
import logging
from gensim.corpora import WikiCorpus, MmCorpus

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

wiki = WikiCorpus("elwiki-latest-pages-articles.xml.bz2",lemmatize=False, dictionary={})

intonations = {
    'ά': 'α',
    'έ': 'ε',
    'ί': 'ι',
    'ό': 'ο',
    'ύ': 'υ',
    'ή': 'η',
    'ώ': 'ω'
}


def normalize_word(s):
    s = s.strip('-')
    global intonations
    for key, val in intonations.items():
        s = s.replace(key, val)
    return s


# english language about 300 stop-words.
num_of_words=350
my_dict=defaultdict(int)
sentences = list(wiki.get_texts())
for sentence in sentences:
	for word in sentence:
		my_dict[normalize_word(word)]+=1



# sorted based on their frequencies
sorted_tuple=sorted(my_dict.items(),key=operator.itemgetter(1),reverse=True)
count=0
my_list=[]
for i in sorted_tuple:
	if (count>num_of_words):
		break
	count+=1
	if (len(i[0])>1):
		my_list.append(i[0])
previous='α'
# sorts strings after removing accents
for i in sorted(my_list):
	# new line when letter changes
	if (i[0]!=previous):
		previous=i[0]
		print()
	print("{} ".format(i),end='')
