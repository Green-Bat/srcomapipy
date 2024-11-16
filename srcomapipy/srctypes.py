from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional


class SRCException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class SRCAPIException(Exception):
    def __init__(self, code: int, uri: str, data: dict):
        self.message = f"{code}: {data["message"]} ({uri}) "
        super().__init__(self.message)
        self.status_code: int = data["status"]
        self.errormsg: str = data["message"]
        self.links: list[dict[str, str]] = data["links"]


class SRCRunException(SRCAPIException):
    def __init__(self, code: int, uri: str, data: dict):
        super().__init__(code, uri, data)
        self.errors = "\n".join(data["errors"])


class SRCType:
    def __init__(self, data: dict):
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.links: list[dict[str, str]] = data["links"]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name} ({self.id})>"


class Developer(SRCType):
    def __init__(self, data: dict):
        super().__init__(data)


class Publisher(SRCType):
    def __init__(self, data: dict):
        super().__init__(data)


class Genre(SRCType):
    def __init__(self, data: dict):
        super().__init__(data)


class GameType(SRCType):
    def __init__(self, data: dict):
        super().__init__(data)


class Engine(SRCType):
    def __init__(self, data: dict):
        super().__init__(data)


class Platform(SRCType):
    def __init__(self, data: dict):
        super().__init__(data)
        self.released: str = data["released"]


class Region(SRCType):
    def __init__(self, data: dict):
        super().__init__(data)


TYPES: dict[str, SRCType] = {
    "developers": Developer,
    "publishers": Publisher,
    "genres": Genre,
    "gametypes": GameType,
    "engines": Engine,
    "platforms": Platform,
    "regions": Region,
}


class Series:
    def __init__(self, data: dict):
        self.data = data
        self.id: str = data["id"]
        self.name: str = data["names"]["international"]
        self.abv: str = data["abbreviation"]
        self.weblink: str = data["weblink"]
        self.created = None
        if data["created"]:
            self.created = datetime.fromisoformat(data["created"])
        if data["moderators"]["data"]:
            self.moderators = [Moderator(m) for m in data["moderators"]["data"]]

    def __repr__(self) -> str:
        rep = f"<Series: {self.name}; moderated by "
        mods = ", ".join([m.name for m in self.moderators])
        return rep + f"{mods}>"


class User:
    def __init__(self, data: dict):
        self.data = data
        self.id: str = data["id"]
        self.name: str = data["names"]["international"]
        self.pronouns: str = data["pronouns"]
        if data["location"]:
            self.country: str = data["location"]["country"]["names"]["international"]
        self.weblink: str = data["weblink"]
        self.role: str = data["role"]
        self.signupdate = datetime.fromisoformat(data["signup"])

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name} ({self.id})>"


class Moderator(User):
    def __init__(self, data: dict):
        super().__init__(data)


class Guest:
    def __init__(self, data: dict):
        self.name: str = data["name"]

    def __repr__(self) -> str:
        return f"<Guest: {self.name}>"


class Notification:
    def __init__(self, data: dict):
        self.id: str = data["id"]
        self.creation_date: datetime = datetime.fromisoformat(data["created"])
        self.status: str = data["status"]
        self.text: str = data["text"]
        self.item: str = data["item"]["rel"]
        self.item_link: str = data["item"]["link"]
        self.links: list[dict[str, str]] = data["links"]

    def __repr__(self) -> str:
        return f"<Notification: {self.text} [{self.status}] ({self.id})>"


class Variable:
    def __init__(self, data: dict):
        self.data = data
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.mandatory: bool = data["mandatory"]
        self.values: dict[str, str] = {
            v["label"]: k for k, v in data["values"]["values"].items()
        }
        self.values_by_id: dict[str, str] = {
            k: v["label"] for k, v in data["values"]["values"].items()
        }
        if data["values"]["default"]:
            self.default_val: str = {
                k: v for k, v in self.values.items() if v == data["values"]["default"]
            }
        else:
            self.default_val = None
        self.obsoletes: bool = data["obsoletes"]
        self.user_defined: bool = data["user-defined"]
        self.is_subcategory: bool = data["is-subcategory"]

    def __repr__(self) -> str:
        vals = [f"{k}({v})" for k, v in self.values.items()]
        vals = " - ".join(vals)
        return f"<Variable: '{self.name}' vlaues: [{vals}]>"


class Level:
    def __init__(self, data: dict):
        self.data = data
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.rules: str = data["rules"]
        if "variables" in data:
            variables = [Variable(v) for v in data["variables"]["data"]]
            self.variables: dict[str, Variable] = {v.name: v for v in variables}
            self.variables_by_id: dict[str, Variable] = {v.id: v for v in variables}

    def __repr__(self) -> str:
        return f"<Level: {self.name} ({self.id})>"


class Category:
    def __init__(self, data: dict):
        self.data = data
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.rules: str = data["rules"]
        self.weblink: str = data["weblink"]
        self.players = data["players"]
        if "variables" in data:
            variables = [Variable(v) for v in data["variables"]["data"]]
            self.variables: dict[str, Variable] = {v.name: v for v in variables}
            self.variables_by_id: dict[str, Variable] = {v.id: v for v in variables}
        self.type: str = data["type"]
        self.misc: bool = data["miscellaneous"]

    def __repr__(self) -> str:
        return f"<Category: {self.name} ({self.id})>"


class Game:
    def __init__(self, data: dict, bulk: bool = False):
        self.data = data
        self.id: str = data["id"]
        self.name: str = data["names"]["international"]
        self.abv: str = data["abbreviation"]
        self.weblink: str = data["weblink"]
        if bulk:
            return
        self.boosts_received: int = data["boostReceived"]
        self.distinct_donors: int = data["boostDistinctDonors"]
        self.release_year: str = data["released"]
        self.release_date: datetime = datetime.fromisoformat(data["release-date"])
        if data["created"]:
            self.creation_date: datetime = datetime.fromisoformat(data["created"])
        self.ruleset: dict = data["ruleset"]
        self.platforms: list[str] = data["platforms"]
        self.regions: list[str] = data["regions"]
        self.genres: list[str] = data["genres"]
        self.engines: list[str] = data["engines"]
        self.devs: list[str] = data["developers"]
        self.publishers: list[str] = data["publishers"]
        self.moderators: dict[str, str] = data["moderators"]
        if "categories" in data:
            categories = [Category(c) for c in data["categories"]["data"]]
            self.categories: dict[str, Category] = {c.name: c for c in categories}
            self.categories_by_id: dict[str, Category] = {c.id: c for c in categories}
        if "levels" in data:
            levels = [Level(l) for l in data["levels"]["data"]]
            self.levels: dict[str, Level] = {l.name: l for l in levels}
            self.levels_by_id: dict[str, Level] = {l.id: l for l in levels}
        self.derived_games: list[Game] = None
        self.embeds: list[dict] = None

    def __repr__(self) -> str:
        return f"<Game: {self.name} ({self.id})>"


class Run:
    def __init__(
        self, data: dict, cat: Category = None, lvl: Level = None, player: User = None
    ):
        self.data = data
        self.id: str = data["id"]
        self.game: str = data["game"]
        self.category = data["category"]
        self.level = None
        self.variables: list[tuple[Variable, str]] = []
        if cat:
            self.category = cat
        elif "data" in data["category"] and data["category"]["data"]:
            self.category = Category(data["category"]["data"])
        if isinstance(self.category, Category):
            for k, v in data["values"].items():
                var = self.category.variables_by_id[k]
                val = var.values_by_id[v]
                self.variables.append((var, val))
        if lvl:
            self.level = lvl
        elif data["level"] and isinstance(data["level"], str):
            self.level = data["level"]
        elif data["level"] and data["level"]["data"]:
            self.level = Level(data["level"]["data"])
        self.video_text: str = data["videos"].get("text", "")
        self.videos: list[str] = [
            link["uri"] for link in data["videos"].get("links", [])
        ]
        self.comment: str = data["comment"]
        self.status: str = data["status"]["status"]
        if self.status == "rejected":
            self.reason: str = data["status"]["reason"]
        # --times--
        self._primary_time = timedelta(seconds=data["times"]["primary_t"])
        self.time: str = self.format_td(self._primary_time)
        self.realtime: str = None
        self.ingametime: str = None
        self.loadremovedtime: str = None
        if rta := data["times"]["realtime_t"]:
            self.realtime = self.format_td(timedelta(seconds=rta))
        if igt := data["times"]["ingame_t"]:
            self.ingametime = self.format_td(timedelta(seconds=igt))
        if lrt := data["times"]["realtime_noloads_t"]:
            self.loadremovedtime = self.format_td(timedelta(seconds=lrt))
        self.times = {
            "RTA": rta,
            "IGT": igt,
            "LRT": lrt,
        }
        # --dates--
        if "verify-date" in data["status"]:
            self.verify_date: datetime = datetime.fromisoformat(
                data["status"]["verify-date"]
            )
        self.date: datetime = datetime.fromisoformat(data["date"])
        self.submission_date: datetime = datetime.fromisoformat(data["submitted"])

        self.players: list[User] = None
        if player:
            self.players = [player]
        elif "data" in data["players"]:
            self.players = [
                User(p) if p["rel"] == "user" else Guest(p)
                for p in data["players"]["data"]
            ]

    def format_td(self, td: timedelta) -> str:
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = round(td.microseconds / 1000)
        formated = f"{minutes:02}:{seconds:02}.{milliseconds:03}"
        if hours > 0:
            formated = f"{hours}:" + formated
        return formated

    def primary_time(self) -> str:
        match self.time:
            case self.realtime:
                return "RTA"
            case self.ingametime:
                return "IGT"
            case self.loadremovedtime:
                return "LRT"

    def __repr__(self) -> str:
        rep = f"<Run: "
        time_p = self.primary_time()
        rep += f"{time_p}-{self.times[time_p]} "
        for k, v in self.times.items():
            if v is not None and k != time_p:
                rep += f"{k}-{v} "
        rep += f"({self.id})"
        if isinstance(self.category, Category):
            rep += f"-{self.category.name}-"
        if self.level and isinstance(self.level, Level):
            rep += f"{self.level.name}-"
        for var, val in self.variables:
            rep += f"'{var.name}'={val} "
        if self.players:
            players = [n.name for n in self.players]
        else:
            players = [p["id"] for p in self.data["players"]]
        players = ", ".join(players)
        rep += f"by {players}>"
        return rep


class Leaderboard:
    def __init__(
        self,
        data: dict,
        game: Game,
        category: Category,
        level: Level = None,
        vars: list[tuple[Variable, str]] = None,
    ):
        self.data = data
        self.game = game
        self.category = category
        self.level = level
        self.vars = vars
        self.platform: str = data["platform"]
        self.emulators: Optional[bool] = data.get("emulators", None)
        self.video_only: bool = data["video-only"]
        self.timing: str = data["timing"]
        self.top_runs: defaultdict[int, list[Run]] = defaultdict(list)
        for run in data["runs"]:
            self.top_runs[run["place"]].append(Run(run["run"], category, level))
        self.top_runs: dict[int, list[Run]] = dict(self.top_runs)

    def wr(self) -> Run:
        if len(self.top_runs[1]) == 1:
            return self.top_runs[1][0]
        return self.top_runs[1]

    def __repr__(self) -> str:
        rep = f"<Leaderboard: "
        rep += f"{self.category.name}"
        if self.level:
            rep += f" - {self.level.name}"
        if self.vars:
            rep += " -"
            for v in self.vars:
                rep += f" {v[0].name}={v[1]}"
        return rep + ">"
