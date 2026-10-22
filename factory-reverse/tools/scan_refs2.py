import re,sys
from pathlib import Path
def imm(s):
 s=s.strip().split('(')[0]
 try:return int(s,0)
 except:return None
DEST3={'add','sub','and','or','xor','sll','srl','sra','slt','sltu','mul','div','rem','addw','subw','sllw','srlw','sraw','mulh','mulhu','divu','remu'}
LOAD={'lb','lbu','lh','lhu','lw','lwu','ld'}
def load(path):
 out=[]
 for line in Path(path).read_text(errors='replace').splitlines():
  m=re.match(r'ram:([0-9a-f]+)\s+(\S+)\s*(.*)',line.strip())
  if m:out.append((int(m.group(1),16),m.group(2),m.group(3)))
 return out
def scan(path,targets):
 ins=load(path); regs={}; hits={t:[] for t in targets}; tset=set(targets)
 for pc,op,args in ins:
  parts=[x.strip() for x in args.split(',')] if args else []
  rd=None
  if op=='lui' and len(parts)==2:
   v=imm(parts[1]); regs[parts[0]]=((v<<12)&0xffffffff) if v is not None else None; rd=parts[0]
  elif op=='auipc' and len(parts)==2:
   v=imm(parts[1]); regs[parts[0]]=((pc+(v<<12))&0xffffffff) if v is not None else None; rd=parts[0]
  elif op in ('addi','c.addi','andi','ori','xori','slli','srli','srai') and len(parts)>=3:
   a=regs.get(parts[1]); v=imm(parts[2]); regs[parts[0]]=((a+v)&0xffffffff) if a is not None and v is not None else None; rd=parts[0]
  elif op=='c.addi' and len(parts)==2:
   a=regs.get(parts[0]); v=imm(parts[1]); regs[parts[0]]=((a+v)&0xffffffff) if a is not None and v is not None else None; rd=parts[0]
  elif op in DEST3 and len(parts)==3:
   a=regs.get(parts[1]); b=regs.get(parts[2]); regs[parts[0]]=((a+b)&0xffffffff) if a is not None and b is not None else None; rd=parts[0]
  elif op in LOAD and len(parts)>=2:
   regs[parts[0]]=None; rd=parts[0]
  elif op in ('mv','c.mv') and len(parts)==2:
   regs[parts[0]]=regs.get(parts[1]); rd=parts[0]
  elif op in ('li','c.li') and len(parts)==2:
   regs[parts[0]]=imm(parts[1]); rd=parts[0]
  elif op in ('jal','jalr') and parts:
   regs[parts[0]]=None; rd=parts[0]
  # stores/branches no dest
  if rd and regs.get(rd) in tset:hits[regs[rd]].append((pc,op,args,rd))
 for t in targets:
  print(f'TARGET {t:#x}')
  for h in hits[t]:print('  %x %s %s [%s]'%h)
  if not hits[t]:print('  NONE')
scan(sys.argv[1],[int(x,0) for x in sys.argv[2:]])
