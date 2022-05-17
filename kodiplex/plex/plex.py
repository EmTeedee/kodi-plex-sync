"""Plex Media Server interface"""
from plexapi.server import PlexServer
from kodiplex.media import Media, MediaType
from logger import logger

__all__ = [
    'get_media'
]

class PlexMedia(Media):
    """Plex implementation of Media class"""
    def get_watched_from_raw(self):
        return self.raw.isWatched

    def update_watched(self, watched: bool):
        logger.debug("Setting %s watched to %s", self.raw, watched)
        if watched:
            self.raw.markWatched()
        else:
            self.raw.markUnwatched()

def get_media(plex_url: str, plex_token=None):
    """get list with all plex media files"""
    plex = PlexServer(plex_url, token=plex_token)
    medias = []
    for thing in plex.library.all():
        if thing.TYPE == MediaType.movie:
            files = get_media_files(thing)
            for file in files:
                medias.append(PlexMedia(file, thing))
        if thing.type == MediaType.show:
            for episode in thing.episodes():
                files = get_media_files(episode)
                for file in files:
                    medias.append(PlexMedia(file, episode))
    return medias


def get_media_files(thing):
    """de-construct plex media into individual files"""
    files = []
    for media in thing.media:
        for part in media.parts:
            files.append(part.file)
    return files


def main():
    """main function to test adapter"""
    medias = get_media("http://192.168.0.100:32400")
    for media in medias:
        print(media)

if __name__ == "__main__":
    main()
    