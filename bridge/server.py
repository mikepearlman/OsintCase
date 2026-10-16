#!/usr/bin/env python3
"""Local OsintCase bridge. Keeps phone data and credentials outside the fork."""
import argparse, datetime, hashlib, importlib.util, json, mimetypes, os, secrets, sys, threading, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT.parent / 'crime-stoppers'
spec = importlib.util.spec_from_file_location('phone_case', CASE / 'server.py')
phone = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phone)
STORE = CASE / 'data' / 'osintcase'
TOKEN = secrets.token_hex(24)
SAVE_LOCK = threading.Lock()

def make_case(ids=None, full=False):
    """Export native case objects with stable IDs and explicit metadata links."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with phone.connect() as c:
        if full:
            chosen = {r[0] for r in c.execute('SELECT id FROM records')}
        elif ids is not None:
            chosen = set(ids)
        else:
            chosen = {r[0] for r in c.execute('SELECT audio_id FROM audio_leads UNION SELECT message_id FROM audio_leads')}
        leads = [dict(r) for r in c.execute('SELECT * FROM audio_leads')]
        matches = [dict(r) for r in c.execute('SELECT * FROM audio_call_matches WHERE accepted=1')]
        for link in matches:
            if link['audio_id'] in chosen: chosen.add(link['call_id'])
        if not chosen: rows = []
        else:
            marks = ','.join('?' for _ in chosen)
            rows = [dict(r) for r in c.execute('SELECT r.*,s.path,s.name filename,s.sha256,s.phone_path,s.bytes FROM records r JOIN sources s ON s.id=r.source_id WHERE r.id IN ('+marks+') ORDER BY r.person,r.at,r.id', sorted(chosen))]
        tags = {}
        for r in c.execute('SELECT * FROM record_tags'):
            if r['record_id'] in chosen: tags.setdefault(r['record_id'], []).append(dict(r))
        manual = [dict(r) for r in c.execute('SELECT * FROM links')]
    out = dict(schemaVersion=2,id='phone-evidence',name='Phone evidence',createdAt=now,updatedAt=now,classification='ozel',caseInfo={'caseNumber':'PHONE-LOCAL','status':'acik','priority':'orta','summary':'Phone source records. Contact labels identify addressing metadata, not verified speakers. Text-led audio links are review suggestions.'},target={'name':'Phone archive','notes':'Original phone files remain unchanged.'},identifiers=[],connections=[],events=[],evidence=[],locations=[],pinLinks=[],auditLog=[],mapDisplay={})
    people = {}
    def node(id, type, fields, notes='', **extra):
        i = len(out['identifiers'])
        n = dict(id=id,type=type,fields=fields,notes=notes,position={'x':(i%5)*350,'y':(i//5)*210},photos=[],createdAt=now,updatedAt=now,**extra)
        out['identifiers'].append(n)
    def edge(id,a,b,label,note,confidence='muhtemel'):
        out['connections'].append(dict(id=id,source=a,target=b,label=label,note=note,confidence=confidence))
    for r in rows:
        rid = r['id']; nid = f'record-{rid}'; person = r['person'].strip()
        if person and person not in people:
            pid = 'contact-'+hashlib.sha256(person.encode()).hexdigest()[:20];people[person]=pid
            node(pid,'custom',{'title':person,'value':'Source contact label'},'Addressing/filename label only. Speaker identity remains unverified.')
        text = r['body'] or '(No transcript text)' if r['kind']=='audio' else r['body']
        tagtext = ', '.join(t['tag'] for t in tags.get(rid,[]))
        node(nid,'custom',{'title':f"{r['kind'].upper()} · {r['title']}",'value':r['at'],'url':f'/source/{rid}'},f"Record {rid}\n{r['at']}\nTags: {tagtext}\n\n{text}",sourceRecordId=rid)
        if person: edge(f'contact-record-{rid}',people[person],nid,'Addressed contact','Source contact/filename metadata only. Not verified speaker identity.','kesin')
        ev=f'evidence-{rid}'
        out['evidence'].append(dict(id=ev,number=f'R-{rid}',title=r['title'],description=f"{r['kind']} · {r['at']}\nTags: {tagtext}\n\n{text}",fileName=r['filename'],mimeType=mimetypes.guess_type(r['path'])[0] or 'text/plain',size=r['bytes'] or 0,sha256=r['sha256'] or '',dataUrl=None,source=f"/source/{rid}\nOriginal: {r['phone_path'] or r['path']}\nSource row: {r['source_key']}",acquiredAt='',identifierIds=[nid]+([people[person]] if person else []),pinIds=[],addedAt=now,addedBy='Phone archive bridge',custody=[],verifications=[],sourceRecordId=rid))
        if r['at']:
            out['events'].append(dict(id=f'event-{rid}',date=r['at'][:10],time=r['at'][11:19],title=r['title'],description=f"Source timestamp (UTC): {r['at']}\n{r['kind']} record {rid}. This records communication, not a proven real-world event.",category='olay',identifierIds=[nid],pinIds=[],evidenceIds=[ev],createdAt=now,updatedAt=now))
    visible={r['id'] for r in rows}
    for l in leads:
        if {l['audio_id'],l['message_id']} <= visible:
            edge(f"lead-{l['audio_id']}-{l['message_id']}",f"record-{l['message_id']}",f"record-{l['audio_id']}",'Text-led review',f"Jev suggestion: {l['decision']}; probability {l['probability']}; {l['distance_hours']} hours apart. Same addressed contact and time proximity do not prove shared meaning.")
    for m in matches:
        if {m['audio_id'],m['call_id']} <= visible:
            edge(f"match-{m['audio_id']}-{m['call_id']}",f"record-{m['audio_id']}",f"record-{m['call_id']}",'Matched call metadata',m['basis'],'kesin')
    for l in manual:
        if {l['a'],l['b']} <= visible: edge(f"manual-{l['id']}",f"record-{l['a']}",f"record-{l['b']}",'Analyst link',l['reason'])
    return out

class Handler(phone.Handler):
    def backend(self):
        headers={}
        if self.headers.get('Range'): headers['Range']=self.headers['Range']
        data=None
        if self.command=='POST':
            self.check(True)
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=2*1024*1024: raise ValueError('Invalid request size.')
            data=self.rfile.read(n)
            with urllib.request.urlopen('http://127.0.0.1:8765/api/bootstrap',timeout=10) as r: session=json.load(r)['token']
            headers.update({'X-Case-Token':session,'Content-Type':'application/json'})
        req=urllib.request.Request('http://127.0.0.1:8765'+self.path,data=data,headers=headers,method=self.command)
        try: res=urllib.request.urlopen(req,timeout=120)
        except urllib.error.HTTPError as e: res=e
        with res:
            self.send_response(res.status)
            for k in ['Content-Type','Content-Length','Content-Range','Accept-Ranges']:
                if res.headers.get(k): self.send_header(k,res.headers[k])
            self.send_header('Cache-Control','no-store');self.end_headers()
            while chunk:=res.read(65536):self.wfile.write(chunk)
    def do_GET(self):
        try:
            self.check();u=urlparse(self.path);p=u.path;q=parse_qs(u.query)
            if p=='/app.config.json':return self.reply({'map':{'provider':'osm'}})
            if p=='/bridge/status':return self.reply({'token':TOKEN,'backend':phone.stats(),'models':['typesafe/jev-1.14','deepgram/nova-3']})
            if p=='/bridge/case':
                ids=[int(i) for i in q['ids'][0].split(',')] if q.get('ids') else None
                return self.reply(make_case(ids,full=q.get('all')==['1']))
            if p=='/bridge/saved':
                file=STORE/'working.case.json'
                return self.reply(json.loads(file.read_text()) if file.exists() else make_case())
            if p.startswith('/api/'):return self.backend()
            if p.startswith('/source/'):
                rid=int(p.rsplit('/',1)[1]);r=phone.detail(rid)
                import html
                esc=lambda s:html.escape(str(s))
                body=f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Record {rid}</title><style>body{{font:16px system-ui;max-width:850px;margin:32px auto;padding:16px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}audio{{width:100%}}a{{color:#165dba}}</style><a href="/">Back to case board</a><h1>{esc(r["title"])}</h1><p>{esc(r["kind"])} · {esc(r["at"])} · Record {rid}</p>'
                if r['kind']=='audio':body+=f'<audio controls preload="metadata" src="/api/media/{rid}"></audio>'
                body+=f'<pre>{esc(r["body"])}</pre><h2>Source</h2><pre>{esc(r["phone_path"] or r["path"])}\n{esc(r["source_key"])}\nSHA-256: {esc(r["sha256"])}</pre><h2>Transcript passages</h2>'
                for s in r['metadata'].get('segments',[]):body+=f'<p>{esc(s.get("start",0))}–{esc(s.get("end",0))} seconds: {esc(s.get("text",""))}</p>'
                data=body.encode();self.send_response(200);self.headers_out('text/html; charset=utf-8',len(data));self.end_headers();self.wfile.write(data);return
            path=(ROOT/'dist'/unquote(p).lstrip('/')).resolve()
            if not path.is_relative_to((ROOT/'dist').resolve()):raise ValueError('Invalid file path.')
            if not path.is_file():path=ROOT/'dist'/'index.html'
            return self.send_file(path)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:self.reply({'error':str(e)[:500]},400)
    def check(self,mutation=False):
        super().check(False)
        if mutation and self.headers.get('X-Case-Token')!=TOKEN:raise ValueError('Reload the case board.')
    def do_POST(self):
        try:
            self.check(True)
            if self.path.startswith('/api/'):
                if self.path!='/api/process':raise ValueError('Unsupported bridge action.')
                return self.backend()
            if self.path!='/bridge/save':raise ValueError('Unknown action.')
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=50*1024*1024:raise ValueError('Invalid case size.')
            obj=json.loads(self.rfile.read(n))
            if obj.get('id')!='phone-evidence' or not isinstance(obj.get('identifiers'),list):raise ValueError('Invalid phone case.')
            STORE.mkdir(parents=True,exist_ok=True)
            with SAVE_LOCK:
                dest=STORE/'working.case.json';tmp=STORE/'working.tmp'
                if dest.exists(): (STORE/'previous.case.json').write_bytes(dest.read_bytes())
                tmp.write_text(json.dumps(obj,ensure_ascii=False));tmp.chmod(0o600);os.replace(tmp,dest)
            self.reply({'saved':True})
        except Exception as e:self.reply({'error':str(e)[:500]},400)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8770);parser.add_argument('--export-all',action='store_true');args=parser.parse_args()
    if args.export_all:
        STORE.mkdir(parents=True,exist_ok=True);dest=STORE/'archive.case.json';dest.write_text(json.dumps(make_case(full=True),ensure_ascii=False));dest.chmod(0o600);print(dest)
    else:
        print(f'OsintCase: http://127.0.0.1:{args.port}',flush=True)
        ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
