import struct, sys
def rd(f):
    d=open(f,'rb').read(); p=[0]
    def u8():  v=d[p[0]]; p[0]+=1; return v
    def u16(): v=struct.unpack_from('<H',d,p[0])[0]; p[0]+=2; return v
    def i16(): v=struct.unpack_from('<h',d,p[0])[0]; p[0]+=2; return v
    def u32(): v=struct.unpack_from('<I',d,p[0])[0]; p[0]+=4; return v
    def s():
        n=u8(); v=d[p[0]:p[0]+n].decode('latin1'); p[0]+=n; return v
    sig=u32(); frameCount=u32()
    sheets=[s() for _ in range(u8())]
    hitboxes=[s() for _ in range(u8())]
    animCount=u16()
    anims=[]
    for a in range(animCount):
        name=s(); fc=u16(); spd=u16(); loop=u8(); rot=u8()
        frames=[]
        for _ in range(fc):
            sh=u8(); dur=u16(); uni=u16()
            x=i16(); y=i16(); w=i16(); h=i16(); px=i16(); py=i16()
            p[0]+=len(hitboxes)*8
            frames.append((sh,x,y,w,h,px,py))
        anims.append((a,name,frames))
    return sheets,hitboxes,anims

def gifdim(f):
    d=open(f,'rb').read(10)
    return struct.unpack_from('<HH',d,6)

import os
M="/sdcard/Download/SonicMania/SonicMania/mods/Sonic Mania Addendum/Data/Sprites/Title"
for binf in ["Logo.bin","PlusLogo.bin"]:
    path=os.path.join(M,binf)
    sheets,hb,anims=rd(path)
    print(f"\n===== {binf} =====")
    print("sheets:", sheets)
    for sh in sheets:
        g=os.path.join(M, sh.strip(chr(0)).split("/")[-1])
        if os.path.exists(g):
            print(f"   {sh} -> {gifdim(g)} (w,h)")
        else:
            print(f"   {sh} -> MISSING on disk")
    for a,name,frames in anims:
        print(f"  [{a}] {name!r}  frames={len(frames)}")
