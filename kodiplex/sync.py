"""
Kodi - Plex watched status sync
"""
import time

from kodiplex.kodi.kodi import get_media as get_kodi_media
from kodiplex.plex.plex import get_media as get_plex_media
from kodiplex.logger import logger
from kodiplex.config import cfg_get

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
                    media_b.update_watched(media_a.watched)

    def sync_bidirectional(self):
        """sync a and b, resolve conflicts as specified"""
        for normalized_a, media_a in self.medias_a.items():
            if normalized_a in self.medias_b:
                media_b = self.medias_b[normalized_a]
                if media_a.watched != media_b.watched:
                    logger.info("Update watch status: %s", normalized_a)
                    if self.mode == 1:
                        if not media_a.watched:
                            media_a.update_watched(True)
                        if not media_b.watched:
                            media_b.update_watched(True)
                    elif self.mode == 2:
                        if media_a.watched:
                            media_a.update_watched(False)
                        if media_b.watched:
                            media_b.update_watched(False)

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


def main():
    """run the media sync"""

    start = time.monotonic()
    kodi_media = get_kodi_media(cfg_get("kodi", "url", "http://localhost:8080"))
    logger.debug('Get Kodi media %d files %.4fs', len(kodi_media), time.monotonic() - start)

    start = time.monotonic()
    plex_media = get_plex_media(
        cfg_get("plex", "url", "http://192.168.0.100:32400"),
        cfg_get("plex", "token", None))
    logger.debug("Get Plex media %d files %.4fs", len(plex_media), time.monotonic() - start)

    if cfg_get("sync", "first", "kodi") == "kodi":
        sync = MediaSyncer(kodi_media, plex_media, cfg_get("sync", "mode", 1),
                           strict = cfg_get("sync", "strict", False),
                           normalize = cfg_get("normalize"))
    else:
        sync = MediaSyncer(plex_media, kodi_media, cfg_get("sync", "mode", 1),
                           strict = cfg_get("sync", "strict", False),
                           normalize = cfg_get("normalize"))
    sync.sync()

if __name__ == "__main__":
    main()
