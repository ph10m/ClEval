from IPython.core.display import display, HTML
from .html_template import transform_to_tree, span_wrapper

import pandas as pd
import numpy as np

def unify_data_format(fn):
    def unified_data(data, **kwargs):
        if kwargs.get('stanford', False):
            tokens, clusters = stanford_data_adapter(data)
        if kwargs.get('corenlp', False):
            tokens, clusters = corenlp_data_adapter(data)
        if kwargs.get('allen', False):
            tokens, clusters = allen_data_adapter(data)
        if kwargs.get('huggingface', False):
            tokens, clusters = huggingface_data_adapter(data)
        if kwargs.get('proref', False):
            tokens, clusters = labelled_pronoun(data)

        return fn(tokens, clusters, **kwargs)

    return unified_data

# Either return the html string or rander in a jupyter notebook output
# Function signature based on displacy render functionality
@unify_data_format
def render(tokens,
            clusters,
            style='coref', 
            stanford=False,
            corenlp=False,
            allen=False, 
            huggingface=False, 
            proref=False,
            jupyter=True):

    #print("tokens:", tokens)
    #print("clust:", clusters)
    html = to_html(tokens, clusters)

    if jupyter:
        display(HTML(html))
    else:
        return html

def raw_render(tokens, clusters):
    html = to_html(tokens, clusters)
    display(HTML(html))

def stanford_data_adapter(data):
    sents = []
    for sent in data['sentences']:
        sents.append([])
        for token in sent['tokens']:
            sents[-1].append(token['originalText'])

    clusters = []
    if data['corefs'] is not None:
        for num, mentions in data['corefs'].items():
            clusters.append([])
            for mention in mentions:
                start = np.cumsum([0]+list(map(len, sents)))[mention['sentNum']-1] + mention['startIndex']-1
                end = np.cumsum([0]+list(map(len, sents)))[mention['sentNum']-1] + mention['endIndex']-2
                clusters[-1].append([start, end])
            
    return sum(sents, []), clusters

# tollef jørgensen, 12.05.2020
def corenlp_data_adapter(data):
    tokens = []
    for sent in data.sentence:
        #print(sent.token)
        tokens.extend([t.value for t in sent.token])

    corefs = data.corefChain
    clusters = []
    
    for coref in corefs:
        mentions = list(coref.mention)
        mentionclusters = []
        for m in mentions:
            start = m.beginIndex
            end = m.endIndex
            head = m.headIndex
            sentidx = m.sentenceIndex
            sent_by_idx = data.sentence[sentidx]
            offset = sent_by_idx.tokenOffsetBegin
            sent_toks = [tok.value for tok in sent_by_idx.token]
            mentionclusters.append([offset + start, offset + end - 1])
        clusters.append(mentionclusters)
    return tokens, clusters
    

def allen_data_adapter(data):
    return data['document'], data['clusters']

def huggingface_data_adapter(doc):
    tokens = [token.text for token in doc]

    clusters = []
    if doc._.coref_clusters is not None:
        for cluster in doc._.coref_clusters:
            clusters.append([])
            for mention in cluster.mentions:
                clusters[-1].append([mention.start, mention.end-1])

    return tokens, clusters

def labelled_pronoun(row):
    txt = row.text

    # map char indices to token indices
    tokens = txt.split(' ')
    start_a = len(txt[:row.a_offset].split(' '))-1
    start_b = len(txt[:row.b_offset].split(' '))-1

    clusters = [[[start_a, start_a+len(row.a.split(' '))-1]], [[start_b, start_b+len(row.b.split(' '))-1]]]

    # add pronoun token to the labelled cluster
    start_p = len(txt[:row.pronoun_offset].split(' '))-1
    if row.a_coref:
        clusters[0].append([start_p, start_p+len(row.pronoun.split(' '))-1])
    elif row.b_coref:
        clusters[1].append([start_p, start_p+len(row.pronoun.split(' '))-1])
    else:
        clusters.append([[start_p, start_p+len(row.pronoun.split(' '))-1]])

    return tokens, clusters
    
def to_html(tokens, clusters):
    tree = transform_to_tree(tokens, clusters)
    html = ''.join(span_wrapper(tree, 0))
    html = '<div style="padding: 16px;">{}</div>'.format(html)
    return html