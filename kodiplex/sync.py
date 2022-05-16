from collections.abc import Iterable

from plexapi.server import PlexServer

from kodiplex.kodi.kodi_rpc import KodiRPC
from kodiplex.media import Media, KodiMedia, PlexMedia
from kodiplex.plex.plex import Types
from logger import logger
import yaml

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

    def __init__(self, a, b, mode: int, strict=False, normalize={}):
        self.a = a
        self.b = b
        if not 0 <= mode <= 2:
            raise ValueError("mode must be 0,1 or 2")
        self.mode = mode
        self.strict = strict
        self.normalize = normalize

    def verify(self):
        if not self.strict:
            return
        differences = 0
        for mediaA in self.a:
            mediaApath = self.normalizeNames(mediaA.path)
            for mediaB in self.b:
                if mediaApath == self.normalizeNames(mediaB.path):
                    break
            else:  # Loop fell through without finding mediaA in b.
                differences += 1
                logger.error('Not found: A - %s (normalized: %s)' % (mediaA.path, mediaApath))
        if self.mode > 0:
            for mediaB in self.b:
                mediaBpath = self.normalizeNames(mediaB.path)
                for mediaA in self.a:
                    if mediaBpath == self.normalizeNames(mediaA.path):
                        break
                else:
                    differences += 1
                    logger.error('Not found: B - %s (normalized: %s)' % (mediaB.path, mediaBpath))
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
        self.verify()
        for mediaA in self.a:
            mediaApath = self.normalizeNames(mediaA.path)
            for mediaB in self.b:
                if mediaApath == self.normalizeNames(mediaB.path) and mediaA.watched != mediaB.watched:
                    mediaB.updateWatched(mediaA.watched)

    def bidirectionalSync(self):
        self.verify()
        for mediaA in self.a:
            mediaApath = self.normalizeNames(mediaA.path)
            for mediaB in self.b:
                if mediaApath == self.normalizeNames(mediaB.path) and mediaA.watched != mediaB.watched:
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

    kodiMedia = getKodiMedia(cfg["kodi"]["url"])
    plexMedia = getPlexMedia(cfg["plex"]["url"], cfg["plex"]["token"])
    if (cfg["sync"]["first"] == "kodi"):
        sync = MediaSyncer(kodiMedia, plexMedia, cfg["sync"]["mode"], strict = cfg["sync"]["strict"], normalize = cfg["normalize"])
    else:
        sync = MediaSyncer(plexMedia, kodiMedia, cfg["sync"]["mode"], strict = cfg["sync"]["strict"], normalize = cfg["normalize"])
    sync.sync()
