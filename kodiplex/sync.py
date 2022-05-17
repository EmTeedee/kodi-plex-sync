
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
    0 -> UNIDIRECTIONAL FROM a to b, a always overrides b. In strict mode media in b but not a is ignored.
    1 -> BIDIRECTIONAL, if a and b conflict, mark both as watched
    2 -> BIDIRECTIONAL, if a and b conflict, mark both as unwatched

    strict sync:
    True -> If media in a and not b, raise error. If media in b and not a, raise error only for BIDIRECTIONAL sync mode.
    False -> Ignore discrepancies in media in a and b.
    Note that if strict, checking is done before doing any updates.
    """

    def __init__(self, medias_a, medias_b, mode: int, strict=False, normalize={}):

        self.normalize = normalize

        # hashify inputs
        self.medias_a = {}
        for media in medias_a:
            self.medias_a[self.normalizeNames(media.path)] = media
        self.medias_b = {}
        for media in medias_b:
            self.medias_b[self.normalizeNames(media.path)] = media

        if not 0 <= mode <= 2:
            raise ValueError("mode must be 0,1 or 2")

        self.mode = mode
        self.strict = strict


    def verify(self):
        differences = 0
        for normalized_a in self.medias_a:
            if normalized_a not in self.medias_b:
                differences += 1
                logger.error('Not found: A - %s (normalized: %s)' % (self.medias_a[normalized_a].path, normalized_a))

        if self.mode > 0:
            for normalized_b in self.medias_b:
                if normalized_b not in self.medias_a:
                    differences += 1
                    logger.error('Not found: B - %s (normalized: %s)' % (self.medias_b[normalized_b].path, normalized_b))

        if differences > 0:
            logger.error("Media mismatch!")
            raise Exception("Media mismatch!")

    def normalizeNames(self, nPath):
        if not self.normalize["enable"]:
            return nPath
        else:
            for mediaA_prefix in self.normalize["map"]:
                nPath = nPath.replace(mediaA_prefix, self.normalize["map"][mediaA_prefix])
            nPath = nPath.replace('\\', '/') # For normalizing between Windows and Linux Paths
            return nPath

    def unidirectionalSync(self):
        for normalizedA in self.medias_a:
            if normalizedA in self.medias_b:
                mediaA = self.medias_a[normalizedA]
                mediaB = self.medias_b[normalizedA]
                if mediaA.watched != mediaB.watched:
                    logger.info("Update watch status: %s" % normalizedA)
                    mediaB.updateWatched(mediaA.watched)

    def bidirectionalSync(self):
        for normalizedA in self.medias_a:
            if normalizedA in self.medias_b:
                mediaA = self.medias_a[normalizedA]
                mediaB = self.medias_b[normalizedA]
                if mediaA.watched != mediaB.watched:
                    logger.info("Update watch status: %s" % normalizedA)
                    if self.mode == 1:
                        if not mediaA.watched:
                            mediaA.updateWatched(True)
                        if not mediaB.watched:
                            mediaB.updateWatched(True)
                    elif self.mode == 2:
                        if mediaA.watched:
                            mediaA.updateWatched(False)
                        if mediaB.watched:
                            mediaB.updateWatched(False)

    def sync(self):
        if self.strict:
            start = time.monotonic()
            sync.verify()
            logger.debug("Verify Strict %.4fs" % time.monotonic() - start)

        if self.mode == 0:
            self.unidirectionalSync()
        else:
            self.bidirectionalSync()
        logger.info("Sync complete")


def getKodiMedia(kodiUrl: str):
    kodi = KodiRPC(kodiUrl)
    kodiMedia = kodi.getMovies() + kodi.getEpisodes()
    kodiMedia = [KodiMedia(x["file"], x, kodi) for x in kodiMedia]
    return kodiMedia


def getPlexMedia(plexUrl: str, plexToken=None):
    plex = PlexServer(plexUrl, token=plexToken)
    plexMedia = []
    for thing in plex.library.all():
        if thing.TYPE == Types.movie:
            files = getFiles(thing)
            for f in files:
                plexMedia.append(PlexMedia(f, thing))
        if thing.type == Types.show:
            for ep in thing.episodes():
                files = getFiles(ep)
                for f in files:
                    plexMedia.append(PlexMedia(f, ep))
    return plexMedia


def getFiles(thing):
    files = []
    for m in thing.media:
        for p in m.parts:
            files.append(p.file)
    return files


if __name__ == "__main__":
    with open("config.yml", "r") as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)

    start = time.monotonic()
    kodiMedia = getKodiMedia(cfg["kodi"]["url"])
    logger.debug('Get Kodi media %d files %.4fs' % (len(kodiMedia), time.monotonic() - start))

    start = time.monotonic()
    plexMedia = getPlexMedia(cfg["plex"]["url"], cfg["plex"]["token"])
    logger.debug("Get Plex media %d files %.4fs" % (len(plexMedia), time.monotonic() - start))

    if cfg["sync"]["first"] == "kodi":
        sync = MediaSyncer(kodiMedia, plexMedia, cfg["sync"]["mode"],
                           strict = cfg["sync"]["strict"],
                           normalize = cfg["normalize"])
    else:
        sync = MediaSyncer(plexMedia, kodiMedia, cfg["sync"]["mode"],
                           strict = cfg["sync"]["strict"],
                           normalize = cfg["normalize"])
    sync.sync()
