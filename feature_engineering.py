# -*- coding: utf-8 -*-
"""feature engineering.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/18QWjhzl8Wd2dN9MPauTcYxMCfbWF5dhr
"""

# !pip install distance
# !pip install fuzzywuzzy

import numpy as np
import pandas as pd
import re
import warnings

warnings.filterwarnings("ignore")
import distance
from nltk.stem import PorterStemmer
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
import nltk

nltk.download('stopwords')
from nltk.corpus import stopwords
import pickle
from scipy.spatial.distance import cosine, cityblock, canberra, euclidean, minkowski
import gensim

class FeatureEngineering:

    def __init__(self):
        self.glove_model = []
        self.SAFE_DIV = 0.0001
        with open('glove_model.pickle', 'rb') as handle:
            self.glove_model = pickle.load(handle)
        self.STOP_WORDS = stopwords.words('english')

    def share_word_normalization(self, data):
        first_word = set(map(lambda word: word.lower().strip(), data['question1'].split(" ")))
        second_word = set(map(lambda word: word.lower().strip(), data['question2'].split(" ")))
        return 1.0 * len(first_word & second_word) / (len(first_word) + len(second_word))

    def two_question(self, question1, question2):
        df = pd.DataFrame(data=[[0, question1, question2]], columns=['test_id', 'question1', 'question2'])
        df_tm = self.text_mining(df)
        df = pd.DataFrame(data=[[0, question1, question2]], columns=['test_id', 'question1', 'question2'])
        df_nlp = self.extract_nlp(df)
        df_tm = df_tm.merge(df_nlp, on='test_id', how='left')
        df_tm = df_tm.drop(['question1', 'question2'], axis=1)
        return df_tm

    def common_word_normalization(self, data):
        first_word = set(map(lambda word: word.lower().strip(), data['question1'].split(" ")))
        second_word = set(map(lambda word: word.lower().strip(), data['question2'].split(" ")))
        return 1.0 * len(first_word & second_word)

    def total_word_normalization(self, data):
        first_word = set(map(lambda word: word.lower().strip(), data['question1'].split(" ")))
        second_word = set(map(lambda word: word.lower().strip(), data['question2'].split(" ")))
        return 1.0 * (len(first_word) + len(second_word))

    def get_2_gram_share(self, data):
        question1_str = str(data['question1']).lower().split()
        question2_str = str(data['question2']).lower().split()
        ques1_gram = set([i for i in zip(question1_str, question1_str[1:])])
        ques2_gram = set([i for i in zip(question2_str, question2_str[1:])])
        shared_gram = ques1_gram.intersection(ques2_gram)
        data_gram = 0 if len(ques1_gram) + len(ques2_gram) == 0 else len(shared_gram) / (len(ques1_gram) + len(ques2_gram))
        return data_gram

    def text_mining(self, df):
        df['ques1_len'] = df['question1'].str.len()
        df['ques2_len'] = df['question2'].str.len()
        df['len_diff'] = df['ques1_len'] - df['ques2_len']

        df['q1_word_len'] = df['question1'].apply(lambda row: len(row.split(" ")))
        df['q2_word_len'] = df['question2'].apply(lambda row: len(row.split(" ")))
        df['words_diff'] = df['q1_word_len'] - df['q2_word_len']

        df['q1_caps_count'] = df['question1'].apply(lambda x: sum(1 for i in str(x) if i.isupper()))
        df['q2_caps_count'] = df['question2'].apply(lambda x: sum(1 for i in str(x) if i.isupper()))
        df['caps_diff'] = df['q1_caps_count'] - df['q2_caps_count']

        df['q1_char_len'] = df['question1'].apply(lambda x: len(str(x).replace(' ', '')))
        df['q2_char_len'] = df['question2'].apply(lambda x: len(str(x).replace(' ', '')))
        df['diff_char_len'] = df['q1_char_len'] - df['q2_char_len']

        df['avg_word_len1'] = df['q1_char_len'] / df['q1_word_len']
        df['avg_word_len2'] = df['q2_char_len'] / df['q2_word_len']
        df['diff_avg_word'] = df['avg_word_len1'] - df['avg_word_len2']

        df['common_word'] = df.apply(self.common_word_normalization, axis=1)
        df['total_word'] = df.apply(self.total_word_normalization, axis=1)
        df['word_share'] = df.apply(self.share_word_normalization, axis=1)
        df['share_2_gram'] = df.apply(self.get_2_gram_share, axis=1)

        return df

    def data_preprocess(self, word):
        word = str(word).lower()
        word = word.replace(",000,000", "m").replace(",000", "k").replace("′", "'").replace("’", "'") \
            .replace("won't", "will not").replace("cannot", "can not").replace("can't", "can not") \
            .replace("n't", " not").replace("what's", "what is").replace("it's", "it is") \
            .replace("'ve", " have").replace("i'm", "i am").replace("'re", " are") \
            .replace("he's", "he is").replace("she's", "she is").replace("'s", " own") \
            .replace("%", " percent ").replace("₹", " rupee ").replace("$", " dollar ") \
            .replace("€", " euro ").replace("'ll", " will").replace("covid- 19", "corona virus 2019") \
            .replace("covid - 19", "corona virus 2019").replace('coronavirus', 'corona virus 2019') \
            .replace('corona virus', 'corona virus 2019')
        word = re.sub(r'([0-9]+)000000', r"\1m", word)
        word = re.sub(r"([0-9]+)000", r"\1k", word)

        porter = PorterStemmer()
        pattern = re.compile('\W')

        if type('') == type(word):
            word = re.sub(pattern, ' ', word)

        if type('') == type(word):
            word = porter.stem(word)
            test = BeautifulSoup(word)
            word = test.get_text()

        return word

    def remove_stop(self, question):
        question = str(question)
        if question is None or question == np.nan or question == 'NaN':
            return ' '

        after_stop = [i for i in question.split() if i not in self.STOP_WORDS]
        return ' '.join(after_stop)

    def word_mover_dis(self, ques1, ques2, model):
        ques1 = str(ques1)
        ques2 = str(ques2)
        ques1 = ques1.split()
        ques2 = ques2.split()
        return model.wmdistance(ques1, ques2)

    def extract_features(self, df):
        df["question1"] = df["question1"].fillna("").apply(self.data_preprocess)
        df["question2"] = df["question2"].fillna("").apply(self.data_preprocess)

        print("Extracting Token Features...")

        data_features = df.apply(lambda x: self.get_token_features(x["question1"], x["question2"]), axis=1)

        df["cwc_min"] = list(map(lambda x: x[0], data_features))
        df["cwc_max"] = list(map(lambda x: x[1], data_features))
        df["csc_min"] = list(map(lambda x: x[2], data_features))
        df["csc_max"] = list(map(lambda x: x[3], data_features))
        df["ctc_min"] = list(map(lambda x: x[4], data_features))
        df["ctc_max"] = list(map(lambda x: x[5], data_features))
        df["last_word_eq"] = list(map(lambda x: x[6], data_features))
        df["first_word_eq"] = list(map(lambda x: x[7], data_features))
        df["abs_len_diff"] = list(map(lambda x: x[8], data_features))
        df["mean_len"] = list(map(lambda x: x[9], data_features))

        print("Extracting Fuzzy Features..")

        df["token_set_ratio"] = df.apply(lambda x: fuzz.token_set_ratio(x["question1"], x["question2"]), axis=1)
        df["token_sort_ratio"] = df.apply(lambda x: fuzz.token_sort_ratio(x["question1"], x["question2"]), axis=1)
        df["fuzz_ratio"] = df.apply(lambda x: fuzz.QRatio(x["question1"], x["question2"]), axis=1)
        df["fuzz_partial_ratio"] = df.apply(lambda x: fuzz.partial_ratio(x["question1"], x["question2"]), axis=1)
        df["longest_substr_ratio"] = df.apply(lambda x: self.get_longest_substr_ratio(x["question1"], x["question2"]),
                                              axis=1)
        return df

    def g2w2v(self, list_of_sent, model, d):
        sent_vectors = []
        for sentence in list_of_sent:
            doc = [word for word in sentence if word in model.wv.vocab]
            if doc:
                sent_vec = np.mean(model.wv[doc], axis=0)
            else:
                sent_vec = np.zeros(d)
            sent_vectors.append(sent_vec)
        return sent_vectors

    def get_distance_features(self, df):

        print("Extracting Distance Features..")

        df['question1'] = df.question1.apply(self.remove_stop)
        df['question2'] = df.question2.apply(self.remove_stop)
        df['word_mover_dist'] = df.apply(
            lambda x: self.word_mover_dis(x['question1'], x['question2'], self.glove_model), axis=1)

        print("- word_mover_dis done...")

        ques1_list = list()
        ques2_list = list()

        for sentence in df.question1.values:
            ques1_list.append(sentence.split())
        for sentence in df.question2.values:
            ques2_list.append(sentence.split())

        g2w2v_ques1 = self.g2w2v(ques1_list, self.glove_model, 300)
        g2w2v_ques2 = self.g2w2v(ques2_list, self.glove_model, 300)

        print("- embedding done...")

        df['cosine_dist'] = [cosine(ques1, ques2) for (ques1, ques2) in zip(g2w2v_ques1, g2w2v_ques2)]
        df['cityblock_dist'] = [cityblock(ques1, ques2) for (ques1, ques2) in zip(g2w2v_ques1, g2w2v_ques2)]
        df['canberra_dist'] = [canberra(ques1, ques2) for (ques1, ques2) in zip(g2w2v_ques1, g2w2v_ques2)]
        df['euclidean_dist'] = [euclidean(ques1, ques2) for (ques1, ques2) in zip(g2w2v_ques1, g2w2v_ques2)]
        df['minkowski_dist'] = [minkowski(ques1, ques2) for (ques1, ques2) in zip(g2w2v_ques1, g2w2v_ques2)]

        print('- spatial distance done')

        df.cosine_dist = df.cosine_dist.fillna(0)
        df.word_mover_dist = df.word_mover_dist.apply(lambda wmd: 30 if wmd == np.inf else wmd)

        return df

    def get_token_features(self, ques1, ques2):
        features_list = [0.0] * 10

        ques1_tokens = ques1.split()
        ques2_tokens = ques2.split()

        if len(ques1_tokens) == 0 or len(ques2_tokens) == 0:
            return features_list

        ques1_words = set([word for word in ques1_tokens if word not in self.STOP_WORDS])
        ques2_words = set([word for word in ques2_tokens if word not in self.STOP_WORDS])

        ques1_stops = set([word for word in ques1_tokens if word in self.STOP_WORDS])
        ques2_stops = set([word for word in ques2_tokens if word in self.STOP_WORDS])

        common_word_count = len(ques1_words.intersection(ques2_words))
        common_stop_count = len(ques1_stops.intersection(ques2_stops))
        common_token_count = len(set(ques1_tokens).intersection(set(ques2_tokens)))

        features_list[0] = common_word_count / (min(len(ques1_words), len(ques2_words)) + self.SAFE_DIV)
        features_list[1] = common_word_count / (max(len(ques1_words), len(ques2_words)) + self.SAFE_DIV)
        features_list[2] = common_stop_count / (min(len(ques1_stops), len(ques2_stops)) + self.SAFE_DIV)
        features_list[3] = common_stop_count / (max(len(ques1_stops), len(ques2_stops)) + self.SAFE_DIV)
        features_list[4] = common_token_count / (min(len(ques1_tokens), len(ques2_tokens)) + self.SAFE_DIV)
        features_list[5] = common_token_count / (max(len(ques1_tokens), len(ques2_tokens)) + self.SAFE_DIV)
        features_list[6] = int(ques1_tokens[-1] == ques2_tokens[-1])
        features_list[7] = int(ques1_tokens[0] == ques2_tokens[0])
        features_list[8] = abs(len(ques1_tokens) - len(ques2_tokens))
        features_list[9] = (len(ques1_tokens) + len(ques2_tokens)) / 2

        return features_list

    def get_longest_substr_ratio(self, a, b):
        strs = list(distance.lcsubstrings(a, b))
        return 0 if len(strs) == 0 else len(strs[0]) / (min(len(a), len(b)) + 1)

    def extract_nlp(self, df):
        df = self.extract_features(df)
        df = self.get_distance_features(df)
        df = df.drop(['question1', 'question2'], axis=1)
        return df

    def feature_engineering(self, question):
        df = self.read_csv(question)
        df_tm = self.text_mining(df)
        df_2 = self.read_csv(question)
        df_nlp = self.extract_nlp(df_2)
        df_nlp = df_nlp.drop('answers', axis=1)
        df_tm = df_tm.merge(df_nlp, on='test_id', how='left')
        return df_tm
