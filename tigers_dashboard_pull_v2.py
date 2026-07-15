"""
Tigers dashboard extraction v2 -- monthly built from game logs (confirmed path).

Run from a terminal:
    cd C:\\Users\\kronk\\Downloads     (or wherever this file is)
    python tigers_dashboard_pull_v2.py

Fixes from v1's run:
  - CSVs now write NEXT TO THIS FILE, not the shell's current directory
    (v1 tried to write into C:\\WINDOWS\\system32 because the shell was there).
  - byMonth stat type failed at both scopes (500 / empty), so monthly tables
    are now BUILT from team game logs -- the confirmed-working pull -- by
    grouping games by month and recomputing rates from summed components.
  - Player pulls now use playerPool=ALL (v1's default returned only
    title-qualified players: 4 hitters, 1 pitcher).

What it writes (CSV per section):
  A. tigers_team_{hitting,pitching,fielding}_season   -- KPI cards
  B. tigers_hitting_bymonth, tigers_pitching_bymonth  -- monthly story
  C. tigers_players_{hitting,pitching}_season         -- leaderboards (full roster)
  D. {central,al,mlb}_hitting_bymonth                 -- benchmark lines
     (pooled from 5 / 15 / 30 team game logs; ids read from standings)
"""

import os
import traceback

TIGERS = 116
SEASON = 2026
CENTRAL_DIV = 202

# Write outputs next to this file, regardless of the shell's directory
try:
    OUT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    OUT_DIR = os.getcwd()

HIT_FIELDS = ['atBats', 'hits', 'baseOnBalls', 'hitByPitch', 'sacFlies',
              'totalBases', 'homeRuns', 'runs', 'strikeOuts', 'doubles',
              'triples', 'rbi', 'stolenBases', 'plateAppearances']
PITCH_FIELDS = ['earnedRuns', 'runs', 'hits', 'baseOnBalls', 'strikeOuts',
                'homeRuns', 'battersFaced']


def ip_to_outs(ip_str):
    """MLB innings strings use thirds: '8.2' = 8 innings + 2 outs = 26 outs."""
    try:
        s = str(ip_str)
        if '.' in s:
            whole, frac = s.split('.')
            return int(whole) * 3 + int(frac)
        return int(s) * 3
    except (ValueError, TypeError):
        return 0


def add_hitting_rates(g):
    """Recompute rate stats from summed components (never average rates)."""
    denom_obp = g['atBats'] + g['baseOnBalls'] + g['hitByPitch'] + g['sacFlies']
    g['AVG'] = (g['hits'] / g['atBats']).round(3)
    g['OBP'] = ((g['hits'] + g['baseOnBalls'] + g['hitByPitch']) / denom_obp).round(3)
    g['SLG'] = (g['totalBases'] / g['atBats']).round(3)
    g['OPS'] = (g['OBP'] + g['SLG']).round(3)
    return g


def main():
    import statsapi
    import pandas as pd

    outputs = []

    def save(name, df):
        outputs.append((name, df))

    def stat_frame(splits, lead=None):
        rows = []
        for s in splits:
            row = {}
            if lead:
                for key, path in lead.items():
                    val = s
                    for p in path:
                        val = (val or {}).get(p) if isinstance(val, dict) else None
                    row[key] = val
            row.update(s.get('stat', {}))
            rows.append(row)
        return pd.DataFrame(rows)

    # ---- A. Tigers team season aggregates (confirmed working) ----
    for group in ['hitting', 'pitching', 'fielding']:
        label = 'A team season ' + group
        try:
            r = statsapi.get('team_stats',
                {'teamId': TIGERS, 'season': SEASON, 'group': group,
                 'stats': 'season', 'gameType': 'R'})
            df = stat_frame(r['stats'][0]['splits'])
            print('[ok]   ' + label + ': ' + str(df.shape[0]) + 'x' + str(df.shape[1]))
            save('tigers_team_' + group + '_season', df)
        except Exception as e:
            print('[fail] ' + label + ': ' + type(e).__name__ + ' -- ' + str(e)[:120])

    # ---- helper: pull one team's game log rows for a group ----
    def gamelog_rows(team_id, team_name, group, fields):
        r = statsapi.get('team_stats',
            {'teamId': team_id, 'season': SEASON, 'group': group,
             'stats': 'gameLog', 'gameType': 'R'})
        splits = r['stats'][0]['splits']
        rows = []
        for s in splits:
            stat = s.get('stat', {})
            row = {'team': team_name, 'date': s.get('date')}
            for f in fields:
                row[f] = stat.get(f, 0)
            if group == 'pitching':
                row['outs'] = ip_to_outs(stat.get('inningsPitched', 0))
            rows.append(row)
        return rows

    # ---- B. Tigers monthly, built from game logs ----
    try:
        df = pd.DataFrame(gamelog_rows(TIGERS, 'Detroit Tigers', 'hitting', HIT_FIELDS))
        df['month'] = pd.to_datetime(df['date']).dt.month
        g = df.groupby('month')[HIT_FIELDS].sum().reset_index()
        g = add_hitting_rates(g)
        print('[ok]   B tigers hitting bymonth: ' + str(len(g)) + ' months from ' + str(len(df)) + ' games')
        save('tigers_hitting_bymonth', g)
    except Exception as e:
        print('[fail] B tigers hitting bymonth: ' + type(e).__name__ + ' -- ' + str(e)[:120])

    try:
        df = pd.DataFrame(gamelog_rows(TIGERS, 'Detroit Tigers', 'pitching', PITCH_FIELDS))
        df['month'] = pd.to_datetime(df['date']).dt.month
        cols = PITCH_FIELDS + ['outs']
        g = df.groupby('month')[cols].sum().reset_index()
        ip = g['outs'] / 3.0
        g['IP'] = ip.round(1)
        g['ERA'] = (9 * g['earnedRuns'] / ip).round(2)
        g['WHIP'] = ((g['baseOnBalls'] + g['hits']) / ip).round(2)
        g['K9'] = (9 * g['strikeOuts'] / ip).round(1)
        g['BB9'] = (9 * g['baseOnBalls'] / ip).round(1)
        print('[ok]   B tigers pitching bymonth: ' + str(len(g)) + ' months from ' + str(len(df)) + ' games')
        save('tigers_pitching_bymonth', g)
    except Exception as e:
        print('[fail] B tigers pitching bymonth: ' + type(e).__name__ + ' -- ' + str(e)[:120])

    # ---- C. Tigers players season, FULL roster ----
    for group in ['hitting', 'pitching']:
        label = 'C players ' + group
        try:
            r = statsapi.get('stats',
                {'stats': 'season', 'group': group, 'teamId': TIGERS,
                 'season': SEASON, 'gameType': 'R', 'limit': 200,
                 'playerPool': 'ALL'})
            df = stat_frame(r['stats'][0]['splits'], lead={
                'player': ['player', 'fullName'],
                'playerId': ['player', 'id'],
                'position': ['position', 'abbreviation']})
            print('[ok]   ' + label + ': ' + str(df.shape[0]) + ' players')
            save('tigers_players_' + group + '_season', df)
        except Exception as e:
            print('[fail] ' + label + ': ' + type(e).__name__ + ' -- ' + str(e)[:120])

    # ---- D. Benchmarks monthly: Central, AL, MLB -- pooled from game logs ----
    try:
        st = statsapi.get('standings',
            {'leagueId': '103,104', 'season': SEASON, 'standingsTypes': 'regularSeason'})
        teams = []  # (id, name, division_id, league: 'AL'/'NL')
        for block in st['records']:
            div_id = block.get('division', {}).get('id')
            lg = 'AL' if block.get('league', {}).get('id') == 103 else 'NL'
            for tr in block['teamRecords']:
                teams.append((tr['team']['id'], tr['team']['name'], div_id, lg))
        print('[ok]   D standings: ' + str(len(teams)) + ' teams found')
    except Exception as e:
        print('[fail] D standings: ' + type(e).__name__ + ' -- ' + str(e)[:120])
        teams = []

    if teams:
        all_rows = []
        pulled = 0
        for tid, name, div_id, lg in teams:
            try:
                all_rows.extend(gamelog_rows(tid, name, 'hitting', HIT_FIELDS))
                pulled += 1
            except Exception as e:
                print('  [fail] gamelog ' + name + ': ' + type(e).__name__)
        print('[ok]   D game logs pulled for ' + str(pulled) + '/' + str(len(teams)) + ' teams')

        big = pd.DataFrame(all_rows)
        big['month'] = pd.to_datetime(big['date']).dt.month
        id_by_name = {name: (div_id, lg) for _, name, div_id, lg in
                      [(t[0], t[1], t[2], t[3]) for t in teams]}
        big['div'] = big['team'].map(lambda n: id_by_name.get(n, (None, None))[0])
        big['lg'] = big['team'].map(lambda n: id_by_name.get(n, (None, None))[1])

        scopes = [
            ('central_hitting_bymonth', big[big['div'] == CENTRAL_DIV]),
            ('al_hitting_bymonth', big[big['lg'] == 'AL']),
            ('mlb_hitting_bymonth', big),
        ]
        for name, subset in scopes:
            if subset.empty:
                print('  (empty scope) ' + name)
                continue
            g = subset.groupby('month')[HIT_FIELDS].sum().reset_index()
            g = add_hitting_rates(g)
            save(name, g)
            print('[ok]   D ' + name + ': ' + str(len(g)) + ' months, ' + str(subset["team"].nunique()) + ' teams pooled')

    # ---- write everything next to this file ----
    print('\n--- writing CSVs to ' + OUT_DIR + ' ---')
    for name, df in outputs:
        if df is None or df.empty:
            print('  (skipped empty) ' + name)
            continue
        path = os.path.join(OUT_DIR, name + '_' + str(SEASON) + '.csv')
        df.to_csv(path, index=False)
        print('  ' + name + ': ' + str(df.shape[0]) + 'x' + str(df.shape[1]) + ' -> ' + path)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('\nERROR -- details below:')
        traceback.print_exc()
    finally:
        try:
            input('\nPress Enter to close...')
        except EOFError:
            pass
