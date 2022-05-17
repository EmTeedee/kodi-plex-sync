"""Classes to handle plex and kodi media interchangaebly"""
from abc import ABC, abstractmethod

class MediaType:
    """common media type definition"""
    movie = "movie"
    show = "show"
    episode = "episode"


class Media(ABC):
    """common media type"""
    def __init__(self, path, raw):
        self.raw = raw
        self.watched = self.get_watched_from_raw()
        self.path = path

    @abstractmethod
    def update_watched(self, watched: bool):
        """update watched status"""

    @abstractmethod
    def get_watched_from_raw(self):
        """get watched status"""

    def __eq__(self, other):
        return self.path == other.path

    def __repr__(self):
        return f"{self.path} raw: {self.raw!r}"

    def __str__(self):
        return self.__repr__()
