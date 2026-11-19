"""OpenRouter text-to-audio for the Falcos SFX pass. Key from ~/.highpeaks/openrouter-key.txt (never printed)."""
import json, os, time, urllib.request, urllib.error

KEY_FILE = os.path.expanduser('~/.highpeaks/openrouter-key.txt')
BASE = 'https://openrouter.ai/api/v1'
MODEL = 'bytedance-seed/seed-audio-1-0'


def _key():
    return open(KEY_FILE, encoding='utf-8').read().strip()


def _req(path, body=None, timeout=240):
    data = None if body is None else json.dumps(body).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=data, method='POST' if body is not None else 'GET')
    req.add_header('Authorization', 'Bearer ' + _key())
    req.add_header('X-Title', 'Falcos sfx')
    if body is not None:
        req.add_header('Content-Type', 'application/json')
    return urllib.request.urlopen(req, timeout=timeout)


def key_usage():
    """Dollars used so far on this key (OpenRouter /key)."""
    with _req('/key') as r:
        return float(json.load(r)['data']['usage'])


def speech(text, retries=3):
    """Returns (pcm_bytes, headers dict). int16 LE stereo 24 kHz."""
    body = {'model': MODEL, 'input': text, 'response_format': 'pcm'}
    last = None
    for a in range(retries):
        try:
            with _req('/audio/speech', body) as r:
                return r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            last = f'HTTP {e.code}: {e.read()[:300]!r}'
            if e.code in (400, 401, 402, 403):
                break
        except Exception as e:
            last = repr(e)
        time.sleep(3 + 4 * a)
    raise RuntimeError(last)
