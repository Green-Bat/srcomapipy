import requests
from typing import Literal, Optional
from datetime import date
from .srctypes import *
from itertools import groupby
from urllib.parse import urlparse

API_URL = "https://www.speedrun.com/api/v1/"


# API BUGS:
# skip-empty for records endpoint sometimes skips non-empty boards
# user/personal-bests sometimes gets obsolete runs and non-wr runs
# some variables have no values but still have a default
# potential bug when using orderby category for get runs, not all runs are retrieved
# TODO:
# [] Comprehensive docs
# [] Change list returns to iterators


class SRC:
    TIME_FORMAT = "%H:%M:%S"
    DATE_FORMAT = "%d-%m-%y"
    DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"

    def __init__(self, api_key: str = "", user_agent: str = "Green-Bat/srcomapipy"):
        self.cache: dict[tuple[str, tuple], dict | list] = dict()
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
    ) -> Optional[dict | list[dict]]:
        uri = API_URL + uri
        if params:
            params["max"] = 200 if not bulk else 1000
        else:
            params = {}
        key = (uri, tuple(sorted(params.values(), key=lambda p: str(p))))
        data: dict | list[dict] = self.cache.get(key)
        if data is not None:
            return data
        r = requests.get(uri, headers=self.headers, params=params)
        if r.status_code >= 400:
            raise SRCAPIException(r.status_code, uri[len(API_URL) :], r.json())
        data = r.json()["data"]
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
        self.cache[key] = data
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

    def get_guest(self, name: str) -> Guest:
        """Gets a specific guest by their name"""
        return Guest(self.get(f"guests/{name}"))

    def get_variable(self, var_id: str) -> Variable:
        """Gets a specific variable by its ID"""
        return Variable(self.get(f"variables/{var_id}"))

    def get_category(self, cat_id: str) -> Category:
        """Gets a category by its ID, game and variables are embedded by default"""
        return Category(self.get(f"categories/{cat_id}", {"embed": "game,variables"}))

    def get_level(self, lvl_id: str) -> Level:
        """Gets a level by its ID, categories and their variables
        and the variables of the level are embedded by default"""
        return Level(
            self.get(f"levels/{lvl_id}", {"embed": "categories.variables,variables"})
        )

    def generic_get(
        self,
        endpoint: str,
        id: str = "",
        orderby: Literal["name", "released"] = "name",
        direction: Literal["asc", "desc"] = "asc",
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
            return srcobj(self.get(f"{endpoint}/{id}"))
        payload = {"orderby": orderby, "direction": direction}
        return [srcobj(srct) for srct in self.get(endpoint, payload)]

    def search_game(
        self,
        name: str = "",
        *,
        series: Series = None,
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
            series: will limit search to games from this specific series
            abv: search by abbreviation of the game
            orderby: determines sorting method, similarity is default if 'name' is given
                otherwise name.int is default
            direction: also determines sorting, ascending or descending
            embeds: list of resources to embed e.g. ["platforms","moderators"]
            bulk: flag for bulk mode
        """
        uri = "games"
        if series:
            uri = f"series/{series.id}/{uri}"
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
        """Gets a game based on its ID
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
        game = Game(self.get(uri, {"embed": embeds}))
        game.derived_games = self.get_derived_games(game)
        return game

    def get_derived_games(self, game: Game) -> Optional[list[Game]]:
        """Gets all derived games for a specific game"""
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
        direction: Literal["asc", "desc"] = "asc",
    ) -> Series | list[Series]:
        """Gets a game series by ID or a list of series based on the arguments.
        Moderators are embedded by default
        Args:
            series_id: returns specific series based on id
            name: name of series to search for
            abbreviation: search based on abbreviation of the series
            mod_id: gets series that are moderated by this user
            orderby: determines sorting method
            direction: determines direction of sorting
        """
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
        direction: Literal["asc", "desc"] = "asc",
    ) -> User | list[User]:
        """Gets a user by ID or list of users based on the arguments
        Args:
            user_id: will return a single user based on the ID
            lookup: does a cas-sensitive exact-string match search across the site
                including all URLs and socials.
                If given all remaining arguments are ignored
                except for direction and orderby
            name: case-insensitive search across site users/urls
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

    def get_user_pbs(
        self,
        user: User,
        top: Optional[int] = None,
        series_id: str = "",
        game_id: str = "",
        embeds: list[str] = None,
    ) -> UserBoard:
        """Gets a specific user's personal bests
        Args:
            user: user who's pbs will be returned
            top: gets runs with a place equivalent to or better than this number
            series_id: restricts runs to a specific series
            game_id: restricts runs to a specific game
            embeds: embed options are the same as the ones for runs
        """
        uri = f"users/{user.id}/personal-bests"
        if not embeds:
            embeds = []
        embeds = ",".join(
            set(embeds + ["players", "category.variables", "level.variables"])
        )
        payload = {"top": top, "series": series_id, "game": game_id, "embed": embeds}
        payload = {k: v for k, v in payload.items() if v}
        return UserBoard(self.get(uri, payload), user)

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
        platform_id: str = None,
        region_id: str = None,
        embeds: list[str] = None,
    ) -> Leaderboard:
        """Returns a specific leaderboard of runs. Obsolete runs are not included.
        Args:
            top: number of runs to include
            video_only: determines if included runs must have a video
            variables: a list of tuples of a specific variable associated
                with the leaderboard and the desired value
            date: returns runs done on this date or before
            emulators: determines if only emulators or real devices are shown
                if omitted both are included
            timing: determines which timing method to sort the runs by
            platform_id: gets runs done on a specific platform
            region_id: gets runs done in a specific region
            embeds: list of resources to embed, players are embedded by default
                and reinserted into the runs themselves
        """
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
            "timing": timing,
            "platform": platform_id,
            "region": region_id,
            "embed": embeds,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        if emulators is not None:
            payload["emulators"] = emulators
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
        run_id: str = None,
        game_id: str = None,
        status: Literal["new", "verified", "rejected"] = "verified",
        category_id: str = None,
        level_id: str = None,
        examiner: str = None,
        user_id: str = None,
        guest: str = None,
        platform_id: str = None,
        region_id: str = None,
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
        embeds: list[str] = None,
        time_sort: bool = False,
    ) -> Run | list[Run]:
        """Get a run based on ID or a list of runs based on the arguments.
        Obsolete runs are included.
        Args:
            run_id: ID of the run to get
            game_id: gets runs from a specific game
            status: status of the runs to get
            category_id: category of the runs
            level_id: level of the runs
            examiner: ID of a moderator, returns runs verified by this moderator
            user_id: returns runs done by a specific user
            guest: returns runs done by a specific guest
            platform_id: gets runs performed on a specific platform
            region_id: gets runs from a specific region
            emulated: determiens if emulated runs are included or excluded,
                if omitted both are included
            orderby: determines sorting order
            direction: determines sorting direction
            embeds: list of things to embed, players, categories/levels and
                their variables are embedded by default
            time_sort: sorts by run time in addition to orderby
        """
        uri = "runs"
        if embeds is None:
            embeds = []
        embeds = ",".join(set(embeds + ["players,category.variables,level.variables"]))
        if run_id:
            uri += f"/{run_id}"
            return Run(self.get(uri, {"embed": embeds}))
        payload = {
            "status": status,
            "game": game_id,
            "category": category_id,
            "level": level_id,
            "examiner": examiner,
            "user": user_id,
            "guest": guest,
            "platform": platform_id,
            "region": region_id,
            "orderby": orderby,
            "direction": direction,
            "embed": embeds,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        if emulated is not None:
            payload["emulated"] = emulated
        data = self.get(uri, payload)
        runs = [Run(r) for r in data]

        def key_func(run: Run, orderby: str):
            if orderby in ["game", "platform", "region"]:
                comparator = run.__dict__[orderby].id
            elif orderby in ["level", "category"]:
                comparator = run.category_id
                if run.level:
                    comparator += f"_{run.level_id}"
                for v in run.variables:
                    if v[0].is_subcategory:
                        comparator += f"_{v[1]}"
            elif orderby == "submitted":
                comparator = run.submission_date
            elif orderby == "verify-date":
                comparator = run.verify_date
            else:
                comparator = run.__dict__[orderby]
            return comparator

        sorted_runs = []
        if time_sort:
            for _, g in groupby(runs, key=lambda r: key_func(r, orderby)):
                sorted_runs += sorted(list(g), key=lambda r: r._primary_time)
            return sorted_runs
        return runs

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
        """Changes the players of a run
        Args:
            run: the run to be changed
            players: the new players of the run
        """
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
        platform_id: str,
        times: dict[str, float],
        players: list[User | Guest],
        level_id: Optional[str] = None,
        date: str = date.today().isoformat(),
        region_id: Optional[str] = None,
        verified: bool = False,
        emulated: bool = False,
        video_link: str = None,
        comment: Optional[str] = None,
        splitsio: Optional[str] = None,
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
                val = v.values[val]  # get id of value
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
                    "realtime": times.get("realtime", 0),
                    "realtime_noloads": times.get("realtime_noloads", 0),
                    "ingame": times.get("ingame", 0),
                },
                "players": _players,
                "emulated": emulated,
                "video": video_link,
                "comment": comment,
                "splitsio": splitsio,
                "variables": _variables,
            }
        }
        payload["run"] = {k: v for k, v in payload["run"].items() if v is not None}
        return Run(self.post(uri, json=payload))

    def delte_run(self, run_id: str) -> Run:
        """Deletes a run. Requires API Key. You can only delete your own runs,
        unless you're a global mod. May raise an exception with code 500 on success"""
        uri = f"{API_URL}runs/{run_id}"
        r = requests.delete(uri, headers=self.headers)
        if r.status_code >= 400:
            raise SRCAPIException(r.status_code, uri[len(API_URL) :], r.json())
        return Run(r.json()["data"])

    def get_at_risk_wrs(self, game_id: str) -> list[Run]:
        """Gets all former World Records that only have Twitch links
        and may be at risk of being deleted"""
        runs: list[Run] = self.get_runs(game_id=game_id)

        def key_func(r: Run):
            comparator = r.category_id
            for v in r.variables:
                if v[0].is_subcategory:
                    comparator += f"_{v[1]}"
            return comparator

        former_wrs: list[Run] = []
        runs = sorted(runs, key=key_func)
        for _, g in groupby(runs, key=key_func):
            g: list[Run] = sorted(g, key=lambda r: r.date)
            latest_wr = g[0]
            former_wrs.append(g[0])
            for run in g[1:]:
                if run._primary_time < latest_wr._primary_time:
                    latest_wr = run
                    former_wrs.append(run)

        runs = filter(
            lambda r: r.videos
            and all("twitch.tv" in urlparse(vid).netloc for vid in r.videos),
            former_wrs,
        )
        return list(runs)
