from typing import List, Tuple, Type, cast

import twitter
from loguru import logger

from iocingestor.artifacts import Artifact
from iocingestor.sources import Source

TWEET_URL = "https://twitter.com/{user}/status/{id}"


class Plugin(Source):
    def __init__(
        self,
        name: str,
        api_key: str,
        api_secret_key: str,
        access_token: str,
        access_token_secret: str,
        defanged_only: bool = True,
        tweet_mode: str = "extended",
        **kwargs,
    ):
        self.name = name
        self.api = twitter.Twitter(
            auth=twitter.OAuth(
                access_token, access_token_secret, api_key, api_secret_key
            )
        )

        # Let the user decide whether to include non-obfuscated URLs or not.
        self.include_nonobfuscated = not defanged_only

        # Forward kwargs.
        # NOTE: No validation is done here, so if the config is wrong, expect bad results.
        self.kwargs = kwargs

        # Set "extended" as the default tweet mode
        if kwargs.get("tweet_mode") is None:
            self.kwargs["tweet_mode"] = tweet_mode

        # Decide which endpoint to use based on passed arguments.
        # If slug and owner_screen_name, use List API.
        # If screen_name or user_id, use User Timeline API.
        # If q is set, use Search API.
        # Otherwise, default to mentions API.
        self.endpoint = self.api.statuses.mentions_timeline

        has_owner_screen_name: bool = kwargs.get("owner_screen_name") is not None
        has_slug_or_list_id: bool = (
            kwargs.get("slug") or kwargs.get("list_id") is not None
        )
        has_screen_name_or_user_id: bool = (
            kwargs.get("screen_name") or kwargs.get("user_id")
        ) is not None
        has_query: bool = kwargs.get("q") is not None

        if has_slug_or_list_id and has_owner_screen_name:
            self.endpoint = self.api.lists.statuses
        elif has_screen_name_or_user_id:
            self.endpoint = self.api.statuses.user_timeline
        elif has_query:
            self.endpoint = self.api.search.tweets

    def run(self, saved_state: str) -> Tuple[str, List[Type[Artifact]]]:
        # Modify kwargs to insert since_id.
        if saved_state:
            self.kwargs["since_id"] = saved_state

        # Pull new tweets.
        try:
            response = self.endpoint(**self.kwargs)
        except twitter.api.TwitterHTTPError as e:
            # API error; log and return early.
            logger.warning(f"Twitter API Error: {e}")

            return saved_state, []

        # Correctly handle responses from different endpoints.
        try:
            tweet_list = response["statuses"]
        except TypeError:
            tweet_list = response

        tweets = [
            {
                "content": s.get("full_text") or s.get("text"),
                "id": s["id_str"],
                "user": s["user"]["screen_name"],
                "entities": s.get("entities", {}),
            }
            for s in tweet_list
        ]

        artifacts: List[Type[Artifact]] = []
        # Traverse in reverse, old to new.
        tweets.reverse()
        for tweet in tweets:
            # Expand t.co links.
            for url in tweet["entities"].get("urls", []):
                try:
                    tweet["content"] = tweet["content"].replace(
                        url["url"], url["expanded_url"]
                    )
                except KeyError:
                    # No url/expanded_url, continue without expanding.
                    pass

            # Process tweet.
            saved_state = cast(str, tweet["id"])
            artifacts += self.process_element(
                tweet["content"],
                TWEET_URL.format(user=tweet["user"], id=tweet["id"]),
                include_nonobfuscated=self.include_nonobfuscated,
            )

        return saved_state, artifacts
