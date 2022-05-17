"""Kodi RPC"""
import json
import requests

# noinspection PyPep8Naming
from logger import logger

class KodiRPC:
    """Kodi RPC interface"""
    def __init__(self, server_url="http://localhost:8080"):
        self.server = server_url + "/jsonrpc"

    def rpc(self, method: str = "JSONRPC.Introspect", params: dict = None, request_id=1):
        """call kodi rpc"""
        logger.debug("RPC %s %s", method, params)
        if params is None:
            params = {}
        data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        resp = requests.post(self.server, json=data)
        if resp.status_code // 100 != 2:
            raise Exception(
                f"Request failed with response code {resp.status_code}, response {resp.text}")
        resp = resp.json()
        assert resp['id'] == request_id
        if 'error' in resp:
            raise Exception(str(resp['error']))
        return resp['result']

    def get_docs(self):
        """get rpc documentation"""
        return self.rpc()

    def get_episodes(self):
        """get episode list"""
        params = {
            "properties": ["playcount", "file"]
        }
        return self.rpc("VideoLibrary.GetEpisodes", params)["episodes"]

    def mark_episode_watched(self, episode):
        """mark episode watched"""
        if episode["playcount"] == 0:
            params = {
                "episodeid": episode["episodeid"],
                "playcount": 1
            }
            return self.rpc("VideoLibrary.SetEpisodeDetails", params)

    def mark_episode_unwatched(self, episode):
        """mark episode unwatched"""
        params = {
            "episodeid": episode["episodeid"],
            "playcount": 0
        }
        return self.rpc("VideoLibrary.SetEpisodeDetails", params)

    def get_movies(self):
        """get movie list"""
        params = {
            "properties": ["playcount", "file"]
        }
        return self.rpc("VideoLibrary.GetMovies", params)["movies"]

    def mark_movie_watched(self, movie):
        """mark movie watched"""
        if movie["playcount"] == 0:
            params = {
                "movieid": movie["movieid"],
                "playcount": 1
            }
            return self.rpc("VideoLibrary.SetMovieDetails", params)

    def mark_movie_unwatched(self, movie):
        """mark movie unwatched"""
        params = {
            "movieid": movie["movieid"],
            "playcount": 0
        }
        return self.rpc("VideoLibrary.SetMovieDetails", params)

    def remove_empty_shows(self):
        """remove shows from kodi library that have no episodes"""
        shows = self.rpc(method="VideoLibrary.GetTvShows")["tvshows"]
        for show in shows:
            show["episode"] = self.rpc(method="VideoLibrary.GetTVShowDetails",
                                       params={"tvshowid": show["tvshowid"],
                                               "properties": ["episode"]}
                                       )["tvshowdetails"]["episode"]
        for show in shows:
            if show["episode"] == 0:
                logger.info("Removing show %s", show)
                self.rpc(method="VideoLibrary.RemoveTVShow", params={"tvshowid": show["tvshowid"]})


def main():
    """main function for testing"""
    print(json.dumps(KodiRPC().get_episodes(), indent=4))

if __name__ == "__main__":
    main()
