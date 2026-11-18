"""Recover source bytes from the SQLite archive for reproducibility.
Run from project root: python scripts/recover_input.py --out work/recovered_input
The reconstructed inner ZIP has original member bytes, not original ZIP metadata.
"""
import argparse,pathlib,sqlite3,zipfile
parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=True)
assert not (out/'group16_data.zip').exists(),'Choose a new output directory'
c=sqlite3.connect(root/'database/group16.sqlite')
with zipfile.ZipFile(out/'group16_data.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for name,b in c.execute('SELECT path,raw_bytes FROM source_file ORDER BY source_id'):
  path=pathlib.PurePosixPath(name)
  assert '..' not in path.parts and not path.is_absolute()
  if name.startswith('group16_data/'):z.writestr(name,b)
  else:
   dest=out/path;dest.parent.mkdir(parents=True,exist_ok=True)
   with dest.open('xb') as f:f.write(b)
print('Recovered original source bytes into',out)
