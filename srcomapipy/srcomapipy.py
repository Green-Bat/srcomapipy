import requests
from typing import Literal, Optional
from datetime import date
from .srctypes import *

API_URL = "https://www.speedrun.com/api/v1/"


# BUGS:
# skip-empty for records endpoint sometimes skips non-empty boards
# TODO:
# [x] expand get_runs
# [] save and load from file
# [] cache


class SRC:
    TIME_FORMAT = "%H:%M:%S"
    DATE_FORMAT = "%d-%m-%y"
    DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"

    def __init__(self, api_key: str = "", user_agent: str = "Green-Bat/srcomapipy"):
        self.api_key = api_key
        self.user_agent = user_agent
        self.headers = {"User-Agent": user_agent}
        if api_key:
            self.headers["X-API-Key"] = api_key

    def post(self, uri, json: dict) -> dict:
        uri = API_URL + uri
        r = requests.post(uri, headers=self.headers, json=json)
        if r.status_code >= 400:
            raise SRCRunException(r.status_code, uri[len(API_URL) :], r.json())
        return r.json()["data"]

    def put(self, uri: str, json: dict) -> dict:
        uri = API_URL + uri
        r = requests.put(uri, headers=self.headers, json=json)
        if r.status_code >= 400:
            raise SRCAPIException(r.status_code, uri[len(API_URL) :], r.json())
        return r.json()["data"]

    def get(
        self, uri: str, params: dict = None, bulk: bool = False
    ) -> Optional[dict | list]:
        uri = API_URL + uri
        if params:
            params["max"] = 200 if not bulk else 1000
        r = requests.get(uri, headers=self.headers, params=params)
        if r.status_code >= 400:
            raise SRCAPIException(r.status_code, uri[len(API_URL) :], r.json())
        data: dict | list = r.json()["data"]
        if "pagination" in r.json():
            while next_link := r.json()["pagination"]["links"]:
                if len(next_link) == 1 and next_link[0]["rel"] == "prev":
                    break
                elif len(next_link) == 1:
                    next_link = next_link[0]["uri"]
                else:
                    next_link = next_link[1]["uri"]
                r = requests.get(next_link, headers=self.headers)
                if r.status_code >= 400:
                    raise SRCAPIException(r.status_code, uri[len(API_URL) :], r.json())
                data.extend(r.json()["data"])
        return data

    def get_current_profile(self) -> Optional[User]:
        """Returns the currently authenticated User. Requires API Key"""
        return User(self.get("profile")) if self.api_key else None

    def get_notifications(
        self, direction: Literal["asc", "desc"] = "desc"
    ) -> Optional[list[Notification]]:
        """Gets the notifications for the current authenticated user. Requires API Key
        Args:
            direction: sorts ascendingly (oldest first) or descendingly (newest first)
        """
        if not self.api_key:
            return None
        uri = "notifications"
        payload = {"orderby": "created", "direction": direction}
        return [Notification(n) for n in self.get(uri, payload)]

    def get_variable(self, var_id: str):
        return Variable(self.get(f"variables/{var_id}"))

    def get_guest(self, name: str) -> Guest:
        return Guest(self.get(f"guests/{name}"))    

    def generic_get(
        self, endpoint: str, id: str = "", orderby: Literal["name", "released"] = "name"
    ) -> SRCType | list[SRCType]:
        """Used to get any of the following resources:
        developers, publishers, genres, gametypes, engines, platforms, regions
        Args:
            endpoint: name of the endpoint
            id: ID of the desired resource
            orderby: "name", sorts by name alphanumerically.
                "released", sorts by release date, only available for the "platforms" endpoint
        """
        srcobj = TYPES[endpoint]
        if id:
            return srcobj(self.get(endpoint + f"/{id}"))
        return [srcobj(srct) for srct in self.get(endpoint, {"orderby": orderby})]

    def _unpack_embeds(
        self, data: dict, embeds: str, ignore: list[str] = None
    ) -> dict[dict]:
        """Extracts embedded resources from data"""
        unpacked = {}
        embeds = embeds.split(",")
        for embed in embeds:
            embed = embed.split(".")
            if ignore and embed[0] in ignore:
                continue
            unpacked[embed[0]] = data.pop(embed[0])
        return unpacked

    def search_game(
        self,
        name: str,
        abv: str = "",
        release_year: str = "",
        mod_id: str = "",
        gametype_id: str = "",
        platform_id: str = "",
        region_id: str = "",
        genre_id: str = "",
        engine_id: str = "",
        dev_id: str = "",
        publisher_id: str = "",
        orderby: Literal[
            "name.int", "name.jap", "abbreviation", "released", "created", "similarity"
        ] = "",
        direction: Literal["asc", "desc"] = "desc",
        embeds: list[str] = None,
        bulk: bool = False,
    ) -> list[Game]:
        """Searches for a game based on the arguments, categories and levels
        are awlays embedded along with their variables except when using bulk mode
        Args:
            name: name of game to search for
            abv: abbreviation of the game
            orderby: determines sorting method, similarity is default if name is given
                otherwise name.int is default
            direction: also determines sorting, ascending or descending
            embeds: list of resources to embed e.g. ["platforms","moderators"]
            bulk: flag for bulk mode
        """
        uri = "games"
        if name and not orderby:
            orderby = "similarity"
        if not embeds:
            embeds = []
        embeds = ",".join(set(embeds + ["categories.variables", "levels.variables"]))
        payload = {
            "name": name,
            "abbreviation": abv,
            "released": release_year,
            "moderator": mod_id,
            "gametype": gametype_id,
            "platform": platform_id,
            "region": region_id,
            "genre": genre_id,
            "engine": engine_id,
            "developer": dev_id,
            "publisher": publisher_id,
            "orderby": orderby,
            "direction": direction,
            "embed": embeds,
            "_bulk": bulk,
        }
        payload = {k: v for k, v in payload.items() if v}
        return [Game(game, bulk) for game in self.get(uri, payload, bulk)]

    def get_game(self, game_id: str, embeds: list[str] = None) -> Game:
        """Gets a game based on ID
        Args:
            game_id: ID of the game
            embeds: list of resources to embed,
                categories/levels and their variables are always embedded
        """
        if embeds is None:
            embeds = []
        # embed categories and their variables and levels by default
        embeds = ",".join(set(embeds + ["categories.variables", "levels.variables"]))
        uri = f"games/{game_id}"
        payload = {"embed": embeds}
        data = self.get(uri, payload)
        unpacked_embeds = self._unpack_embeds(
            data, embeds, ignore=["categories", "levels"]
        )
        game = Game(data)
        game.derived_games = self.get_derived_games(game)
        for embed in unpacked_embeds:
            game.embeds.append({embed: unpacked_embeds[embed]["data"]})
        return game

    def get_derived_games(self, game: Game) -> Optional[list[Game]]:
        derived_uri = f"games/{game.id}/derived-games"
        data = self.get(derived_uri)
        derived_games = [Game(d) for d in data]
        return derived_games if len(derived_games) > 0 else None

    def get_series(
        self,
        series_id: str = "",
        name: str = "",
        abbreviation: str = "",
        mod_id: str = "",
        orderby: Literal[
            "name.int", "name.jap", "abbreviation", "created"
        ] = "name.int",
        direction: Literal["asc", "desc"] = "desc",
    ) -> Series | list[Series]:
        uri = "series"
        if series_id:
            uri += f"/{series_id}"
            return Series(self.get(uri, {"embed": "moderators"}))
        payload = {
            "name": name,
            "abbreviation": abbreviation,
            "moderator": mod_id,
            "orderby": orderby,
            "direction": direction,
            "embed": "moderators",
        }
        payload = {k: v for k, v in payload.items() if v}
        return [Series(s) for s in self.get(uri, payload)]

    def get_users(
        self,
        user_id: str = "",
        lookup: str = "",
        name: str = "",
        twitch: str = "",
        hitbox: str = "",
        twitter: str = "",
        speedrunslive: str = "",
        orderby: Literal["name.int", "name.jap", "signup", "role"] = "name.int",
        direction: Literal["asc", "desc"] = "desc",
    ) -> User | list[User]:
        """Gets user or users
        Args:
            user_id: will return a single user based on the ID
            lookup: does a cas-sensitive exact-string match search across the site
                including all URLs and socials.
                If given all remaining arguments are ignored
                except for direction and orderby
            name: case-sensitive search across site users/urls
            twitch,hitbox,twitter,speedrunslive:
                search by the username of the respective social media
            orderby: determines the way the users are sorted,\n
                name.int sorts by international username\n
                name.jap sorts by japanese username\n
                signup sorts by signup date\n
                role sorts by role
            direction: sorts either ascendingly or descendingly
        """
        uri = "users"
        if user_id:
            uri += f"/{user_id}"
            return User(self.get(uri))
        payload = {"orderby": orderby, "direction": direction}
        if lookup:
            payload["lookup"] = lookup
            return [User(u) for u in self.get(uri, payload)]
        payload.update(
            {
                "name": name,
                "twitch": twitch,
                "hitbox": hitbox,
                "twitter": twitter,
                "speedrunslive": speedrunslive,
            }
        )
        return [User(u) for u in self.get(uri, payload)]

    def get_leaderboard(
        self,
        game: Game,
        category: Category,
        level: Level = None,
        top: int = 3,
        video_only: bool = False,
        variables: list[tuple[Variable, str]] = None,
        date: str = date.today().isoformat(),
        emulators: Optional[bool] = None,
        timing: Optional[Literal["realtime", "realtime_noloads", "ingame"]] = None,
        platform_id: str = "",
        region_id: str = "",
        embeds: list[str] = None,
    ) -> Leaderboard:
        uri = f"leaderboards/{game.id}"
        if level:
            uri += f"/level/{level.id}/{category.id}"
        else:
            uri += f"/category/{category.id}"
        if not embeds:
            embeds = []
        embeds = ",".join(set(embeds + ["players"]))
        payload = {
            "top": top,
            "video-only": video_only,
            "date": date,
            "emulators": emulators,
            "timing": timing,
            "platform": platform_id,
            "region": region_id,
            "embed": embeds,
        }
        payload = {k: v for k, v in payload.items() if v}
        if variables:
            for var in variables:
                payload[f"var-{var[0].id}"] = var[1]
        data: dict = self.get(uri, payload)
        # reinsert players embed inside of each run
        i = j = 0
        while i < len(data["runs"]):
            l = len(data["runs"][i]["run"]["players"])
            data["runs"][i]["run"]["players"] = {}
            data["runs"][i]["run"]["players"]["data"] = data["players"]["data"][
                j : j + l
            ]
            j += l
            i += 1
        data.pop("players")
        return Leaderboard(data, game, category, level, variables)

    def get_runs(
        self,
        game_id: str = "",
        run_id: str = "",
        status: Literal["new", "verified", "rejected"] = "verified",
        category_id: str = "",
        level_id: str = "",
        examiner: str = "",
        user_id: str = "",
        guest: str = "",
        platform_id: str = "",
        region_id: str = "",
        emulated: Optional[bool] = None,
        orderby: Literal[
            "game",
            "category",
            "level",
            "platform",
            "region",
            "emulated",
            "date",
            "submitted",
            "status",
            "verify-date",
        ] = "game",
        direction: Literal["asc", "desc"] = "desc",
    ) -> Run | list[Run]:
        uri = "runs"
        payload = {"embed": "players,category.variables,level.variables"}
        if run_id:
            uri += f"/{run_id}"
            return Run(self.get(uri, payload))
        payload.update(
            {
                "status": status,
                "game": game_id,
                "category": category_id,
                "level": level_id,
                "examiner": examiner,
                "user": user_id,
                "guest": guest,
                "platform": platform_id,
                "region": region_id,
                "emulated": emulated,
                "orderby": orderby,
                "direction": direction,
            }
        )
        payload = {k: v for k, v in payload.items() if v}
        data = self.get(uri, payload)
        runs = [Run(r) for r in data]
        return sorted(runs, key=lambda r: r._primary_time)

    def change_run_status(
        self, run: Run, status: Literal["verified", "rejected"], reason: str = ""
    ) -> Run:
        """Changes the status of a run to either "verified" or "rejected"
        Args:
            run: the run to be changed
            status: the new status of the run
            reason: the rejection reason, not required if status="verified"
        """
        if run.status == status:
            raise SRCException(f"Given run is already {run.status}")
        uri = f"runs/{run.id}/status"
        payload = {"status": {"status": status}}
        if status == "rejected":
            payload["status"]["reason"] = reason
        return Run(self.put(uri, json=payload))

    def change_run_players(self, run: Run, players: list[User | Guest]) -> Run:
        uri = f"runs/{run.id}/players"
        payload = {"players": []}
        for p in players:
            if isinstance(p, User):
                payload["players"].append({"rel": "user", "id": p.id})
            elif isinstance(p, Guest):
                payload["players"].append({"rel": "guest", "name": p.name})
        return Run(self.put(uri, json=payload))

    def submit_run(
        self,
        category_id: str,
        level_id: str,
        platform_id: str,
        times: dict[str, float],
        players: list[User | Guest],
        date: str = date.today().isoformat(),
        region_id: str = "",
        verified: bool = False,
        emulated: bool = False,
        video_link: str = "",
        comment: str = "",
        splitsio: str = "",
        variables: list[tuple[Variable, str]] = None,
    ) -> Run:
        uri = "runs"
        _variables = {}
        _players = []
        for p in players:
            if isinstance(p, User):
                _players.append({"rel": "user", "id": p.id})
            elif isinstance(p, Guest):
                _players.append({"rel": "guest", "id": p.name})
        for v, val in variables:
            _type = "user-defined"
            if not v.user_defined:
                _type = "pre-defined"
                val = v.values[val]
            _variables[v.id] = {"type": _type, "value": val}
        payload = {
            "run": {
                "category": category_id,
                "level": level_id,
                "date": date,
                "region": region_id,
                "platform": platform_id,
                "verified": verified,
                "times": {
                    "realtime": times["realtime"],
                    "realtime_noloads": times["realtime_noloads"],
                    "ingame": times["ingame"],
                },
                "players": _players,
                "emulated": emulated,
                "video": video_link,
                "comment": comment,
                "splitsio": splitsio,
                "variables": _variables,
            }
        }
        return Run(self.post(uri, json=payload))

    def delte_run(self, run_id: str) -> Run:
        uri = f"{API_URL}runs/{run_id}"
        r = requests.delete(uri, headers=self.headers)
        if r.status_code >= 400:
            raise SRCAPIException(r.status_code, uri[len(API_URL) :], r.json())
        return Run(r.json()["data"])
