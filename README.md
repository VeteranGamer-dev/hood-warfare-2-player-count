# Hood Warfare 2 player count tracker

How many people are playing [Hood Warfare 2](https://store.steampowered.com/app/5155360/Hood_Warfare_2/) on Steam, recorded every hour since October 12, 2026. The chart and the numbers below update automatically.

![Hood Warfare 2 concurrent players on Steam, hourly](chart.png)

<!-- stats:start -->
| | Players | When (US Eastern) |
|---|---:|---|
| Latest reading | **7,808** | Oct 12, 2026, 7:14 PM EDT |
| Peak in the last 24 hours | 7,808 | Oct 12, 2026, 7:14 PM EDT |
| Highest reading recorded | 7,808 | Oct 12, 2026, 7:14 PM EDT |

4 readings since Oct 12, 2026, 9:04 AM EDT.
<!-- stats:end -->

## What the number means

This is the number Steam reports as "in game" right now. It counts everyone who has Hood Warfare 2 open, including people sitting in menus and people playing bot matches. That's why the in-game lobby list can look much emptier than this number: it only shows public lobbies you can join at that moment.

For what players think of the game, which platforms it's on, and the player count explained in more detail, see the unofficial fan guide at **[hoodwarfare2.org](https://hoodwarfare2.org/review/#player-count)**.

## The data

[`data/players.csv`](data/players.csv) has one row per reading:

| Column | Meaning |
|---|---|
| `timestamp_utc` | When the reading was taken, in UTC |
| `players` | Concurrent players on Steam at that moment |
| `source` | `steam_api` for automatic hourly readings, `manual` for the two readings taken before the tracker started |

- **Source:** the Steam Web API (`ISteamUserStats/GetNumberOfCurrentPlayers`, app ID 5155360).
- **How often:** a [GitHub Actions workflow](.github/workflows/record.yml) runs once an hour. GitHub sometimes delays or skips scheduled runs, so expect occasional gaps. Readings more than 3 hours apart aren't joined on the chart.
- **Times on the chart** are US Eastern.

## Use it

The data is free to use under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Please credit "Hood Warfare 2 player count tracker" with a link to this repository. The code is MIT-licensed (see [LICENSE](LICENSE)).

Run it yourself:

```
pip install pillow
python scripts/record.py            # take a reading, redraw the chart
python scripts/record.py --render   # redraw from the CSV only
```

Fonts: [Big Shoulders](https://github.com/xotypeco/big_shoulders) and [Inter](https://github.com/rsms/inter), both under the SIL Open Font License (see `fonts/`).

---

Not affiliated with Trapstar Games or Valve.
