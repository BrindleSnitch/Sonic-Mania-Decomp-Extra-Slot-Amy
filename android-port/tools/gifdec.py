import struct
def decode(path):
    d=open(path,'rb').read()
    n=2<<(d[10]&7); has_gct=bool(d[10]&0x80)
    pal=[tuple(d[13+i*3:16+i*3]) for i in range(n)] if has_gct else []
    p=13+(n*3 if has_gct else 0)
    while p<len(d):
        b=d[p]
        if b==0x21:            # extension
            p+=2
            while d[p]!=0: p+=1+d[p]
            p+=1
        elif b==0x2C:          # image descriptor
            left,top,w,h=struct.unpack_from('<HHHH',d,p+1)
            f=d[p+9]; p+=10
            if f&0x80: p+= (2<<(f&7))*3
            mcs=d[p]; p+=1
            data=bytearray()
            while d[p]!=0:
                ln=d[p]; data+=d[p+1:p+1+ln]; p+=1+ln
            return w,h,lzw(bytes(data),mcs),pal
        else: p+=1
    raise ValueError("no image")

def lzw(data,mcs):
    clear=1<<mcs; eoi=clear+1
    size=mcs+1; mask=(1<<size)-1
    dic=[bytes([i]) for i in range(clear)]+[b'',b'']
    out=bytearray(); prev=None
    bitpos=0; total=len(data)*8
    while bitpos+size<=total:
        byi=bitpos>>3; sh=bitpos&7
        chunk=int.from_bytes(data[byi:byi+3].ljust(3,b'\0'),'little')
        code=(chunk>>sh)&mask
        bitpos+=size
        if code==clear:
            dic=dic[:clear+2]; size=mcs+1; mask=(1<<size)-1; prev=None; continue
        if code==eoi: break
        if code<len(dic): entry=dic[code]
        elif prev is not None: entry=prev+prev[:1]
        else: break
        out+=entry
        if prev is not None:
            dic.append(prev+entry[:1])
            if len(dic)==(1<<size) and size<12:
                size+=1; mask=(1<<size)-1
        prev=entry
    return bytes(out)
