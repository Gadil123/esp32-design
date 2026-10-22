import re,sys
from pathlib import Path
def imm(s):
 s=s.strip().split('(')[0]
 try:return int(s,0)
 except:return None
def load(path):
 out=[]
 for line in Path(path).read_text(errors='replace').splitlines():
  m=re.match(r'ram:([0-9a-f]+)\s+(\S+)\s*(.*)',line.strip())
  if m:out.append((int(m.group(1),16),m.group(2),m.group(3)))
 return out
ins=load(sys.argv[1]); target=int(sys.argv[2],0)
for i in range(len(ins)-1):
 pc,op,args=ins[i]
 if op!='auipc':continue
 parts=[x.strip() for x in args.split(',')]
 if len(parts)!=2 or parts[0]!='ra':continue
 hi=imm(parts[1]); pc2,op2,args2=ins[i+1]
 if hi is None or op2!='jalr':continue
 p2=[x.strip() for x in args2.split(',')]
 if len(p2)!=3 or p2[0]!='ra' or p2[1]!='ra':continue
 lo=imm(p2[2])
 if lo is None:continue
 t=(pc+((hi<<12)&0xffffffff)+lo)&0xffffffff
 if t==target:print(f'{pc:#x} -> {target:#x}')
