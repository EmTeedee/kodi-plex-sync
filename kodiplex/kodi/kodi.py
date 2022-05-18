"""Kodi interface"""
from typing import List
from kodiplex.kodi.kodi_rpc import KodiRPC
from kodiplex.media import Media
from kodiplex.logger import logger

__all__ = [
    'KodiMedia',
    'get_media'
]

class KodiMedia(Media):
    """Kodi implementation of Media class"""
    def __init__(self, path, raw, kodi: KodiRPC):
        Media.__init__(self, path, raw)
        self.kodi = kodi

    def get_watched_from_raw(self):
        return self.raw["playcount"] > 0

    def update_watched(self, watched: bool):
        logger.debug("Setting %s watched to %s", self.raw, watched)
        if watched:
            if "movieid" in self.raw:
                return self.kodi.mark_movie_watched(self.raw)
            else:
                return self.kodi.mark_episode_watched(self.raw)
        else:
            if "movieid" in self.raw:
                return self.kodi.mark_movie_unwatched(self.raw)
            else:
                return self.kodi.mark_episode_unwatched(self.raw)

def get_media(kodi_url: str) -> List[KodiMedia]:
    """get list with all kodi media files"""
    kodi = KodiRPC(kodi_url)
    medias = kodi.get_movies() + kodi.get_episodes()
    medias = [KodiMedia(media["file"], media, kodi) for media in medias]
    return medias

def main():
    """main function to test adapter"""
    medias = get_media("http://localhost:8080")
    for media in medias:
        print(media)

if __name__ == "__main__":
    main()
