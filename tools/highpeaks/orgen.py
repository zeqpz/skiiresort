"""Falcos art generator: OpenRouter Images API.

  python3 tools/highpeaks/orgen.py <job.json>        one job: {"name", "prompt", "aspect_ratio", "background", "refs":[paths], "model"}

The key is read from ~/.highpeaks/openrouter-key.txt and never printed. Every image's usage.cost is
appended to art/highpeaks/cost_log.jsonl. Raw output lands in art/highpeaks/raw/<name>.png (versioned
<name>.v2.png ... if the name already exists).
"""
import base64, io, json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# the owner's game-art key (owner, 2026-11-19: "use gamedevkey in documents"); the Mac's file is the fallback
KEY_FILE = os.path.join(os.path.expanduser('~'), 'Documents', 'gamdevkey.txt')
if not os.path.exists(KEY_FILE):
    KEY_FILE = os.path.expanduser('~/.highpeaks/openrouter-key.txt')
BASE = 'https://openrouter.ai/api/v1'
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
LOG = os.path.join(ROOT, 'art', 'highpeaks', 'cost_log.jsonl')
MODEL = 'openai/gpt-image-2.6-sunburst'


def _key():
    return open(KEY_FILE, encoding='utf-8').read().strip()


def call(path, body=None, timeout=900):
    req = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + _key(), 'Content-Type': 'application/json',
                 'User-Agent': 'highpeaks-art/1.0', 'X-Title': 'High Peaks art'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:600]}')


def data_url(path):
    from PIL import Image
    im = Image.open(path).convert('RGBA')
    im.thumbnail((2048, 2048), Image.LANCZOS)   # big references break the upload (broken pipe)
    buf = io.BytesIO(); im.save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def out_path(name):
    os.makedirs(RAW, exist_ok=True)
    p = os.path.join(RAW, name + '.png'); v = 2
    while os.path.exists(p):
        p = os.path.join(RAW, f'{name}.v{v}.png'); v += 1
    return p


def generate(job):
    body = dict(model=job.get('model', MODEL), prompt=job['prompt'], quality=job.get('quality', 'high'),
                output_format='png', aspect_ratio=job.get('aspect_ratio', '1:1'), n=1)
    if job.get('background'):
        body['background'] = job['background']
    for k in ('size', 'resolution'):
        if job.get(k):
            body[k] = job[k]
    if job.get('refs'):
        body['input_references'] = [{'type': 'image_url', 'image_url': {'url': data_url(p)}} for p in job['refs']]
    t0 = time.time(); err = None
    for attempt in range(6):
        try:
            r = call('/images', body)
            break
        except Exception as e:
            err = str(e)
            # 402 in_flight_budget_exhausted: other requests (another job, another session) hold the credit budget
            # for now - wait for them to settle and go again
            busy = 'in_flight_budget_exhausted' in err
            if attempt == 5 or not (busy or any(s in err for s in ('HTTP 502', 'HTTP 503', 'HTTP 429', 'timed out', 'Broken pipe', 'Connection reset', 'SSL', 'EOF occurred'))):
                rec = dict(name=job['name'], error=err[:500], secs=round(time.time() - t0, 1))
                _log(rec); return rec
            time.sleep(30 if busy else 10)
    out = out_path(job['name'])
    open(out, 'wb').write(base64.b64decode(r['data'][0]['b64_json']))
    from PIL import Image
    im = Image.open(out)
    rec = dict(name=job['name'], file=os.path.relpath(out, ROOT), size=im.size, mode=im.mode,
               cost=(r.get('usage') or {}).get('cost'), model=body['model'], secs=round(time.time() - t0, 1),
               t=time.strftime('%Y-%m-%d %H:%M:%S'))
    _log(rec); return rec


def _log(rec):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a') as f:
        f.write(json.dumps(rec) + '\n')


if __name__ == '__main__':
    jobs = json.load(open(sys.argv[1]))
    if isinstance(jobs, dict):
        jobs = [jobs]
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max_workers=int(os.environ.get('FALCOS_PAR', '4'))) as ex:
        for rec in ex.map(generate, jobs):
            print(json.dumps(rec), flush=True)
    tot = 0.0
    for line in open(LOG):
        tot += json.loads(line).get('cost') or 0
    print(f'total spent so far: ${tot:.3f}')
