"""
Kodi - Plex watched status sync
"""
import time
import yaml

from plexapi.server import PlexServer
from kodiplex.kodi.kodi_rpc import KodiRPC
from kodiplex.media import KodiMedia, PlexMedia
from kodiplex.plex.plex import Types
from logger import logger


class MediaSyncer:
    """
    Sync mode:
    0 -> UNIDIRECTIONAL FROM a to b, a always overrides b.
        In strict mode media in b but not a is ignored.
    1 -> BIDIRECTIONAL, if a and b conflict, mark both as watched
    2 -> BIDIRECTIONAL, if a and b conflict, mark both as unwatched

    strict sync:
    True -> If media in a and not b, raise error. If media in b and not a,
        raise error only for BIDIRECTIONAL sync mode.
    False -> Ignore discrepancies in media in a and b.
    Note that if strict, checking is done before doing any updates.
    """

    def __init__(self, medias_a, medias_b, mode: int, strict=False, normalize=None):

        if normalize is None:
            normalize = {'enabled': False, 'map': {}}

        self.normalize = normalize

        # hashify inputs
        self.medias_a = {}
        for media in medias_a:
            self.medias_a[self.normalize_names(media.path)] = media
        self.medias_b = {}
        for media in medias_b:
            self.medias_b[self.normalize_names(media.path)] = media

        if not 0 <= mode <= 2:
            raise ValueError("mode must be 0,1 or 2")

        self.mode = mode
        self.strict = strict


    def verify(self):
        """Verify that all media on one source is available in the other"""
        differences = 0
        for normalized_a, media_a in self.medias_a.items():
            if normalized_a not in self.medias_b:
                differences += 1
                logger.error('Not found: A - %s (normalized: %s)',
                             media_a.path, normalized_a)

        if self.mode > 0:
            for normalized_b, media_b in self.medias_b.items():
                if normalized_b not in self.medias_a:
                    differences += 1
                    logger.error('Not found: B - %s (normalized: %s)',
                                 media_b.path, normalized_b)

        if differences > 0:
            logger.error("Media mismatch!")
            raise Exception("Media mismatch!")

    def normalize_names(self, path):
        """normalize path names according to supplied rules,
        also change path separators to unix style"""
        if not self.normalize["enable"]:
            return path
        else:
            for media_a_prefix in self.normalize["map"]:
                path = path.replace(media_a_prefix, self.normalize["map"][media_a_prefix])
            path = path.replace('\\', '/') # For normalizing between Windows and Linux Paths
            return path

    def sync_unidirectional(self):
        """sync from a to b"""
        for normalized_a, media_a in self.medias_a.items():
            if normalized_a in self.medias_b:
                media_b = self.medias_b[normalized_a]
                if media_a.watched != media_b.watched:
                    logger.info("Update watch status: %s", normalized_a)
                    media_b.updateWatched(media_a.watched)

    def sync_bidirectional(self):
        """sync a and b, resolve conflicts as specified"""
        for normalized_a, media_a in self.medias_a.items():
            if normalized_a in self.medias_b:
                media_b = self.medias_b[normalized_a]
                if media_a.watched != media_b.watched:
                    logger.info("Update watch status: %s", normalized_a)
                    if self.mode == 1:
                        if not media_a.watched:
                            media_a.updateWatched(True)
                        if not media_b.watched:
                            media_b.updateWatched(True)
                    elif self.mode == 2:
                        if media_a.watched:
                            media_a.updateWatched(False)
                        if media_b.watched:
                            media_b.updateWatched(False)

    def sync(self):
        """main function to sync stuff"""
        if self.strict:
            start = time.monotonic()
            self.verify()
            logger.debug("Verify Strict %.4fs", time.monotonic() - start)

        if self.mode == 0:
            self.sync_unidirectional()
        else:
            self.sync_bidirectional()
        logger.info("Sync complete")


def get_kodi_media(kodi_url: str):
    """get list with all kodi media files"""
    kodi = KodiRPC(kodi_url)
    medias = kodi.getMovies() + kodi.getEpisodes()
    medias = [KodiMedia(media["file"], media, kodi) for media in medias]
    return medias


def get_plex_media(plex_url: str, plex_token=None):
    """get list with all plex media files"""
    plex = PlexServer(plex_url, token=plex_token)
    medias = []
    for thing in plex.library.all():
        if thing.TYPE == Types.movie:
            files = get_media_files(thing)
            for file in files:
                medias.append(PlexMedia(file, thing))
        if thing.type == Types.show:
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
    """run the media sync"""
    with open("config.yml", "r", encoding="utf-8") as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)

    start = time.monotonic()
    kodi_media = get_kodi_media(cfg["kodi"]["url"])
    logger.debug('Get Kodi media %d files %.4fs', len(kodi_media), time.monotonic() - start)

    start = time.monotonic()
    plex_media = get_plex_media(cfg["plex"]["url"], cfg["plex"]["token"])
    logger.debug("Get Plex media %d files %.4fs", len(plex_media), time.monotonic() - start)

    if cfg["sync"]["first"] == "kodi":
        sync = MediaSyncer(kodi_media, plex_media, cfg["sync"]["mode"],
                           strict = cfg["sync"]["strict"],
                           normalize = cfg["normalize"])
    else:
        sync = MediaSyncer(plex_media, kodi_media, cfg["sync"]["mode"],
                           strict = cfg["sync"]["strict"],
                           normalize = cfg["normalize"])
    sync.sync()

if __name__ == "__main__":
    main()
