# 	1. Get playlist/video
# 		a. Playlist
# 		b. Video
# 	2. IF PLAYLIST
# 		a. Add all music into spotify (existing or create new)
# 	3. IF VIDEO
# 		a. Find all songs in video first
#       b. Add to spotify (existing or create new)
import json
from typing import List, Dict, Tuple

# for YouTube AP
import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import requests
import youtube_dl

# for spotify
import sys

import spotipy
import spotipy.util as util


class Playlist:
    """
    Attributes

    youtube_client : the client
    """

    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.spotify_user_id = self.get_spotify_user_token()[0]
        self.spotify_token = self.get_spotify_user_token()[1]
        self.playlist_id = self.create_playlist()
        self.song_info = {}

    '''
    def create_or_add(self):
        print("Create a new playlist or add?")
        user_input = input()
        if user_input == "Create": 
            playlist_name = input()
            return playlist_name 
        else: 
    '''

    # Log into YouTube. Return the Youtube client.
    def get_youtube_client(self):
        """Log into YouTube. Return the Youtube client.
        """
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_file.json"

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()

        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)

        return youtube_client

    def get_spotify_user_token(self) -> Tuple[str, str]:
        if len(sys.argv) > 3:
            username = sys.argv[1]
        else:
            sys.exit()

        scope = 'playlist-modify-public'
        token = util.prompt_for_user_token(username, scope)
        return username, token

    def get_yt_playlist(self, yt_playlist_id: str) -> None:
        """ Get a list of all the videos in a YouTube playlist with <yt_playlist_id>
        and create a dictionary of important song info. (self.song_info)
        """

        request = self.youtube_client.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=yt_playlist_id
        )
        response = request.execute()  # a list of everything

        # collect each video and get important information
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtube_url = "https://www.youtube.com/watch?v={}".format(
                item["id"])

            # use youtube_dl to collect the song name & artist name
            video = youtube_dl.YoutubeDL({}).extract_info(
                youtube_url, download=False)
            song_name = video["track"]
            artist = video["artist"]

            if song_name is not None and artist is not None:
                # save all important info and skip any missing song and artist
                self.song_info[video_title] = {
                    "youtube_url": youtube_url,  # may not need
                    "song_name": song_name,
                    "artist": artist,

                    # add the uri, easy to get song to put into playlist
                    "spotify_uri": self.get_spotify_uri(song_name, artist)

                }

    def _get_playlist_id(self, playlist_url: str) -> str:
        """Return the id of a playlist from <playlist_url>."""
        beg_index = playlist_url.find("list=")

        # not found
        if beg_index == -1:
            pass  # not a playlist

        playlist_id = playlist_url[beg_index + 5:]
        return playlist_id

    # get the youtube video
    def get_yt_video(self, yt_video_url: str) -> None:
        """ Get video with <yt_video_url> and create a dictionary of
        important song info. (self.song_info)
        """

        video_title = "Placeholder Title"

        # use youtube_dl to collect the song name & artist name
        video = youtube_dl.YoutubeDL({}).extract_info(
            yt_video_url, download=False)
        song_name = video["track"]
        artist = video["artist"]

        if song_name is not None and artist is not None:
            # save all important info and skip any missing song and artist
            self.song_info[video_title] = {
                "youtube_url": yt_video_url,  # may not need
                "song_name": song_name,
                "artist": artist,

                # add the uri, easy to get song to put into playlist
                "spotify_uri": self.get_spotify_uri(song_name, artist)

            }

    # 3. Log into Spotify & create a new playlist/ get existing playlist
    def create_playlist(self):
        """Create A New Playlist"""
        request_body = json.dumps({
            "name": "Youtube Liked Vids",
            "description": "New Playlist",
            "public": True
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(
            self.spotify_user_id)
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )
        response_json = response.json()

        # playlist id
        playlist_id = response_json["id"]
        return playlist_id

    def get_spotify_uri(self, song_name, artist):
        """Search For the Song"""
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name,
            artist
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]

        # only use the first song
        uri = songs[0]["uri"]

        return uri

    # add songs to playlist
    def add_song_to_playlist(self):
        """Add all songs into a new Spotify playlist"""

        if self.spotify_token:
            sp = spotipy.Spotify(auth=self.spotify_token)
            sp.trace = False
            sp.user_playlist_add_tracks(self.spotify_user_id, self.playlist_id,
                                        self.song_info.values())


if __name__ == '__main__':
    cp = Playlist()
    cp.add_song_to_playlist()
