import struct
def read_spr(path):
    d=open(path,'rb').read(); p=[0]
    def u8():  v=d[p[0]]; p[0]+=1; return v
    def u16(): v=struct.unpack_from('<H',d,p[0])[0]; p[0]+=2; return v
    def i16(): v=struct.unpack_from('<h',d,p[0])[0]; p[0]+=2; return v
    def u32(): v=struct.unpack_from('<I',d,p[0])[0]; p[0]+=4; return v
    def s():   n=u8(); v=d[p[0]:p[0]+n]; p[0]+=n; return v
    sig=u32(); total=u32()
    sheets=[s() for _ in range(u8())]
    hitboxes=[s() for _ in range(u8())]
    animCount=u16(); anims=[]
    for _ in range(animCount):
        name=s(); fc=u16(); spd=u16(); loop=u8(); rot=u8(); frames=[]
        for _ in range(fc):
            sh=u8(); dur=u16(); uni=u16()
            x=i16(); y=i16(); ww=i16(); hh=i16(); pxv=i16(); pyv=i16()
            hb=[tuple(i16() for _ in range(4)) for _ in range(len(hitboxes))]
            frames.append(dict(sheet=sh,dur=dur,uni=uni,x=x,y=y,w=ww,h=hh,px=pxv,py=pyv,hb=hb))
        anims.append(dict(name=name,spd=spd,loop=loop,rot=rot,frames=frames))
    assert p[0]==len(d), f"trailing {len(d)-p[0]} bytes"
    return dict(sig=sig,sheets=sheets,hitboxes=hitboxes,anims=anims)

def write_spr(spr,path):
    o=bytearray()
    def u8(v): o.append(v&0xFF)
    def u16(v): o.extend(struct.pack('<H',v&0xFFFF))
    def i16(v): o.extend(struct.pack('<h',v))
    def u32(v): o.extend(struct.pack('<I',v))
    def s(b): u8(len(b)); o.extend(b)
    u32(spr['sig'])
    u32(sum(len(a['frames']) for a in spr['anims']))
    u8(len(spr['sheets'])); [s(x) for x in spr['sheets']]
    u8(len(spr['hitboxes'])); [s(x) for x in spr['hitboxes']]
    u16(len(spr['anims']))
    for a in spr['anims']:
        s(a['name']); u16(len(a['frames'])); u16(a['spd']); u8(a['loop']); u8(a['rot'])
        for f in a['frames']:
            u8(f['sheet']); u16(f['dur']); u16(f['uni'])
            i16(f['x']); i16(f['y']); i16(f['w']); i16(f['h']); i16(f['px']); i16(f['py'])
            for hb in f['hb']:
                for v in hb: i16(v)
    open(path,'wb').write(bytes(o))
