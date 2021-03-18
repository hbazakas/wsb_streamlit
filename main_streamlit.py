from flask import Flask, request, render_template, session, redirect
import praw
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
from collections import Counter
#from nltk.corpus import stopwords
import streamlit as st
st.set_page_config(layout="wide")

def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

lottie_book = load_lottieurl('https://assets1.lottiefiles.com/packages/lf20_BiAtYn.json')
st_lottie(lottie_book, speed=0.25, height=200, key="initial")

st.title('Reddit Trend Scraping')
st.subheader('By Henry Bazakas')
col1, col2, col3 = st.beta_columns((3, 3, 2))

with col3: st.write("This page uses the last 6 hours of comments [r/wallstreetbets]('https://www.reddit.com/r/wallstreetbets/new/') and [r/satoshistreetbets]('https://www.reddit.com/r/satoshistreetbets/new/') to rank the 10 most talked about stocks and cryptocurrencies on Reddit right now. Scraping the data and tabulating the top tickers takes about 60 seconds. \n\nThese rankings are meant to be used for tracking trends and informing investment decisions. Invest at your own risk.")

st.write("This page was created by Henry Bazakas in March 2021. If you\'re interested in how it was built or in Henry\'s other work, take a look at his [Github]('https://github.com/hbazakas'). If you've made a fortune investing in securities you learned about here, please let him know via a [tweet]('https://twitter.com/bighenbazakas') or [LinkedIn]('https://www.linkedin.com/in/henry-bazakas-471201143/') message. Thanks for checking out this project!")

def comments_scraper(sub, comment_age, hot, case_sensitive = False):
    #Reddit API
    reddit = praw.Reddit(client_id='HG7dA6CRLvCD_w',
                     client_secret='rH5FP42F__la6jpUdt01BQvZU48WiA',
                     user_agent='WSB_Trends')

    posts = []
    subreddit = reddit.subreddit(sub)
    for post in subreddit.hot(limit = hot):
        posts.append([post.title, post.score, post.id, post.subreddit, post.url, post.num_comments, post.selftext, post.created])
    posts = pd.DataFrame(posts,columns=['title', 'score', 'id', 'subreddit', 'url', 'num_comments', 'body', 'created'])

    comment_count = 0
    comments = ""

    for post_id in posts.id:
        submission = reddit.submission(id=post_id)
        submission.comments.replace_more(limit=0)
        for comment in submission.comments.list():
            #Loops through all comments. comment.body is a string with each comment's contents.
            #comment.created is the time the comment was created.
            comment_age = (comment.created - time.time())/3600
            if comment_age <=comment_age:
                comments += comment.body + " "
                comment_count+=1
    if case_sensitive == False:
        comments = comments.upper()

    for character in'$ -.,\n!<>':
        comments = comments.replace(character, " ")

    comments = comments.split()
    comments_counter = Counter(comments)
    return(comments_counter)

def wsb_leaderboard(n, hours, hot):
    #Stock Tickers and Names
    wsb_ticker_list = []
    wsb_name_list = []
    URL = 'https://stockanalysis.com/stocks/'
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'lxml')
    wsb_tickers = soup.find_all('li')

    for i in wsb_tickers[12:-18]:
        #print(i.text.split(" - "))
        wsb_ticker_list.append(i.text.split(" - ")[0])
        wsb_name_list.append(i.text.split(" - ")[1])

    #Scrape Comments
    wsb_comments = comments_scraper('wallstreetbets', hours, hot, case_sensitive = True)

    #Reading in Stopwords
    stopword_df = pd.read_csv('stopwords.csv')
    stopwords_list = list(stopword_df.word)

    #Calculate Frequencies
    frequencies = []
    for tick in wsb_ticker_list:
        if tick not in stopwords_list:
            frequencies.append(wsb_comments[tick])
        else:
            frequencies.append(0)

    wsb_tickers_and_counts = pd.DataFrame([wsb_name_list, wsb_ticker_list, frequencies]).T
    wsb_tickers_and_counts.columns = ['Name','Ticker','Mentions']
    wsb_tickers_and_counts = wsb_tickers_and_counts.sort_values(by = ['Mentions'], ascending = False)[0:n]
    wsb_tickers_and_counts.index = range(1,n+1)
    return wsb_tickers_and_counts

def ssb_leaderboard(n, hours, hot):
    #Crypto Tickers and Names
    ssb_name_list = []
    ssb_ticker_list = []
    URL = 'https://coinmarketcap.com/all/views/all/'
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'lxml')
    ssb_names = soup.find_all('td',
                            class_ = 'cmc-table__cell cmc-table__cell--sticky cmc-table__cell--sortable cmc-table__cell--left cmc-table__cell--sort-by__name')
    ssb_tickers = soup.find_all('td',
                            class_ = 'cmc-table__cell cmc-table__cell--sortable cmc-table__cell--left cmc-table__cell--sort-by__symbol')

    for i in range(len(ssb_names)):
        ssb_name_list.append(ssb_names[i].text.split('\">"')[0])
        ssb_ticker_list.append(ssb_tickers[i].text.split('\">"')[0])

    #Scrape Comments
    ssb_comments = comments_scraper('satoshistreetbets', hours, hot, case_sensitive = True)

    #Reading in Stopwords
    stopword_df = pd.read_csv('stopwords.csv')
    stopwords_list = list(stopword_df.word)

    frequencies = []
    for coin in range(len(ssb_name_list)):
        freq = 0
        #print(name_list[coin], ticker_list[coin])
        if ssb_name_list[coin] not in stopwords_list:
            freq+=ssb_comments[ssb_name_list[coin]]
        else:
            freq+=0
        if ssb_ticker_list[coin] not in stopwords_list:
            freq+=ssb_comments[ssb_ticker_list[coin]]
        else:
            freq+=0
        frequencies.append(freq)

    ssb_tickers_and_counts = pd.DataFrame([ssb_name_list, ssb_ticker_list, frequencies]).T
    ssb_tickers_and_counts.columns = ['Name','Ticker','Mentions']
    ssb_tickers_and_counts = ssb_tickers_and_counts.sort_values(by = ['Mentions'], ascending = False)[0:n]
    ssb_tickers_and_counts.index = range(1,n+1)
    return ssb_tickers_and_counts

def assemble_rankings(n, hours, hot):
    print("Task Starting.")
    start = time.time()

    wsb = wsb_leaderboard(n, hours, hot)
    ssb = ssb_leaderboard(n, hours, hot)

    end = time.time()
    print(f"Finished in {end-start}")
    return wsb, ssb

wsb, ssb = assemble_rankings(10, 6, 15)

col1.header("r/wallstreetbets leaderboard")
col1.write(wsb)

col2.header("r/satishistreetbets leaderboard")
col2.write(ssb)
