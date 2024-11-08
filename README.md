# srcompy
A python library for the speedrun.com API
 
## Examples
### Find a game:
```python
from srcompaipy.srcomapipy import SRC
import srcomapipy.srctypes as st

api = SRC(user_agent="usrename")
# search for a game
games: list[st.Game] = api.search_game("Batman: Arkham City")
print(games)
>>> [<Game: Batman: Arkham City (x3692ldl)>, <Game: Batman: Arkham City Lockdown (9d3808w1)>, <Game: Batman: Arkham City Category Extensions (m1mnnv3d)>]
# get newly submitted runs for a game
bac: st.Game = games[0]
runs: list[st.Run] = api.get_runs(game=bac, status="new")
```
### Get WR of a specific Leaderboard:
```python
# get category and it's variables
cat = bac.categories["Any%"]
var1 = cat.variables["Version"]
var2 = cat.variables["Difficulty"]
lb = api.get_leaderboard(bac, cat, variables=[(var1, "PC"), (var2, "NG+")])
print(lb.wr())
>>> [<Run: RTA-14:30.000 (yox7rk5y)-Any%-'Version'=PC 'Difficulty'=NG+ by Bepsi>]
```
### Search for specific User:
```python
users: list[st.User] = api.get_users(lookup="username")
```
### Exception example:
```python
try:
    game: st.Game = api.get_game(game_id="id")
except SRCAPIException as e:
    print(f"Error: {e.message}")
```
### Change Run Status (Requires API Key):
```python
api = SRC(user_agent="username", api_key="api-key-here")
bac: st.Game = api.search_game("Batman: Arkham City")[0]
# reject a new run
runs: list[st.Run] = api.get_runs(game=bac, status="new")
# returns the run that was changed
run: st.Run = api.change_run_status(runs[0], status="rejected", reason="reason")
```