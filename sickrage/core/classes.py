# Author: echel0n <sickrage.tv@gmail.com>
# URL: https://sickrage.tv/
# Git: https://github.com/SiCKRAGETV/SickRage.git
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import random
import re
import sys
import urllib

from datetime import datetime, date
from dateutil import parser

import sickrage
from core.common import Quality, dateFormat, dateTimeFormat
from core.helpers.sessions import USER_AGENTS


class SiCKRAGEURLopener(urllib.FancyURLopener):
    version = random.choice(USER_AGENTS)


class AuthURLOpener(SiCKRAGEURLopener):
    """
    URLOpener class that supports http auth without needing interactive password entry.
    If the provided username/password don't work it simply fails.

    user: username to use for HTTP auth
    pw: password to use for HTTP auth
    """

    def __init__(self, user, pw):
        self.username = user
        self.password = pw

        # remember if we've tried the username/password before
        self.numTries = 0

        # call the base class
        urllib.FancyURLopener.__init__(self)

    def prompt_user_passwd(self, host, realm):
        """
        Override this function and instead of prompting just give the
        username/password that were provided when the class was instantiated.
        """

        # if this is the first try then provide a username/password
        if self.numTries == 0:
            self.numTries = 1
            return self.username, self.password

        # if we've tried before then return blank which cancels the request
        else:
            return '', ''

    # this is pretty much just a hack for convenience
    def openit(self, url):
        self.numTries = 0
        return SiCKRAGEURLopener.open(self, url)


class SearchResult(object):
    """
    Represents a search result from an indexer.
    """

    def __init__(self, episodes):
        self.provider = None

        # release show object
        self.show = None

        # URL to the NZB/torrent file
        self.url = ""

        # used by some providers to store extra info associated with the result
        self.extraInfo = []

        # list of TVEpisode objects that this result is associated with
        self.episodes = episodes

        # quality of the release
        self.quality = Quality.UNKNOWN

        # release name
        self.name = ""

        # size of the release (-1 = n/a)
        self.size = -1

        # release group
        self.release_group = ""

        # version
        self.version = -1

        # hash
        self.hash = None

        # content
        self.content = None

        # ratio
        self.ratio = None

        # result type
        self.resultType = ''

    def __str__(self):

        if self.provider is None:
            return "Invalid provider, unable to print self"

        myString = self.provider.name + " @ " + self.url + "\n"
        myString += "Extra Info:\n"
        for extra in self.extraInfo:
            myString += "  " + extra + "\n"

        myString += "Episodes:\n"
        for ep in self.episodes:
            myString += "  " + str(ep) + "\n"

        myString += "Quality: " + Quality.qualityStrings[self.quality] + "\n"
        myString += "Name: " + self.name + "\n"
        myString += "Size: " + str(self.size) + "\n"
        myString += "Release Group: " + str(self.release_group) + "\n"

        return myString

    def fileName(self):
        return self.episodes[0].prettyName() + "." + self.resultType


class NZBSearchResult(SearchResult):
    """
    Regular NZB result with an URL to the NZB
    """

    def __init__(self, episodes):
        super(NZBSearchResult, self).__init__(episodes)
        self.resultType = "nzb"
        self.provider = self


class NZBDataSearchResult(SearchResult):
    """
    NZB result where the actual NZB XML data is stored in the extraInfo
    """

    def __init__(self, episodes):
        super(NZBDataSearchResult, self).__init__(episodes)
        self.resultType = "nzbdata"


class TorrentSearchResult(SearchResult):
    """
    Torrent result with an URL to the torrent
    """

    def __init__(self, episodes):
        super(TorrentSearchResult, self).__init__(episodes)
        self.resultType = "torrent"


class AllShowsListUI(object):
    """
    This class is for indexer api. Instead of prompting with a UI to pick the
    desired result out of a list of shows it tries to be smart about it
    based on what shows are in SB.
    """

    def __init__(self, config, log=None):
        self.config = config
        self.log = log

    def selectSeries(self, allSeries):
        searchResults = []
        seriesnames = []

        # get all available shows
        try:
            if 'searchterm' in self.config:
                searchterm = self.config[b'searchterm']
                # try to pick a show that's in my show list
                for curShow in allSeries:
                    if curShow in searchResults:
                        continue

                    if 'seriesname' in curShow:
                        seriesnames.append(curShow[b'seriesname'])
                    if 'aliasnames' in curShow:
                        seriesnames.extend(curShow[b'aliasnames'].split('|'))

                    for name in seriesnames:
                        if searchterm.lower() in name.lower():
                            if 'firstaired' not in curShow:
                                curShow[b'firstaired'] = date.fromordinal(1).strftime("%Y-%m-%d")
                                curShow[b'firstaired'] = re.sub("([-]0{2})+", "", curShow[b'firstaired'])
                                fixDate = parser.parse(curShow[b'firstaired'], fuzzy=True).date()
                                curShow[b'firstaired'] = fixDate.strftime(dateFormat)

                            if curShow not in searchResults:
                                searchResults += [curShow]
        except:
            pass

        return searchResults


class ShowListUI(object):
    """
    This class is for tvdb-api. Instead of prompting with a UI to pick the
    desired result out of a list of shows it tries to be smart about it
    based on what shows are in SiCKRAGE.
    """

    def __init__(self, config, log=None):
        self.config = config
        self.log = log

    def selectSeries(self, allSeries):
        try:
            # try to pick a show that's in my show list
            showIDList = [int(x.indexerid) for x in sickrage.srCore.SHOWLIST]
            for curShow in allSeries:
                if int(curShow[b'id']) in showIDList:
                    return curShow
        except Exception:
            pass

        # if nothing matches then return first result
        return allSeries[0]


class Proper(object):
    def __init__(self, name, url, date, show):
        self.name = name
        self.url = url
        self.date = date
        self.provider = None
        self.quality = Quality.UNKNOWN
        self.release_group = None
        self.version = -1

        self.show = show
        self.indexer = None
        self.indexerid = -1
        self.season = -1
        self.episode = -1
        self.scene_season = -1
        self.scene_episode = -1

    def __str__(self):
        return str(self.date) + " " + self.name + " " + str(self.season) + "x" + str(self.episode) + " of " + str(
                self.indexerid) + " from " + str(sickrage.srCore.INDEXER_API(self.indexer).name)


class UIError(object):
    """
    Represents an error to be displayed in the web UI.
    """

    def __init__(self, message):
        self.time = datetime.now().strftime(dateTimeFormat)
        self.title = sys.exc_info()[-2] or message
        self.message = message


class UIWarning(object):
    """
    Represents an error to be displayed in the web UI.
    """

    def __init__(self, message):
        self.time = datetime.now().strftime(dateTimeFormat)
        self.title = sys.exc_info()[-2] or message
        self.message = message


class ErrorViewer(object):
    """
    Keeps a static list of UIErrors to be displayed on the UI and allows
    the list to be cleared.
    """

    errors = []

    def add(self, error, ui=False):
        self.errors += [(error, UIError(error))[ui]]

    @classmethod
    def clear(cls):
        cls.errors = []

    def get(self):
        return self.errors


class WarningViewer(object):
    """
    Keeps a static list of (warning) UIErrors to be displayed on the UI and allows
    the list to be cleared.
    """

    errors = []

    def add(self, error, ui=False):
        self.errors += [(error, UIWarning(error))[ui]]

    @classmethod
    def clear(cls):
        cls.errors = []

    def get(self):
        return self.errors

class AttrDict(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)