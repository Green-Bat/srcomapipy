from srcomapipy.srcomapipy import SRC
from srcomapipy.srctypes import *


def main():
    from os import getenv
    from dotenv import load_dotenv

    load_dotenv()
    api_key = getenv("SRCAPIKEY")
    api = SRC(api_key=api_key)
    me = api.get_users(lookup="GreenBat")[0]
    print(me)
    # us = api.get_users(lookup="za9c")[0]
    # game = api.search_game("Batman: Arkham City")[0]
    # runs: list[Run] = api.get_runs(game, status="new")
    # print(runs)
    # for run in runs:
    #     for p in run.players:
    #         if p.name == "mahkra":
    #             success = api.change_run_status(run, status="verified")
    # print(success)
    # cat = game.categories["Fastest"]
    # print(api.generic_get(endpoint="platforms"))
    # lvl = game.levels["Wayne Manor"]
    # lbrd = api.get_leaderboard(
    #     game, cat, lvl, variables=[(cat.variables["Version"], "PC")]
    # )
    # print(lbrd, lbrd.top_runs)
    # for _, cat in game.categories.items():
    #     print(cat.name)
    #     for _, v in cat.variables.items():
    #         print(f"{v} {v.mandatory} {v.obsoletes=} {v.is_subcategory=}")
    # runs: list[Run] = api.get_runs(game, category=cat.id)
    # for run in runs:
    #     print(run)


if __name__ == "__main__":
    main()
