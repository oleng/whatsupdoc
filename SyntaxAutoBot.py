#!/usr/bin/env python
""""
[SyntaxBot] Python documentation bot <auto> for Reddit by /u/num8lock
version:    v.0.9
Notes:      praw4 (see requirements.txt)
            [Heroku] uses env variables for all authentication credentials
Acknowledgment:
            Codes based on many reddit bot creators /u/redditdev
            and helps from /r/learnpython.
            Thanks to:
            - u/w1282 for reminding what function in programming function means
            - u/bboe for authoring praw and making it easier to use reddit API
"""
import os
import re
import time
from datetime import datetime
import logging, logging.config
import praw
import requests
import ast
from sqlalchemy import create_engine, exists
from sqlalchemy.orm import sessionmaker
from docdb import Library as libdb 
from docdb import RedditActivity as reddb

''' CONFIGS '''
# Retrieve (Heroku) env private variables
ua          = 'Python Syntax help bot <auto> for reddit v.1 (by /u/num8lock)'
appid       = os.getenv('syntaxbot_app_id')
secret      = os.getenv('syntaxbot_app_secret')
botlogin    = os.getenv('syntaxbot_username')
passwd      = os.getenv('syntaxbot_password')
db_config   = os.getenv('DATABASE_URL')
# Reddit related variables
baseurl     = 'docs.python.org'
sub_list    = ['SyntaxBot', 'learnpython']
sortfilter  = 'new'
timefilter  = 'day'
postlimit   = 100
# regex pattern for capturing definition url. Need to have everything 
# captured between the identifiers
urlpattern = re.compile(r"""(?P<version>[32]/)(?P<topic>\w+/)
    (?P<page>[\w\.]+\.html)(?P<syntax>[\?#\w=\.]+)""", re.I | re.X)


def check_replied(comment):
    """check if comment is already saved in profile"""
    log.debug('Checking if replied... %s', comment)
    saved_comments = r.user.me().saved()
    for saved in saved_comments:
        log.debug('Match post? saved: %s, %s', saved, comment)
        if saved == comment.id:
            log.info('Found as saved: %s, %s', saved, comment)
            # save data to db
            return True
        else: 
            log.info('This saved not matching comment. %s, %s', saved, comment)
            continue
    # not saved yet
    return False


def contain_url(comment):
    """Searching valid url in comment, if found, return the regex pattern match, 
    if not return False"""
    # to find if submision or comment : stackoverflow.com/a/17431054/6882768
    if not hasattr(comment, 'body'):
        log.error('A submission. Searching selftext %s', comment.id)
        found = re.search(urlpattern, comment.selftext)
        log.debug('Contains valid URL? %s : %s', found, comment.selftext)
    else:
        log.debug('Comment in submission: %s', comment.submission)
        found = re.search(urlpattern, comment.body)
        log.debug('Contains valid URL? %s : %s', found, comment.body)

    if found is None:
        log.error('Error: cannot find url in %s', comment)
        return False

    _url = '{0}'.format( found.group(0) )
    log.debug('Contains valid url: %s', found.groupdict())

    return found


def querydb(data):
    """Get query definitions from libdb database"""
    if not data:
        log.error('querydb: No url to query.')
        return None
    log.info('Start querying db for %s', data)
    _strip = re.compile(r'\?highlight=\w+\#|\#')
    wordstrip = re.search(_strip, data.group(4))
    if wordstrip is not None:
        _syntax = data.group(4).replace(wordstrip.group(0), '')
        log.debug('Stripped: %s', _syntax)
    else:
        _syntax = data.group(4)
    _version = data.group(1).rstrip('/')
    _topic = data.group(2).rstrip('/')
    _module = data.group(3).rstrip('.html')

    log.debug("Getting definition from db: %s", [_version, _module, _syntax])
    # DB queries
    # Data needed to process a reply:
    columns = [ libdb.id, libdb.version_id, libdb.module, libdb.keywords, 
                libdb.header, libdb.body, libdb.footer, libdb.url ]

    log.info('> Query check: Version: `%s`. Module: `%s`, Keyword: `%s`', 
                _version, _module, _syntax)
    # check if keyword exists
    check = session.query(exists().where(
                libdb.module == _module).where(
                libdb.keywords.contains(_syntax))).scalar()
    log.debug('> Exists? check: %s.', check)
    
    if check:
        log.info('Starting query')
        _query = session.query(*columns).filter(
                (libdb.module == _module) & 
                (libdb.keywords.contains(_syntax))
                ).group_by(libdb.module, libdb.id).order_by(libdb.id).first()
        log.info('Library returns: id: %s, vers: %s, syntax: %s', 
                    _query.id, _query.version_id, _query.keywords)
        return _query
    else:
        # since only version 3 stored in Heroku postgres lets replace _version
        url_full = 'https://{0}/{1}/{2}/{3}.html#{4}'.format(
            baseurl, '3', _topic, _module, _syntax)
        log.error('Cannot found %s for constructed url %s', _syntax, url_full)
        return None


def format_response(data, comment):
    """Format bot reply"""
    if data is None:
        return False

    botreply = """Hi, I'm a bot being developed to get Python syntax 
            definition. I noticed you included a link to this syntax in your 
            post, so here's the entry from Python 3 official documentation: 
            \n\n{0} \n {1} \n {2}""".format(data.header, data.body, data.footer)
    return botreply


def reply(comment):
    """Reply user comment"""
    log.info('Start replying...{}'.format( {comment.id: 
        [datetime.utcfromtimestamp(comment.created_utc), comment.author.name]}))
    response_data = querydb(contain_url(comment))
    # pass comment too for logging purpose
    bot_response = format_response(response_data, comment)
    log.debug('Reply message: %s', bot_response)
    if bot_response:
        comment.reply(bot_response)
        comment.save(category='comment_replied')
        justnow = datetime.utcnow()
        log.info('Pause: 5secs.')
        time.sleep(5)
        log.info('Checking if reply posted:...')  
        if check_replied(comment):
            log.info('Replied and saved: %s', comment.id)
        else:
            log.error('Comment %s not saved at %s', comment.id, justnow)
    else:
        log.info('Nothing to reply for %s', comment.id)

def scan_submission(subreddit, sort, time, limit):
    ''' Search for the queries in the sub using reddit search, time filtered 
    '''
    search_result = r.subreddit(subreddit).search('{0}'.format(
                    baseurl), sort=sort, time_filter=time, limit=limit)
    log.info('Search result: sub %s, found %s', search_result.url, 
        search_result.yielded)
    log.debug('Search result: {}'.format(search_result.__dict__))
    if search_result is None or search_result.yielded == 0:
        log.info('No matching result.')
        return None
    for thread in search_result:
        ''' get OP thread / submission to iterate comment/replies '''
        log.info('Iterating threads in search result : %s', thread)
        # iterate every comments and their replies
        submission = r.submission(id=thread)
        submission.comments.replace_more(limit=0)
        log.info('Processing comment tree: {} [{}]: {}'.format(
            submission, submission.author, submission.comments.list() ))
        # check OP
        op_replied = check_replied(submission)
        if op_replied:
            log.info('Skipping submission %s: replied', submission)
        elif not op_replied:
            reply(submission)
        # check comment forest
        for comment in submission.comments.list(): 
            # skip own & replied comment
            if comment.author == botlogin:
                log.info('Skipping own comment: %s', comment)
                continue
            elif check_replied(comment):
                log.info('Skipping comment %s: replied', comment)
                continue
            # skip non-query comment
            elif not contain_url(comment):
                log.info('Skipping comment %s: no url found', comment)
                continue
            else:
                reply(comment)
    # Finished scanning this sub
    return True


def scan_comments(subreddit):
    """Use Pushshift API to search comments, hardcoded to default to the last
    3 days. See https://redd.it/5gawot for API v2 documentation"""
    _endpoint = 'https://apiv2.pushshift.io/reddit/comment/search/'
    _fields = ['author', 'body', 'created_utc', 'id', 'link_author', 
                'link_created_utc', 'link_id', 'link_num_comments', 
                'link_permalink', 'parent_id', 'url']
    _args = '?q={0}&subreddit={1}&sort=desc&after=3d&fields={2}'.format(
                baseurl, subreddit, ','.join(_fields))
    url = _endpoint + _args
    r = requests.get(url)
    log.debug('[%s] sub: %s, content: %s', r, subreddit, r.content)

def whatsub_doc(subreddits):
    """Main bot activities & limit rate requests to oauth.reddit.com"""
    log.info('Whatsub, doc?')
    for sub in subreddits:
        log.info('Searching for submissions.')
        submissions = scan_submission(sub, sortfilter, timefilter, postlimit)
        log.info('Bot sleep interval to avoid spamming %s: 30s', sub)
        if submissions is not None:
            # avoid spamming-like activity, add some sleep interval    
            log.info('Finished scanning %s, sleeping for 30s.', sub)
            time.sleep(30)
        log.info('Searching for comments.')
        comments = scan_comments(sub)

    log.info('Done.')


def login():
    """praw4 OAuth2 login procedure"""
    ''' praw4 only needs the first 3 for read-only mode '''
    log.info('Logging started')
    r = praw.Reddit(user_agent=ua, client_id=appid, client_secret=secret, 
        username=botlogin,
        password=passwd
        )
    ''' log connection '''
    log.info('Connected. Starting bot activity')
    return r


if __name__ == '__main__':
    log = logging.getLogger(__name__)
    logging.config.dictConfig(ast.literal_eval(os.getenv('WHATSUPDOC_CFG')))
    engine = create_engine(db_config, echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    ''' capture exceptions '''
    try:
        r = login()
        whatsub_doc(sub_list)
    except ConnectionError as no_connection:
        log.error(no_connection, exc_info=True)
        time.sleep(10)
        log.info('Reconnecting in 10secs...')
        r = login()
        whatsub_doc(sub_list)
