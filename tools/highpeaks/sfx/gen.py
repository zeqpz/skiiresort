"""Generate raw takes (resumable): art/highpeaks/sfx_raw/<name>_<take>.pcm (int16 LE stereo 24 kHz).
Every call is logged to art/highpeaks/sfx_raw/log.jsonl (name, take, seconds, generation id).
  python gen.py [--max N] [name ...]          python gen.py --cost   (sum the logged calls' real cost)"""
import os, sys, json, time, concurrent.futures as cf, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orapi, spec

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'sfx_raw')
LOG = os.path.join(RAW, 'log.jsonl')
BUDGET = float(os.environ.get('SFX_BUDGET', '8.0'))
_lock = threading.Lock()


def log(rec):
    with _lock, open(LOG, 'a') as f:
        f.write(json.dumps(rec) + '\n')


def one(name, prompt, take):
    out = os.path.join(RAW, f'{name}_{take}.pcm')
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return name, take, 'kept', 0
    t0 = time.time()
    try:
        b, h = orapi.speech(prompt)
    except Exception as e:
        log(dict(name=name, take=take, seconds=0, error=str(e)[:200], t=time.time()))
        return name, take, f'ERR {str(e)[:160]}', 0
    ct = h.get('Content-Type', '')
    open(out + '.part', 'wb').write(b)
    os.replace(out + '.part', out)
    sec = len(b) / 4 / 24000
    log(dict(name=name, take=take, seconds=round(sec, 3), id=h.get('X-Generation-Id'), ct=ct,
             wall=round(time.time() - t0, 1), t=time.time(), prompt=prompt))
    return name, take, f'{sec:.2f}s', sec


def spent():
    """Sum the real cost of every logged call (OpenRouter /generation)."""
    tot, n, miss = 0.0, 0, 0
    for line in open(LOG):
        r = json.loads(line)
        if not r.get('id'):
            continue
        n += 1
        if 'cost' not in r:
            miss += 1
        tot += r.get('cost', 0)
    return tot, n, miss


def fill_costs():
    recs = [json.loads(l) for l in open(LOG)]
    for r in recs:
        if r.get('id') and 'cost' not in r:
            try:
                with orapi._req('/generation?id=' + r['id']) as resp:
                    r['cost'] = float(json.load(resp)['data']['total_cost'])
            except Exception:
                pass
    with open(LOG, 'w') as f:
        for r in recs:
            f.write(json.dumps(r) + '\n')


def main():
    os.makedirs(RAW, exist_ok=True)
    args = sys.argv[1:]
    if args[:1] == ['--cost']:
        fill_costs(); tot, n, miss = spent()
        print(f'{n} calls, ${tot:.4f} (no cost yet for {miss})'); return
    mx = None
    if args[:1] == ['--max']:
        mx = int(args[1]); args = args[2:]
    work = [(n, p, t) for n, p, k, _ in spec.jobs() if not args or n in args
            for t in range(1, k + 1) if not os.path.exists(os.path.join(RAW, f'{n}_{t}.pcm'))]
    if mx is not None:
        work = work[:mx]
    if os.path.exists(LOG):
        tot, n, _ = spent()
        est = tot + len(work) * 0.0015
        if est > BUDGET:
            print(f'would pass the budget (${est:.2f} > ${BUDGET})'); return
    print(f'{len(work)} takes', flush=True)
    secs = 0
    with cf.ThreadPoolExecutor(6) as ex:
        for i, (n, t, r, d) in enumerate(ex.map(lambda w: one(*w), work)):
            secs += d
            print(f'[{i + 1}/{len(work)}] {n}_{t}: {r}', flush=True)
    print(f'{secs:.1f}s of audio', flush=True)


if __name__ == '__main__':
    main()
