# -*- coding: utf-8 -*-
# Copyright 2012 Amaç Herdağdelen
"""
This file is part of Twitter API Python Tools (https://github.com/amacinho/Twitter-API-Python-Tools)
Twitter API Tools is free software:
you can redistribute it and/or modify it under the terms of
the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option)
any later version.

Twitter API Tools is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
Twitter API Tools. If not, see <http://www.gnu.org/licenses/>.
"""

import tweepy
try:
    import json
except:
    import simplejson as json
import time
import sys
import socket

# Default timeout in the socket module is None. Sets timeout to 10 seconds.
# (http://docs.python.org/library/socket.html#socket.getdefaulttimeout)
HTTP_TIMEOUT = 10
socket.setdefaulttimeout(HTTP_TIMEOUT)

class TwitterTools:

    def __init__(self):
        pass
    
    def read_properties_line(self, line):
        key,value = line.strip().split("=")
        return key,value
    
    def read_config_file(self, fn):
        """ Reads a properties-formatted-like file with the same format of what Twitter4J uses:
        oauth.accessToken=************************************
        oauth.accessTokenSecret=************************************
        oauth.consumerKey=************************************
        oauth.consumerSecret=************************************
        """
        try:
            fp = open(fn)
        except:
            raise(Exception("Need to provide a valid auth file which contains access token, access token secret, consumer key and consumer secret."))
        credentials = dict()
        # Applies poor man's properties parser.
        for line in fp:
            key,value = self.read_properties_line(line)
            if key=="oauth.accessToken":
                credentials["access_token"] = value
            elif key=="oauth.accessTokenSecret":
                credentials["access_token_secret"] = value
            elif key=="oauth.consumerKey":
                credentials["consumer_key"] = value
            elif key=="oauth.consumerSecret":
                credentials["consumer_secret"] = value
        assert len(credentials)==4, "Improper auth file."
        return credentials
    
    def get_api(self, auth_file="auth.txt"):    
        credentials = self.read_config_file(auth_file)
        #self.credentials = credentials
        auth = tweepy.OAuthHandler(credentials["consumer_key"], credentials["consumer_secret"])
        auth.set_access_token(credentials["access_token"], credentials["access_token_secret"])
        try:
            # Makes use of a patch to tweepy which provides a default timeout value.
            api = tweepy.API(auth_handler=auth, timeout=HTTP_TIMEOUT)
        except:
            # Makes use of standard tweepy.
            api = tweepy.API(auth_handler=auth)
        self.api = api

    def get_access(self):
        assert self.api
        """Enters into a blocking loop until there is available quota for REST API calls."""
        while True:
            try:
                req = self.api.rate_limit_status()
                remaining = int(req["remaining_hits"])
                sys.stderr.write("remaining: %d\n" % remaining)
                if remaining < 1:
                    sys.stderr.write("Not enough remaining hits. Sleeping 20 minutes before retry.\n\n")
                    time.sleep(1200)                
                    continue
                break
            except:
                sys.stderr.write("Unknown error while trying to get quota. Sleeping 5 seconds before retry.\n\n")
                time.sleep(5)

    def get_all_followers_by_id(self, user_id):
        next_cursor = -1
        follower_ids = set()
        # Iterates over the paginated results
        while next_cursor != 0:        
            while True:
                try:
                    response = self.api.followers_ids(user_id=user_id, cursor=next_cursor)
                    break
                except tweepy.error.TweepError, e:
                    if str(e) == "Not authorized":
                        # Ignores the users with protected accounts.
                        response = None
                        break
                    raise
                
                if response == None:
                    break
            follower_ids.update(response[0])
            sys.stderr.write(".")
            next_cursor = response[1][1]
        return follower_ids

    def get_all_friends_by_id(self, user_id):
        next_cursor = -1
        friends_ids = set()
        # Iterates over the paginated results
        while next_cursor != 0:        
            while True:
                try:
                    response = self.api.friends_ids(user_id=user_id, cursor=next_cursor)
                    break
                except tweepy.error.TweepError, e:
                    if str(e) == "Not authorized":
                        # Ignores the users with protected accounts.
                        response = None
                        break
                    raise
                
                if response == None:
                    break
            friends_ids.update(response[0])
            sys.stderr.write(".")
            next_cursor = response[1][1]
        return friends_ids

    def get_all_statuses_by_id(self, user_id, page=5, rpp=50):
        statuses = set()
        self.get_access()
        for page in xrange(page):
            responses = self.get_robust_statuses_page(user_id, page, count=rpp)
            if responses:
                statuses.update(responses)
                sys.stderr.write('.')
            else:
                break
        return statuses
    
    def get_robust_statuses_page(self, user_id, page, count=50):    
        statuses = set()
        trial = 1
        while True:
            try:
                responses = [jsonize_status(status) for status in self.api.user_timeline(user_id=user_id, count=count, page=page+1)]
                if responses:
                    statuses.update(set(responses))
                else:
                    return statuses
                break
            except Exception, e:
                trial += 1
                if trial > 2:
                    self.get_access()
                    if trial > 5:
                        return statuses,api
                    if str(e) == 'Not authorized':
                        return []
                time.sleep(trial)
                sys.stderr.write("%s\n" % (str(e)))            

        return statuses


def jsonize_user(user):
    """Remove status and _api fields and returns a JSON string for the user variable."""
    d = user.__dict__
    d.pop("_api")
    try:
        d.pop("status")
    except:
        pass
    s = json.dumps(dict([(k,unicode(v)) for k,v in d.items()]))
    return s
    
def jsonize_status(status):
    """Remove status and _api fields and returns a JSON string for the status variable."""
    d = status.__dict__    
    d.pop("_api")        
    d.pop("author")
    d["user"] = d["user"].__dict__
    d["user"].pop("_api")
    s = json.dumps(dict([(k,unicode(v)) for k,v in d.items()]))
    return s

