#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import multiprocessing
from datetime import date, datetime, time
import os
import gensim
from gensim.models import KeyedVectors
import logging
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
import itertools
import glob
params = {'size': 200, 'iter' : 10,  'window': 10, 'min_count': 10,'workers': max(1, multiprocessing.cpu_count() -1), 'sample': 1E-3,}

date_regex = re.compile('(\
([1-9]|0[1-9]|[12][0-9]|3[01])\
[-/.\s+]\
(1[1-2]|0[1-9]|[1-9]|Ιανουαρίου|Φεβρουαρίου|Μαρτίου|Απριλίου|Μαΐου|Ιουνίου|Ιουλίου|Αυγούστου|Νοεμβρίου|Δεκεμβρίου|Σεπτεμβρίου|Οκτωβρίου|Ιαν|Φεβ|Μαρ|Απρ|Μαϊ|Ιουν|Ιουλ|Αυγ|Σεπτ|Οκτ|Νοε|Δεκ)\
(?:[-/.\s+](1[0-9]\d\d|20[0-9][0-8]))?)')

class Minister:

	def __init__(self, name, middle, surname, ministry):
		self.name = name
		self.surname = surname
		self.ministry = ministry
		self.middle = middle

	def is_mentioned(self, s):
		search_full = re.search(self.name + ' ' + self.surname, s)
		if search_full != None:
			return search_full.span()
		search_sur = re.search(self.surname, s)
		if search_sur != None:
			return search_sur.span()
		search_min = re.search(self.ministry, s)
		if search_min != None:
			return search_min.span()

	def __repr__(self):
		return '{} {}'.format(self.name, self.surname)


ministers = [
Minister('ΠΡΟΚΟΠΙΟΣ', 'Β.', 'ΠΑΥΛΟΠΟΥΛΟΣ', 'ΠΡΟΕΔΡΟΣ ΤΗΣ ΔΗΜΟΚΡΑΤΙΑΣ'),
Minister('ΔΗΜΟΣ', '', 'ΠΑΠΑΔΗΜΗΤΡΙΟΥ', 'Οικονομίας και Ανάπτυξης'),
Minister('ΕΛΕΝΑ', '', 'ΚΟΥΝΤΥΡΑ', 'Τουρισμού'),
Minister('ΣΤΑΥΡΟΣ', '', 'ΚΟΝΤΟΝΗΣ', 'Δικαιοσύνης'),
Minister('ΚΩΝΣΤΑΝΤΙΝΟΣ', '', 'ΓΑΒΡΟΓΛΟΥ', 'Παιδείας, Έρευνας και Θρησκευμάτων')
]



def edit_distance(str1, str2, weight = lambda s1,s2, i, j: 0.75 if s1[i-1] == ' ' or s2[j-1] == ' ' else 1):
		m, n = len(str1), len(str2)
		dp = [[0 for x in range(n+1)] for x in range(m+1)]

		for i in range(m+1):
			for j in range(n+1):

				if i == 0:
					dp[i][j] = j

				elif j == 0:
					dp[i][j] = i
				elif str1[i-1] == str2[j-1]:
					dp[i][j] = dp[i-1][j-1]

				else:
					dp[i][j] = weight(str1,str2,i,j) + min(dp[i][j-1],
									   dp[i-1][j],
									   dp[i-1][j-1])
		return dp[m][n]

MONTHS_PREFIXES = {
	'Ιανουαρίο' : 1,
	'Φεβρουαρίο' : 2,
	'Μαρτίο' : 3,
	'Απριλίο' : 4,
	'Μαΐο' : 5,
	'Ιουνίο' : 6,
	'Ιουλίο' : 7,
	'Αυγούστο' : 8,
	'Σεπτέμβριο' : 9,
	'Οκτωβρίο' : 10,
	'Νοεμβρίο' : 11,
	'Δεκεμβρίο' : 12,
}


class IssueParser:

	def __init__(self, filename, toTxt = False):
		self.filename = filename
		self.lines  = []
		with open(filename, 'r') as infile:
			tmp_lines = infile.read().splitlines()
		for line in tmp_lines:
			if line == '': continue
			elif line.startswith('Τεύχος'): continue
			else:  self.lines.append(line)

		self.dates = []
		self.find_dates()
		self.articles = {}
		self.sentences = {}
		self.find_articles()

	def find_dates(self):
		for i, line in enumerate(self.lines):
			result = date_regex.findall(line)
			if result != []:
				self.dates.append((i, result))

		if self.dates == []:
			raise Exception('Could not find dates!')

		full, day, month, year = self.dates[0][1][0]

		for m in MONTHS_PREFIXES.keys():
			if month == m + 'υ':
				month = MONTHS_PREFIXES[m]
				break

		self.issue_date = date(int(year), month, int(day))
		self.signed_date = self.dates[-1]
		return self.dates

	def find_articles(self, min_extract_chars = 100):
		article_indices = []
		for i, line in enumerate(self.lines):
			if line.startswith('Άρθρο') or line.startswith('Ο Πρόεδρος της Δημοκρατίας'):
				article_indices.append((i, line))
				self.articles[line] = ''


		for j in range(len(article_indices) - 1):
			self.articles[article_indices[j][1]] = ''.join(self.lines[article_indices[j][0] + 1 :  article_indices[j+1][0]])

		self.extracts = {}

		for article in self.articles.keys():
			# find extracts
			left_quot = [m.start() for m in re.finditer('«', self.articles[article])]
			right_quot = [m.start() for m in re.finditer('»', self.articles[article])]
			left_quot.extend(right_quot)
			temp_extr = sorted ( left_quot )
			res_extr = []
			c = '«'
			for idx in temp_extr:
				if c == '«' and self.articles[article][idx] == c:
					res_extr.append(idx)
					c = '»'
				elif c == '»' and self.articles[article][idx] == c:
					res_extr.append(idx)
					c = '«'
			self.extracts[article] = list ( zip(res_extr[::2], res_extr[1::2]) )

			# drop extracts with small chars
			self.extracts[article] = list ( filter(lambda x: x[1] - x[0] + 1 >= min_extract_chars, self.extracts[article] ) )



			tmp = self.articles[article].strip('-').split('.')

			# remove punctuation
			tmp = [re.sub(r'[^\w\s]','',s) for s in tmp]
			tmp = [line.split(' ') for line in tmp]
			self.sentences[article] = tmp


	def get_extracts(self, article):
		for i, j in self.extracts[article]:
			yield self.articles[article][i + 1 : j]



	def all_sentences(self):
		for article in self.sentences.keys():
			for sentence in self.sentences[article]:
				yield sentence


	def detect_signatories(self):
		self.signatories = set([])
		for i, line in enumerate( self.lines ):
			if line.startswith('Ο Πρόεδρος της Δημοκρατίας'):
				minister_section = self.lines[i:]
				break

		for i, line in enumerate(minister_section):
			for minister in ministers:
				x = minister.is_mentioned(line)
				if x != None:
					self.signatories |= set([minister])

		for signatory in self.signatories:
			print(signatory)

		return self.signatories




	def train_word2vec(self):

		self.all_sentences = [sentence for sentence in self.all_sentences()]

		self.model = gensim.models.Word2Vec(self.all_sentences, **params)
		print('Model train complete!')
		self.model.wv.save_word2vec_format('model')




def generate_model_from_government_gazette_issues(directory='data'):
	cwd = os.getcwd()
	os.chdir(directory)
	filelist = glob.glob('*.pdf'.format(directory))
	issues = []
	all_sentences = []
	for filename in filelist:
		outfile = filename.strip('.pdf') + '.txt'
		if not os.path.isfile(outfile):
			os.system('pdf2txt.py {} > {}'.format(filename, outfile))
		issue = IssueParser(outfile)
		all_sentences.extend(issue.all_sentences())
		issues.append(issue)
	model = gensim.models.Word2Vec(all_sentences, **params)

	os.chdir(cwd)
	return issues, model

issues, model = generate_model_from_government_gazette_issues()

print(model.most_similar(positive=['Υπουργός', 'Υπουργείο']))

issue = IssueParser('data/ocument1.txt')
print(issue.extracts['Άρθρο 1'])
for article in issue.articles.keys():
	print('Article : ' + article)
	for e in issue.get_extracts(article):
		print(e)
