# twium
Seleniumを使ったpython-twitter風ラッパー

## Usage
```python
import twium
api = twium.AltApi()

# login
api.auth('username', 'password')

# or use cookie
api.write_cookies('path/to/cookie.json')


# methods
api.tweet('hogehoge')
api.del_tweet(123)
api.favorite(123)
api.retweet(123)
api.follow('hogehoge')
api.unfollow('hogehoge')


# get tweets
for tweet in api.search('some query'):
    print(tweet.text)

for tweet in api.timeline():
    print(tweet.text)
```
