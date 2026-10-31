"""Physical AI: reproducible grid robot Q-learning comparison.

Run: python run_experiment.py
Colab: no GPU, ROS, Docker required. Simulated discrete grid, not a physics engine.
All scenarios are trained from scratch unless explicitly called 'original policy'.
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SIZE = 8
START = (0, 0)
GOAL = (7, 7)
SEED = 2026
TRAIN_EPISODES = 6000
MAX_TRAIN_STEPS = 80
MAX_TEST_STEPS = 40
ACTIONS = ((-1, 0), (0, 1), (1, 0), (0, -1))
BASE_OBSTACLES = frozenset({
    (1,1), (1,2), (1,3), (2,3), (3,3), (4,3),
    (5,1), (5,2), (5,3), (4,5), (5,5), (6,5)
})
# Experiments requested by the user + an additional on-route obstruction.
# This is equivalent to adding OBSTACLES.add((3, 6)) *after*
# the original model has been trained; use a separate copy to preserve the baseline.
OBSTACLES = set(BASE_OBSTACLES)
OBSTACLES.add((3, 6))
OBSTACLES_OFF_ROUTE = frozenset(OBSTACLES)

# Extra test: add an obstacle on the original learned route.
OBSTACLES = set(BASE_OBSTACLES)
OBSTACLES.add((6, 2))
OBSTACLES_ON_ROUTE = frozenset(OBSTACLES)
OUTPUT = Path('results')


def step(pos, action, obstacles):
    dr, dc = ACTIONS[action]
    nxt = (pos[0]+dr, pos[1]+dc)
    blocked = (not 0 <= nxt[0] < SIZE or not 0 <= nxt[1] < SIZE or nxt in obstacles)
    if blocked:
        return pos, -1.0, False, True
    if nxt == GOAL:
        return nxt, 10.0, True, False
    return nxt, -0.08, False, False


def train(obstacles, seed=SEED, episodes=TRAIN_EPISODES):
    rng = np.random.default_rng(seed)
    q = np.zeros((SIZE, SIZE, len(ACTIONS)), dtype=np.float64)
    train_success = []
    t0 = time.perf_counter()
    for episode in range(episodes):
        pos, reached = START, False
        epsilon = max(0.04, 0.95 * 0.9985 ** episode)
        for _ in range(MAX_TRAIN_STEPS):
            a = int(rng.integers(4)) if rng.random() < epsilon else int(np.argmax(q[pos]))
            nxt, reward, done, _ = step(pos, a, obstacles)
            target = reward if done else reward + 0.95 * np.max(q[nxt])
            q[pos][a] += 0.22 * (target - q[pos][a])
            pos = nxt
            if done:
                reached = True
                break
        train_success.append(reached)
    return q, train_success, time.perf_counter() - t0


def run_episode(q, obstacles, *, seed=0, max_steps=MAX_TEST_STEPS):
    rng = np.random.default_rng(seed)
    pos = START
    states, actions, blocked_count = [pos], [], 0
    for _ in range(max_steps):
        a = int(np.argmax(q[pos])) if q is not None else int(rng.integers(4))
        pos, _, done, blocked = step(pos, a, obstacles)
        states.append(pos)
        actions.append(a)
        blocked_count += int(blocked)
        if done:
            break
    return dict(states=states, actions=actions, success=(pos==GOAL),
                steps=len(actions), blocked=blocked_count)


def evaluate(q, obstacles, trials=100):
    runs = [run_episode(q, obstacles, seed=1000+i) for i in range(trials)]
    return {
        'success_rate_percent': 100 * sum(x['success'] for x in runs) / trials,
        'mean_steps': sum(x['steps'] for x in runs) / trials,
        'mean_blocked_moves': sum(x['blocked'] for x in runs) / trials,
    }


def font(size, bold=False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    places = [f'/usr/share/fonts/truetype/dejavu/{name}',
              '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
    for path in places:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

FB = font(31, True)
FM = font(21, True)
FS = font(18)
FT = font(15)


def draw_map(d, obstacles, result, count, *, origin=(38, 111), cell=49):
    ox, oy = origin
    def xy(p):
        return (int(ox+p[1]*cell+cell/2-2), int(oy+p[0]*cell+cell/2-2))
    for r in range(SIZE):
        for c in range(SIZE):
            x, y = ox+c*cell, oy+r*cell
            fill = (148, 80, 72) if (r,c) in obstacles else (29, 46, 65)
            d.rounded_rectangle((x,y,x+cell-4,y+cell-4), radius=5,
                                fill=fill, outline=(76, 96, 116))
    gx, gy = xy(GOAL)
    d.ellipse((gx-16,gy-16,gx+16,gy+16), fill=(40,173,128),outline='white',width=2)
    d.text((gx-8,gy-12),'G',fill='white',font=FM)
    n = min(len(result['actions']),max(0,count))
    states = result['states'][:n+1]
    if len(states)>1:
        d.line([xy(p) for p in states],fill=(85,222,173),width=5)
    x, y=xy(result['states'][n])
    d.ellipse((x-18,y-18,x+18,y+18), fill=(54,156,236),outline='white',width=3)
    d.ellipse((x-4,y-4,x+4,y+4), fill='white')
    return n


def draw_frame(t, scenario_data):
    # 112 seconds, 6fps. More than one minute and below three minutes.
    stages = [
        (0,10,'Physical AI: learning to navigate','Overview',0),
        (10,30,'A: original map / trained AI','original',1),
        (30,50,'B: add (3,6) / SAME AI','off_old',2),
        (50,73,'C: add (6,2) / SAME AI','on_old',3),
        (73,96,'D: add (6,2) / RETRAINED AI','on_new',4),
        (96,112,'Results and limitations','summary',5),
    ]
    start, end, title, key, stage_n = next(x for x in stages if x[0] <= t < x[1])
    w, h = 960, 540
    img=Image.new('RGB',(w,h),(13,21,35))
    d=ImageDraw.Draw(img)
    d.text((33,19),'Physical AI | Q-learning navigation',fill=(244,249,255),font=FB)
    d.text((33,61),'2D grid simulation / CPU / 6,000 training episodes',fill=(175,195,216),font=FS)
    if key=='summary':
        s=scenario_data
        rows=[
            ('Original map + learned AI',s['original']['eval']['success_rate_percent']),
            ('Add (3,6) + old AI',s['off_old']['eval']['success_rate_percent']),
            ('Add (3,6) + retrained AI',s['off_new']['eval']['success_rate_percent']),
            ('Add (6,2) + old AI',s['on_old']['eval']['success_rate_percent']),
            ('Add (6,2) + retrained AI',s['on_new']['eval']['success_rate_percent']),
        ]
        d.text((40,110),'Goal success in fixed-start repeated tests',fill='white',font=FM)
        for i,(label,rate) in enumerate(rows):
            y=160+i*56
            d.text((48,y),label,fill=(230,238,246),font=FS)
            d.rectangle((435,y+2,435+round(rate)*3.7,y+24),fill=(46,178,138) if rate else (215,114,93))
            d.text((825,y),f'{rate:.0f}%',fill='white',font=FS)
        d.text((42,471),'Caution: repeated deterministic runs, not unseen-map generalization.',fill=(235,192,110),font=FT)
    else:
        scene_key='original' if key=='Overview' else key
        sc=scenario_data[scene_key]
        obstacles=sc['obstacles']
        run=sc['run']
        n = 0 if stage_n==0 else int((t-start)*1.05)
        n=draw_map(d,obstacles,run,n)
        d.text((460,118),title,fill=(237,245,253),font=FM)
        d.text((460,168),f'Obstacles: {len(obstacles)}',fill=(189,205,226),font=FS)
        d.text((460,210),f'Actions shown: {n} / {len(run["actions"])}',fill=(189,205,226),font=FS)
        d.text((460,250),f'Goal reached: {"YES" if n==len(run["actions"]) and run["success"] else "NO / in progress"}',fill=(198,226,232),font=FS)
        d.text((460,295),f'Blocked moves (final): {run["blocked"]}',fill=(189,205,226),font=FS)
        if key == 'Overview':
            note=['Study question: does a learned policy', 'adapt when the obstacle map changes?', 'Compare without and with retraining.']
        elif key == 'off_old':
            note=['Added (3,6) is NOT on the initial path.', 'An unchanged outcome is still a result.']
        elif key == 'on_old':
            note=['Added (6,2) blocks the initial path.', 'Old policy can keep trying a blocked cell.']
        elif key == 'on_new':
            note=['Retrain in the new environment.', 'New policy may discover an alternate route.']
        else:
            note=['Original policy on the original map.', 'Shortest path from (0,0) to (7,7):', 'at least 14 moves without diagonal actions.']
        for j,line in enumerate(note):
            d.text((460,354+j*29),line,fill=(122,219,181) if j==0 else (197,208,224),font=FT)
    d.line((33,508,927,508),fill=(62,85,106),width=2)
    d.text((35,518),'Discrete grid robot, NOT real hardware or a physics-engine simulation',fill=(156,170,189),font=FT)
    return np.asarray(img, dtype=np.uint8)


def make_video(scenarios, dest=OUTPUT/'comparison_demo.mp4', fps=6, secs=112):
    if not shutil.which('ffmpeg'):
        raise RuntimeError('ffmpeg missing. In Colab: !apt-get -qq install ffmpeg')
    cmd=['ffmpeg','-y','-hide_banner','-loglevel','error',
         '-f','rawvideo','-vcodec','rawvideo','-s','960x540','-pix_fmt','rgb24',
         '-r',str(fps),'-i','-','-an','-vcodec','libx264','-preset','ultrafast',
         '-crf','25','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for j in range(secs*fps):
            p.stdin.write(draw_frame(j/fps,scenarios).tobytes())
        p.stdin.close()
        err=p.stderr.read().decode(errors='replace')
        status=p.wait()
        if status != 0:
            raise RuntimeError(f'ffmpeg exited {status}: {err}')
    except Exception:
        if p.poll() is None:p.kill()
        raise
    return dest


def make_route_image(scenarios, dest=OUTPUT/'route_comparison.png'):
    img=Image.new('RGB',(1200,525),(13,21,35))
    d=ImageDraw.Draw(img)
    keys=['original','off_old','on_old']
    titles=['A ORIGINAL 12','B ADD (3,6) 13','C ADD (6,2) 13']
    for j,(key,title) in enumerate(zip(keys,titles)):
        sc=scenarios[key]
        x0=j*400
        d.text((x0+22,24),title,fill=(234,243,253),font=FM)
        draw_map(d,sc['obstacles'],sc['run'],len(sc['run']['actions']),origin=(x0+13,77),cell=44)
        d.text((x0+23,463),'SUCCESS' if sc['run']['success'] else 'FAILED',fill=(67,220,152) if sc['run']['success'] else (240,130,111),font=FS)
    img.save(dest)
    return dest


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    base_q, base_history, t_base = train(BASE_OBSTACLES)
    off_q, off_history, t_off = train(OBSTACLES_OFF_ROUTE)
    on_q, on_history, t_on = train(OBSTACLES_ON_ROUTE)
    np.save(OUTPUT/'q_original.npy',base_q)
    np.save(OUTPUT/'q_with_3_6.npy',off_q)
    np.save(OUTPUT/'q_with_6_2.npy',on_q)

    specs=[
        ('random','Original environment / random','original',BASE_OBSTACLES,None),
        ('original','Original environment / trained AI','original',BASE_OBSTACLES,base_q),
        ('off_old','Add (3,6) / original AI','off',OBSTACLES_OFF_ROUTE,base_q),
        ('off_new','Add (3,6) / retrained AI','off',OBSTACLES_OFF_ROUTE,off_q),
        ('on_old','Add (6,2) / original AI','on',OBSTACLES_ON_ROUTE,base_q),
        ('on_new','Add (6,2) / retrained AI','on',OBSTACLES_ON_ROUTE,on_q),
    ]
    scenarios={}
    rows=[]
    for key,label,kind,obstacles,policy in specs:
        run=run_episode(policy,obstacles,seed=1234 if policy is None else 0)
        ev=evaluate(policy,obstacles)
        rows.append(dict(condition=label, obstacles=len(obstacles),
                         success_rate_percent=ev['success_rate_percent'],
                         mean_steps=round(ev['mean_steps'],1),
                         mean_blocked_moves=round(ev['mean_blocked_moves'],1),
                         one_run_success=int(run['success']),
                         one_run_steps=run['steps'],one_run_blocked=run['blocked']))
        scenarios[key]=dict(label=label,obstacles=obstacles,run=run,eval=ev)
    with (OUTPUT/'comparison_results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]))
        wr.writeheader();wr.writerows(rows)
    path_orig=scenarios['original']['run']['states']
    report={
        'seed':SEED, 'train_episodes':TRAIN_EPISODES,
        'train_time_seconds':{'original':t_base,'add_3_6':t_off,'add_6_2':t_on},
        'training_success_last_100_pct':{
            'original':sum(base_history[-100:]),
            'add_3_6':sum(off_history[-100:]),
            'add_6_2':sum(on_history[-100:])},
        'original_route':[list(x) for x in path_orig],
        'does_original_route_use_3_6':(3,6) in path_orig,
        'does_original_route_use_6_2':(6,2) in path_orig,
        'fixed_start_goal':True,
        'deterministic_ai_repeated_100_times':True,
        'scenario_results':rows,
        'limitations':'Discrete 2D grid only. 100 repeated deterministic policy evaluations with same start and goal are NOT 100 independent trials; no physics engine or real robot.'
    }
    (OUTPUT/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    txt=['Physical AI - Q-learning obstacles comparison',
         f'Seed={SEED}; training episodes={TRAIN_EPISODES}',
         'Obstacle (3,6) on old path? '+str((3,6) in path_orig),
         'Obstacle (6,2) on old path? '+str((6,2) in path_orig),'']
    for r in rows:
        txt.append(f"{r['condition']}: success={r['success_rate_percent']:.1f}%, steps={r['one_run_steps']}, blocked={r['one_run_blocked']}")
    txt+=['','Note: 100 repeats of the deterministic greedy policy use the SAME fixed start/goal.','This is a simplified grid simulation, NOT a physical-engine or hardware experiment.']
    (OUTPUT/'results.txt').write_text('\n'.join(txt)+'\n',encoding='utf-8')
    make_route_image(scenarios)
    print('\n'.join(txt))
    print('Creating 112-second comparison video...')
    p=make_video(scenarios)
    print('Created:',p,'bytes:',p.stat().st_size)
    return report

if __name__ == '__main__':
    main()
