import os

from flask import Flask, render_template, request, jsonify
import requests
from dotenv import load_dotenv
import time
from datetime import datetime, timezone
from typing import Any, TypedDict

load_dotenv()  # loads variables from .env into environment

team_number = os.getenv("TEAM_NUMBER")
default_year = os.getenv("DEFAULT_YEAR")
base_url = os.getenv("BASE_URL")
api_key = os.getenv("API_KEY")

#check if all .env variables are set
if not team_number or not default_year or not base_url or not api_key:
    raise ValueError("Missing required environment variables")

headers = {
        "X-TBA-Auth-Key": api_key
}

app = Flask(__name__)

# Very small in-memory TTL cache to avoid re-hitting TBA too frequently (e.g. 7-min refresh)


class _TbaCacheEntry(TypedDict):
    expires_at: float
    value: Any


_TBA_CACHE: dict[str, _TbaCacheEntry] = {}


def _cache_get(key: str):
    entry = _TBA_CACHE.get(key)
    if entry is None:
        return None
    if entry["expires_at"] < time.time():
        _TBA_CACHE.pop(key, None)
        return None
    return entry["value"]


def _cache_set(key: str, value, ttl_seconds: int):
    _TBA_CACHE[key] = {
        "expires_at": time.time() + ttl_seconds,
        "value": value,
    }


def tba_get_json(url: str, ttl_seconds: int = 420):
    cached = _cache_get(url)
    if cached is not None:
        return cached

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return None

    data = resp.json()
    _cache_set(url, data, ttl_seconds=ttl_seconds)
    return data

@app.route('/')
def index():
    # print('Just before API request')
    response = get_team_events()
    print('Just after API request')
    data = response.get_json(silent=True) or {}
    print(data)
    return render_template('index.html', items=data.get('events', []), team_number=team_number)

@app.route('/get_team_events', methods=['POST'])
def get_team_events():

    # Get team events for the year
    team_events_endpoint = f"{base_url}/team/frc{team_number}/events/{default_year}"
    response = requests.get(team_events_endpoint, headers=headers)
    # print(response.json())
    if response.status_code == 200:
        events = response.json()
        event_list = []
        for event in events:
            event_list.append({
                'key': event['key'],
                'name': event['name'],
                'start_date': event['start_date']
            })
        # Sort events by start date
        event_list.sort(key=lambda x: x['start_date'])
        # print({'success': True, 'events': event_list})
        return jsonify({'success': True, 'events': event_list})
    else:
        return jsonify({'success': False, 'error': f"Error {response.status_code}: {response.reason}"})


@app.route('/analyze', methods=['POST'])
def analyze():
    event_key = request.form.get('event_key')
    if not event_key:
        return jsonify({'success': False, 'error': 'Missing event_key'}), 400

    event_endpoint = f"{base_url}/event/{event_key}"
    matches_endpoint = f"{event_endpoint}/matches"
    teams_endpoint = f"{event_endpoint}/teams"

    matches_resp = requests.get(matches_endpoint, headers=headers)
    teams_resp = requests.get(teams_endpoint, headers=headers)

    if matches_resp.status_code != 200:
        return jsonify({'success': False, 'error': f"Error {matches_resp.status_code}: {matches_resp.reason}"}), 502
    if teams_resp.status_code != 200:
        return jsonify({'success': False, 'error': f"Error {teams_resp.status_code}: {teams_resp.reason}"}), 502

    matches = matches_resp.json() or []
    teams = teams_resp.json() or []

    team_key = f"frc{team_number}"

    team_totals = {}
    match_breakdown = []
    rp_match_nums = []
    rp_running_total = []
    pen_match_nums = []
    pen_diff_by_match = []

    rp_total = 0

    def _apply_penalties(alliance_teams, awarded, opponent_awarded):
        for t in alliance_teams:
            if t not in team_totals:
                team_totals[t] = {'pen_total': 0, 'pen_diff': 0, 'matches': 0}
            team_totals[t]['pen_total'] += awarded
            team_totals[t]['pen_diff'] += (awarded - opponent_awarded)
            team_totals[t]['matches'] += 1

    for match in matches:
        if match.get('comp_level') != 'qm':
            continue

        match_num = match.get('match_number')
        sb = match.get('score_breakdown') or {}

        blue = (match.get('alliances') or {}).get('blue', {})
        red = (match.get('alliances') or {}).get('red', {})
        blue_teams = blue.get('team_keys') or []
        red_teams = red.get('team_keys') or []

        blue_rp = (sb.get('blue') or {}).get('rp', 0) if sb else 0
        red_rp = (sb.get('red') or {}).get('rp', 0) if sb else 0

        blue_pen_awarded = (sb.get('red') or {}).get('foulPoints', 0) if sb else 0
        red_pen_awarded = (sb.get('blue') or {}).get('foulPoints', 0) if sb else 0

        _apply_penalties(blue_teams, blue_pen_awarded, red_pen_awarded)
        _apply_penalties(red_teams, red_pen_awarded, blue_pen_awarded)

        in_blue = team_key in blue_teams
        in_red = team_key in red_teams
        if in_blue or in_red:
            team_rp = blue_rp if in_blue else red_rp
            against_team_pen = blue_pen_awarded if in_blue else red_pen_awarded
            against_opponent_pen = red_pen_awarded if in_blue else blue_pen_awarded

            rp_total += team_rp
            rp_match_nums.append(match_num)
            rp_running_total.append(rp_total)

            diff = against_team_pen - against_opponent_pen
            pen_match_nums.append(match_num)
            pen_diff_by_match.append(diff)
            match_breakdown.append({
                'match_num': match_num,
                'against_team': against_team_pen,
                'against_opponent': against_opponent_pen,
                'difference': diff
            })

    for team in teams:
        key = team.get('key')
        if not key:
            continue
        if key not in team_totals:
            team_totals[key] = {'pen_total': 0, 'pen_diff': 0, 'matches': 0}

    total_rankings = [
        {'team': k.replace('frc', ''), 'score': v['pen_total']}
        for k, v in team_totals.items()
    ]
    diff_rankings = [
        {'team': k.replace('frc', ''), 'diff': v['pen_diff']}
        for k, v in team_totals.items()
    ]

    total_rankings.sort(key=lambda x: x['score'])
    diff_rankings.sort(key=lambda x: x['diff'])

    return jsonify({
        'success': True,
        'rp': {
            'match_nums': rp_match_nums,
            'running_total': rp_running_total,
        },
        'pen': {
            'match_nums': pen_match_nums,
            'diff_by_match': pen_diff_by_match,
        },
        'total_rankings': total_rankings,
        'diff_rankings': diff_rankings,
        'match_breakdown': match_breakdown,
    })


@app.route('/event_data', methods=['POST'])
def event_data():
    event_key = request.form.get('event_key')
    if not event_key:
        return jsonify({'success': False, 'error': 'Missing event_key'}), 400

    team_key = f"frc{team_number}"
    event_endpoint = f"{base_url}/event/{event_key}"
    matches_simple_endpoint = f"{event_endpoint}/matches/simple"
    rankings_endpoint = f"{event_endpoint}/rankings"
    teams_endpoint = f"{event_endpoint}/teams/simple"

    matches = tba_get_json(matches_simple_endpoint) or []
    rankings = tba_get_json(rankings_endpoint) or {}
    teams = tba_get_json(teams_endpoint) or []

    # -----------------
    # Current team stats
    # -----------------
    current_rank = None
    current_rp = None
    record = None

    for row in (rankings.get('rankings') or []):
        if (row.get('team_key') or '') == team_key:
            current_rank = row.get('rank')
            current_rp = row.get('sort_orders', [None])[0] if isinstance(row.get('sort_orders'), list) else None
            record = row.get('record')
            break

    # Next scheduled match for this team
    next_match = None
    upcoming = []
    now = int(time.time())

    def _get_qm_alliances(match_obj):
        if match_obj.get('comp_level') != 'qm':
            return None
        alliances_obj = match_obj.get('alliances') or {}
        red_keys_local = (alliances_obj.get('red') or {}).get('team_keys') or []
        blue_keys_local = (alliances_obj.get('blue') or {}).get('team_keys') or []
        if team_key not in red_keys_local and team_key not in blue_keys_local:
            return None
        return red_keys_local, blue_keys_local

    team_qm = []
    for m in matches:
        alliance_keys = _get_qm_alliances(m)
        if alliance_keys is None:
            continue
        red_keys, blue_keys = alliance_keys
        team_qm.append((m, red_keys, blue_keys))

        # Prefer actual_time, fall back to predicted_time, then time
        t = m.get('actual_time') or m.get('predicted_time') or m.get('time')
        if not t:
            continue

        if m.get('actual_time') is None and t >= now:
            upcoming.append((t, m, red_keys, blue_keys))

    if upcoming:
        upcoming.sort(key=lambda x: x[0])
        _, nm, red_keys, blue_keys = upcoming[0]
        is_red = team_key in red_keys
        teammates = [t.replace('frc', '') for t in (red_keys if is_red else blue_keys) if t != team_key]
        opponents = [t.replace('frc', '') for t in (blue_keys if is_red else red_keys)]
        next_match = {
            'match_number': nm.get('match_number'),
            'scheduled_time': nm.get('time'),
            'predicted_time': nm.get('predicted_time'),
            'bumper_color': 'red' if is_red else 'blue',
            'teammates': teammates,
            'opponents': opponents,
        }

    # Average time between this team's completed qualifier matches
    completed_times = []
    for m, _, _ in team_qm:
        if m.get('actual_time'):
            completed_times.append(int(m['actual_time']))
    completed_times.sort()
    avg_match_gap_seconds = None
    if len(completed_times) >= 2:
        gaps = [b - a for a, b in zip(completed_times, completed_times[1:]) if b > a]
        if gaps:
            avg_match_gap_seconds = sum(gaps) / len(gaps)

    # -----------------
    # Per-team scoring summary (qual matches only; completed only)
    # -----------------
    all_teams = [t.get('key') for t in teams if t.get('key')]

    ranking_map = {}
    for row in (rankings.get('rankings') or []):
        tk = row.get('team_key')
        rk = row.get('rank')
        if tk and rk is not None:
            ranking_map[tk] = rk

    # Exclude teams with rank 0 (not ranked / not in rankings response)
    ranked_teams = [tk for tk in all_teams if ranking_map.get(tk, 0) != 0]

    team_rows = {
        tk: {
            'rank': ranking_map.get(tk, 0),
            'team': tk.replace('frc', ''),
            'matches': 0,
            'avg_alliance_score': 0.0,
            'avg_opponent_score': 0.0,
            'avg_margin': 0.0,
        }
        for tk in ranked_teams
    }

    # Temporary sums
    sums = {tk: {'as': 0, 'os': 0, 'm': 0} for tk in ranked_teams}

    for m in matches:
        if m.get('comp_level') != 'qm':
            continue
        if m.get('actual_time') is None:
            continue

        alliances = m.get('alliances') or {}
        red = alliances.get('red') or {}
        blue = alliances.get('blue') or {}
        red_keys = red.get('team_keys') or []
        blue_keys = blue.get('team_keys') or []
        red_score = red.get('score')
        blue_score = blue.get('score')
        if red_score is None or blue_score is None:
            continue

        for tk in red_keys:
            if tk in sums:
                sums[tk]['as'] += red_score
                sums[tk]['os'] += blue_score
                sums[tk]['m'] += 1

        for tk in blue_keys:
            if tk in sums:
                sums[tk]['as'] += blue_score
                sums[tk]['os'] += red_score
                sums[tk]['m'] += 1

    table = []
    for tk in ranked_teams:
        match_count = sums[tk]['m']
        if match_count > 0:
            team_rows[tk]['matches'] = match_count
            team_rows[tk]['avg_alliance_score'] = round(sums[tk]['as'] / match_count, 2)
            team_rows[tk]['avg_opponent_score'] = round(sums[tk]['os'] / match_count, 2)
            team_rows[tk]['avg_margin'] = round((sums[tk]['as'] - sums[tk]['os']) / match_count, 2)
        table.append(team_rows[tk])

    # Sort by avg alliance score descending, then matches desc
    table.sort(key=lambda r: (r['avg_alliance_score'], r['matches']), reverse=True)

    return jsonify({
        'success': True,
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'team_stats': {
            'rank': current_rank,
            'rp': current_rp,
            'record': record,
            'avg_match_gap_seconds': avg_match_gap_seconds,
            'next_match': next_match,
        },
        'scoring_table': table,
    })


if __name__ == '__main__':
    app.run(debug=True)