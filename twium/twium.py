import json
import os
import re
from urllib import parse

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from search import SearchManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class AltApi:
    is_authenticated = False
    search_manager: SearchManager = None

    BASE_URL = 'https://twitter.com'
    BASE_MOBILE_URL = 'https://mobile.twitter.com'

    def __init__(self, timeout=10, debug=False):
        self.debug = debug
        self.timeout = timeout

        self._start()

    def _start(self):
        options = webdriver.ChromeOptions()
        if not self.debug:
            options.add_argument('--headless')

        log_path = None
        if not self.debug:
            log_path = os.path.devnull
        self.driver = webdriver.Chrome(options=options, service_log_path=log_path)

    def _is_authenticated(self):
        self._get('/', mobile=True)

        try:
            self._wait(lambda x: self.driver.current_url == self.BASE_MOBILE_URL + '/home')
            self.is_authenticated = True
        except:
            self.is_authenticated = False

        return self.is_authenticated

    def auth(self, username, password):
        self._get('/login', mobile=True)
        self._wait((By.NAME, 'session[username_or_email]'))

        self.driver.find_element_by_name('session[username_or_email]').send_keys(username)
        self.driver.find_element_by_name('session[password]').send_keys(password)
        self._click('[data-testid=LoginForm_Login_Button]')

        if not self._is_authenticated():
            raise Exception('ログイン失敗')

    def load_cookies(self, filepath):
        self._get('/', mobile=True)

        with open(filepath, 'r') as f:
            j = json.load(f)
        for cookie in j['cookies']:
            # Seleniumの実装の都合上expiryの形式が異なる
            if 'expiry' in cookie.keys():
                cookie['expiry'] = int(cookie['expiry'])
            self.driver.add_cookie(cookie)

        if not self._is_authenticated():
            raise Exception('ログイン失敗')

    def write_cookies(self, filepath):
        cookies = self.driver.get_cookies()
        with open(filepath, 'w') as f:
            json.dump({'cookies': cookies}, f)

    def _get(self, path, mobile=False):
        if mobile:
            url = self.BASE_MOBILE_URL + path
        else:
            url = self.BASE_URL + path
        return self.driver.get(url)

    def _wait(self, condition):
        if type(condition) is tuple:
            condition = EC.visibility_of_element_located(condition)
        WebDriverWait(self.driver, self.timeout).until(condition)

    def _query_selector(self, q, action):
        self._wait((By.CSS_SELECTOR, q))
        self.driver.execute_script(f"document.querySelector('{q}'){action}")

    def _click(self, query):
        self._query_selector(q=query, action='.click()')

    def _submit(self, query):
        self._query_selector(q=query, action='.submit()')

    def _input(self, query, value):
        self._query_selector(q=query, action=f'.value = {value}')

    def get_session(self):
        session = requests.session()
        for cookie in self.driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])
        return session

    def tweet(self, text, in_reply_to_status_id=None):
        tweet_text = parse.quote(text)
        url = f'/intent/tweet?text={tweet_text}'
        if in_reply_to_status_id is not None:
            url += f'&in_reply_to_status_id={str(in_reply_to_status_id)}'
        self._get(url)
        self._submit('#update-form')
        # ツイートされたIDを返す
        return int(re.findall(r'[0-9]+$', self.driver.current_url)[0])

    def del_tweet(self, tweet_id):
        self._get(f'/-/status/{str(tweet_id)}')
        self._click('.js-actionDelete button')
        self._click('.delete-action')

    def _get_user_intent(self, user_id=None, screen_name=None):
        url = '/intent/user?'
        if user_id:
            url += f'user_id={str(user_id)}'
        elif screen_name:
            url += f'screen_name={screen_name}'
        else:
            return
        self._get(url)

    def follow(self, user_id=None, screen_name=None):
        self._get_user_intent(user_id, screen_name)
        self._submit('form.follow')

    def unfollow(self, user_id=None, screen_name=None):
        self._get_user_intent(user_id, screen_name)
        self._submit('form.unfollow')

    def favorite(self, tweet_id):
        self._get(f'/intent/favorite?tweet_id={str(tweet_id)}')
        self._submit('#favorite_btn_form')

    def retweet(self, tweet_id):
        self._get(f'/intent/retweet?tweet_id={str(tweet_id)}')
        self._submit('#retweet_btn_form')

    def search(self, word, count=200):
        if self.search_manager is None:
            self._get(f'/search?q={word}', mobile=True)
            self.search_manager = SearchManager(self.get_session())
        tweets = self.search_manager.search(word, count)
        return tweets

    def __del__(self):
        self.driver.close()
