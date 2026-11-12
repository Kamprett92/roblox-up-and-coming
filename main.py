#!/usr/bin/env python3
"""
Roblox Up-and-Coming Top 10 Forecaster
Predicts which games will hold each of the top 10 places over the next 3 days.

Strategy: Empirical transition model + momentum + stability
- Learn rank transition probabilities from history
- Weight recent snapshots more heavily
- Stable leaders get high probability to stay
- Spread remaining probability across plausible challengers
"""

import json
import os
from collections import defaultdict, Counter

INPUT_DIR = os.environ.get('MAKEFUN_INPUT_DIR', '/input')
OUTPUT_DIR = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')

def load_history():
    snapshots = []
    with open(os.path.join(INPUT_DIR, 'history.ndjson')) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get('ok') and d.get('up_and_coming'):
                snapshots.append(d)
    return snapshots

def load_task():
    with open(os.path.join(INPUT_DIR, 'task.json')) as f:
        return json.load(f)

def main():
    task = load_task()
    places = task.get('places', 10)
    snapshots = load_history()
    
    if not snapshots:
        result = {'probabilities': [], 'top10': []}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, task.get('output', 'forecast.json')), 'w') as f:
            json.dump(result, f)
        return
    
    # Build transition counts: from_rank -> Counter(to_rank)
    transitions = defaultdict(Counter)
    for i in range(len(snapshots) - 1):
        curr = {r['universe_id']: r['rank'] for r in snapshots[i]['up_and_coming'][:15]}
        nxt = {r['universe_id']: r['rank'] for r in snapshots[i+1]['up_and_coming'][:15]}
        for uid, rank in curr.items():
            if rank > 15:
                continue
            if uid in nxt:
                transitions[rank][nxt[uid]] += 1
            else:
                transitions[rank]['out'] += 1
    
    # Convert to probabilities
    trans_prob = {}
    for from_rank, counter in transitions.items():
        total = sum(counter.values())
        trans_prob[from_rank] = {k: v/total for k, v in counter.items()}
    
    last_snap = snapshots[-1]
    last_chart = sorted(last_snap['up_and_coming'], key=lambda r: r['rank'])
    
    # Track game histories for momentum
    games = {}
    for snap in snapshots:
        for row in snap['up_and_coming']:
            uid = row['universe_id']
            if uid not in games:
                games[uid] = {'ranks': [], 'playings': []}
            games[uid]['ranks'].append(row['rank'])
            games[uid]['playings'].append(row.get('playing', 0))
    
    # For each place, compute probability distribution
    probabilities = []
    
    # Get candidate universe_ids (top 20 from last chart)
    candidates = [r['universe_id'] for r in last_chart[:20]]
    last_rank_map = {r['universe_id']: r['rank'] for r in last_chart}
    
    for place in range(1, places + 1):
        # Score each candidate for this place
        scores = {}
        for uid in candidates:
            curr_rank = last_rank_map[uid]
            g = games[uid]
            ranks = g['ranks']
            
            # Base: transition probability from curr_rank to place
            # Use empirical transitions, with smoothing
            if curr_rank in trans_prob and place in trans_prob[curr_rank]:
                base = trans_prob[curr_rank][place]
            else:
                # Fallback: decay with distance
                dist = abs(curr_rank - place)
                base = max(0.02, 0.3 * (0.7 ** dist))
            
            # Boost for recent stability at this rank
            recent = ranks[-5:]
            if len(recent) >= 3:
                # If game has been at or near this place recently, boost
                close_count = sum(1 for r in recent if abs(r - place) <= 1)
                base *= (1 + close_count * 0.15)
            
            # Momentum: if game is climbing and place is above current, boost
            if len(ranks) >= 3:
                # Recent trend (last 3 ranks)
                trend = ranks[-1] - ranks[-3]  # negative = climbing
                if trend < 0 and place < curr_rank:
                    base *= (1 + min(0.4, abs(trend) * 0.1))
                elif trend > 0 and place > curr_rank:
                    base *= (1 + min(0.3, trend * 0.08))
            
            # Player growth boost
            playings = g['playings']
            if len(playings) >= 3 and playings[-3] > 0:
                growth = (playings[-1] - playings[-3]) / playings[-3]
                if growth > 0.5 and place < curr_rank:
                    base *= (1 + min(0.3, growth * 0.2))
            
            scores[uid] = base
        
        # Normalize, cap at 0.55, leave 0.15 unnamed
        total = sum(scores.values())
        if total > 0:
            # Sort by score, take top 8 per place
            sorted_scores = sorted(scores.items(), key=lambda x: -x[1])[:8]
            total_top = sum(s for _, s in sorted_scores)
            for uid, s in sorted_scores:
                p = (s / total_top) * 0.85
                p = min(p, 0.55)
                if p >= 0.03:
                    probabilities.append({
                        'universe_id': uid,
                        'place': place,
                        'p': round(p, 4)
                    })
    
    # Top 10: use last chart order, but adjust for strong momentum
    # Games with strong upward momentum move up 1-2 spots
    top10_scores = []
    for row in last_chart[:15]:
        uid = row['universe_id']
        g = games[uid]
        ranks = g['ranks']
        score = row['rank']
        # Momentum adjustment
        if len(ranks) >= 3:
            trend = ranks[-1] - ranks[-3]
            score += trend * 0.5  # climbing (negative trend) reduces score = higher rank
        # Player growth adjustment
        playings = g['playings']
        if len(playings) >= 3 and playings[-3] > 0:
            growth = (playings[-1] - playings[-3]) / playings[-3]
            if growth > 0.5:
                score -= 0.5
            elif growth < -0.2:
                score += 0.5
        top10_scores.append((score, row['rank'], uid))
    
    top10_scores.sort()
    top10 = [uid for _, _, uid in top10_scores[:places]]
    
    result = {'probabilities': probabilities, 'top10': top10}
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, task.get('output', 'forecast.json')), 'w') as f:
        json.dump(result, f)
        f.write('\n')

if __name__ == '__main__':
    main()
