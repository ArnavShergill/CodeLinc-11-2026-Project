"""Check the current local key without ever printing or putting it in command arguments."""
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=root,**kwargs)
key=b''
env=root/'.env.local'
if env.exists():
    key=next((line.split('=',1)[1].strip().strip('"').strip("'").encode()
              for line in env.read_text().splitlines() if line.startswith('OLLAMA_API_KEY=')),b'')
tracked=[root/path.decode() for path in git('ls-files','-z').split(b'\0') if path]
working_matches=[str(path.relative_to(root)) for path in tracked if path.is_file() and key and key in path.read_bytes()]
public_matches=[]
if (root/'public').exists():
    public_matches=[str(path.relative_to(root)) for path in (root/'public').rglob('*') if path.is_file() and key and key in path.read_bytes()]
objects=[line.split()[0] for line in git('rev-list','--objects','--all').splitlines()]
meta=git('cat-file','--batch-check',input=b'\n'.join(objects)+b'\n')
blobs=[line.split()[0] for line in meta.splitlines() if len(line.split())==3 and line.split()[1]==b'blob']
stream=git('cat-file','--batch',input=b'\n'.join(blobs)+b'\n');position=0;history_matches=0
while position<len(stream):
    end=stream.index(b'\n',position);size=int(stream[position:end].split()[2]);data=stream[end+1:end+1+size]
    if key and key in data:history_matches+=1
    position=end+1+size+1
ignored=subprocess.run(['git','check-ignore','--no-index','-q','.env.local'],cwd=root).returncode==0
result={'envIgnored':ignored,'envTracked':bool(git('ls-files','.env.local').strip()),
        'keyAvailableForScan':bool(key),'currentKeyTrackedMatches':working_matches,
        'currentKeyPublicMatches':public_matches,'historyBlobsScanned':len(blobs),'currentKeyHistoryMatches':history_matches}
print(json.dumps(result,indent=2))
raise SystemExit(1 if not ignored or result['envTracked'] or working_matches or public_matches or history_matches else 0)
