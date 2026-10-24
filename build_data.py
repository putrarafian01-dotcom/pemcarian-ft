#!/usr/bin/env python3
"""
Bangun data pencarian dari file Excel (SOAL | JAWABAN berpasangan di banyak kolom/sheet).
Pakai:  python3 tools/build_data.py all_latihan.xlsx
Hasil:  folder data/ (index.bin.gz, vocab.txt.gz, meta.json, b0.json.gz, b1.json.gz, ...)
Tidak butuh library tambahan (hanya Python 3.8+). Aman untuk file Excel ratusan MB.
"""
import sys, re, json, gzip, html, zipfile, struct, os, time, collections

SRC = sys.argv[1] if len(sys.argv) > 1 else 'all_latihan.xlsx'
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
BLOCK = 500            # jumlah soal per berkas blok
COMMON_RATIO = 0.06    # kata yang muncul di >6% soal dianggap umum (tidak diindeks)
t0 = time.time()
def log(*a): print('[%6.1fs]' % (time.time() - t0), *a, flush=True)

zf = zipfile.ZipFile(SRC)
names = zf.namelist()

# --- shared strings ---
raw = zf.read('xl/sharedStrings.xml')
sis = re.findall(rb'<si>(.*?)</si>', raw, re.S)
del raw
tre = re.compile(rb'<t[^>]*>(.*?)</t>', re.S)
S = [html.unescape(b''.join(tre.findall(x)).decode('utf-8', 'replace')) for x in sis]
del sis
log('shared strings:', len(S))

def col2n(c):
    n = 0
    for ch in c: n = n * 26 + ch - 64
    return n

cre = re.compile(rb'<c r="([A-Z]+)\d+"[^>]*?t="s"[^>]*?><v>(\d+)</v>')
pairs = set()
sheets = sorted([n for n in names if re.match(r'xl/worksheets/sheet\d+\.xml$', n)], key=lambda s: int(re.findall(r'\d+', s)[0]))
for sh in sheets:
    buf = b''
    with zf.open(sh) as f:
        while True:
            chunk = f.read(1 << 25)
            if not chunk: break
            buf += chunk
            k = buf.rfind(b'</row>')
            if k < 0: continue
            part, buf = buf[:k], buf[k + 6:]
            for row in part.split(b'</row>'):
                cells = {}
                for c, v in cre.findall(row):
                    cells[col2n(c)] = int(v)
                for c, v in cells.items():
                    if c % 2 == 1 and (c + 1) in cells:
                        pairs.add((v, cells[c + 1]))
    log(sh, 'pasangan unik:', len(pairs))

# --- bersihkan & kelompokkan ---
def clean(s): return re.sub(r'\s+', ' ', s.replace('\xa0', ' ')).strip()
def toks(s): return re.sub(r'[^a-z0-9]+', ' ', s.lower()).split()
def fnv(s, h):
    for ch in s.encode('ascii'):
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return h

groups = {}   # key -> [soal, {norm_jawaban: jawaban}, tokens]
for qi, ai in pairs:
    q, a = clean(S[qi]), clean(S[ai])
    if not q or not a or q.upper() == 'SOAL' or a.upper() == 'JAWABAN': continue
    if re.fullmatch(r'(?i)question\s*\d+', q) or re.fullmatch(r'(?i)right answer\s*\d+', a): continue
    t = toks(q)
    if not t: continue
    key = ' '.join(sorted(t))
    g = groups.get(key)
    if g is None:
        groups[key] = [q, {' '.join(toks(a)) or a: a}, t]
    else:
        g[1].setdefault(' '.join(toks(a)) or a, a)
del S, pairs
keys = sorted(groups)
N = len(keys)
log('soal unik:', N)

# --- vocab (kata tidak umum) ---
df = collections.Counter()
for k in keys:
    for t in set(groups[k][2]): df[t] += 1
limit = int(N * COMMON_RATIO)
vocab = sorted(t for t, c in df.items() if c <= limit)
vid = {t: i for i, t in enumerate(vocab)}
V = len(vocab)
log('kata diindeks:', V, '(umum dibuang:', len(df) - V, ')')

hashA = []; hashB = []; nidx = []
post = [[] for _ in range(V)]
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith('.gz') or f.endswith('.json'): os.remove(os.path.join(OUT, f))
blocks = []
for i, k in enumerate(keys):
    q, ans, t = groups[k]
    hashA.append(fnv(k, 0x811C9DC5)); hashB.append(fnv(k, 0x9747B28C))
    ids = set(vid[x] for x in t if x in vid)
    nidx.append(min(len(ids), 65535))
    for x in ids: post[x].append(i)
    blocks.append([q] + list(ans.values()))
    if len(blocks) == BLOCK or i == N - 1:
        n = i // BLOCK
        with gzip.GzipFile(os.path.join(OUT, 'b%d.json.gz' % n), 'wb', 9, mtime=0) as g:
            g.write(json.dumps(blocks, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        blocks = []
log('blok teks selesai:', (N + BLOCK - 1) // BLOCK)

def varint(n, out):
    while n >= 128:
        out.append((n & 127) | 128); n >>= 7
    out.append(n)

data = bytearray(); offs = [0]
for lst in post:
    prev = 0
    for x in lst:
        varint(x - prev, data); prev = x
    offs.append(len(data))
head = struct.pack('<5I', 0x43534F4C, N, V, BLOCK, len(data))
body = struct.pack('<%dI' % N, *hashA) + struct.pack('<%dI' % N, *hashB) + struct.pack('<%dH' % N, *nidx)
if N % 2: body += b'\0\0'
body += struct.pack('<%dI' % (V + 1), *offs) + bytes(data)
with gzip.GzipFile(os.path.join(OUT, 'index.bin.gz'), 'wb', 9, mtime=0) as g: g.write(head + body)
with gzip.GzipFile(os.path.join(OUT, 'vocab.txt.gz'), 'wb', 9, mtime=0) as g: g.write('\n'.join(vocab).encode('ascii'))
json.dump({'n': N, 'blockSize': BLOCK, 'vocab': V, 'source': os.path.basename(SRC),
           'built': time.strftime('%Y-%m-%d %H:%M')}, open(os.path.join(OUT, 'meta.json'), 'w'))
tot = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
log('SELESAI. Total ukuran data: %.1f MB' % (tot / 1e6))
