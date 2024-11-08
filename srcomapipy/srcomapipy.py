import requests
from typing import Literal, Optional
from .srctypes import *
from datetime import date

API_URL = "https://www.speedrun.com/api/v1/"


# BUGS:
# skip-empty for records endpoint sometimes skips non-empty boards
# TODO:
# [x] resolve ties for leaderboards
# [] bulk access
# [x] make variables accessible from runs


class SRC:
    TIME_FORMAT = "%H:%M:%S"
    DATE_FORMAT = "%d-%m-%y"
    DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"

    def __init__(self, api_key: str = "", user_agent: str = "Green-Bat/srcompy"):
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

    def get(self, uri: str, params: dict = None) -> dict | list:
        uri = API_URL + uri
        if params:
            params["max"] = 200
        r = requests.get(uri, headers=self.headers, params=params)
        if r.status_code >= 400:
            raise SRCAPIException(r.status_code, uri[len(API_URL) :], r.json())
        data: dict | list = r.json()["data"]
        if not data:
            raise SRCException("No data recieved, double check your request")
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

    def get_current_profile(self) -> User:
        return User(self.get("profile"))

    def get_variable(self, var_id: str):
        return Variable(self.get(f"variables/{var_id}"))

    def generic_get(
        self, endpoint: str, id: str = "", orderby: Literal["name", "released"] = "name"
    ) -> SRCType | list[SRCType]:
        """Used to get any resource that inherits from SRCType this includes:
        Developer, Publisher, Genre, GameType, Engine, Platform, Region
        """
        srcobj = TYPES[endpoint]
        if id:
            return srcobj(self.get(endpoint + f"/{id}"))
        return [srcobj(srct) for srct in self.get(endpoint, {"orderby": orderby})]

    def get_notifications(
        self, direction: Literal["asc", "desc"] = "desc"
    ) -> list[Notification]:
        uri = "notifications"
        payload = {"orderby": "created", "direction": direction}
        return [Notification(n) for n in self.get(uri, payload)]

    def unpack_embeds(
        self, data: dict, embeds: str, ignore: list[str] = None
    ) -> dict[dict]:
        """Extracts embedded resources from data"""
        unrolled = {}
        embeds = embeds.split(",")
        for embed in embeds:
            embed = embed.split(".")
            if ignore and embed[0] in ignore:
                continue
            unrolled[embed[0]] = data.pop(embed[0])
        return unrolled

    def search_game(self, name: str) -> list[Game]:
        uri = "games"
        payload = {"name": name}
        games = []
        r = self.get(uri, payload)
        for game in r:
            games.append(self.get_game(game["id"]))
        return games

    def get_game(self, game_id: str, embeds: list[str] = None) -> Game:
        if embeds is None:
            embeds = []
        # embed categories and their variables and levels by default
        embeds = list(set(embeds + ["categories.variables", "levels.variables"]))
        embedding = ",".join(embeds)
        uri = f"games/{game_id}"
        payload = {"embed": embedding}
        data = self.get(uri, payload)
        unpacked_embeds = self.unpack_embeds(
            data, embedding, ignore=["categories", "levels"]
        )
        game = Game(data)
        game.derived_games = self.get_derived_games(game)
        # unpacked_embeds.pop("categories")
        # unpacked_embeds.pop("levels")
        for embed in unpacked_embeds:
            game.embeds.append({embed: unpacked_embeds[embed]["data"]})
        return game

    def get_derived_games(self, game: Game) -> list[Game] | None:
        derived_uri = f"games/{game.id}/derived-games"
        try:
            data = self.get(derived_uri)
        except SRCException:
            data = []
        derived_games = [Game(d) for d in data]
        return derived_games if len(derived_games) > 0 else None

    def get_series(
        self,
        series_id: str = "",
        name: str = "",
        abbreviation: str = "",
        mod: Moderator = None,
        orderby: Literal["", "name.int", "name.jap", "abbreviation", "created"] = "",
        direction: Literal["asc", "desc"] = "desc",
    ) -> Series | list[Series]:
        uri = "series"
        if series_id:
            uri += f"/{series_id}"
            return Series(self.get(uri))
        payload = {
            "name": name,
            "abbreviation": abbreviation,
            "moderator": mod.id,
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
        **queries,
    ) -> Leaderboard:
        uri = f"leaderboards/{game.id}"
        if level:
            uri += f"/level/{level.id}/{category.id}"
        else:
            uri += f"/category/{category.id}"
        payload = {"top": top, "video-only": video_only, "embed": "players"}
        payload.update({k: v for k, v in queries.items() if v and k not in payload})
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
        game: Game,
        run_id: str = "",
        orderby: str = "game",
        dir: Literal["asc", "desc"] = "desc",
        status: Literal["new", "verified", "rejected"] = "verified",
        **queries,
    ) -> Run | list[Run]:
        uri = "runs"
        payload = {"embed": "players,category.variables,level.variables"}
        if run_id:
            uri += f"/{run_id}"
            return Run(self.get(uri, payload))
        payload.update(
            {
                "game": game.id,
                "orderby": orderby,
                "direction": dir,
                "status": status,
            }
        )
        payload.update({k: v for k, v in queries.items() if v and k not in payload})
        data = self.get(uri, payload)
        runs = [Run(r) for r in data]
        return sorted(runs, key=lambda r: r._primary_time)

    def change_run_status(
        self, run: Run, status: Literal["verified", "rejected"], reason: str = ""
    ) -> Run:
        if run.status == status:
            raise SRCException(f"Given run is already {run.status}")
        uri = f"runs/{run.id}/status"
        payload = {"status": {"status": status}}
        if status == "rejected":
            payload["status"].update({"reason": reason})
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
