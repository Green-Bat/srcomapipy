from srcomapipy.srcomapipy import SRC
from srcomapipy.srctypes import *


def main():
    from os import getenv
    from dotenv import load_dotenv

    load_dotenv()
    api_key = getenv("SRCAPIKEY")

    api = SRC(api_key=api_key)
    me = api.get_current_profile()
    print(me)
    game = api.search_game("Batman: Arkham City")[0]
    my_pbs = api.get_user_pbs(me, game_id=game.id, embeds=["game"])
    print(my_pbs.runs)
    runs: list[Run] = api.get_runs(game.id, status="new")
    print(runs)
    cat = game.categories["Fastest"]
    lvl = game.levels["Meltdown Mayhem"]
    lbrd = api.get_leaderboard(
        game, cat, lvl, variables=[(cat.variables["Version"], "PC")]
    )
    print(lbrd, lbrd.top_runs)
    # for name, cat in game.categories.items():
    #     print(f"category: {name}")
    #     for _, v in cat.variables.items():
    #         print(f"{v} {v.mandatory=} {v.obsoletes=} {v.is_subcategory=}")
    series = api.get_series(name="Batman")
    print(series)
    print(api.generic_get("platforms", "o7e25xew"))


if __name__ == "__main__":
    main()
