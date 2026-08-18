import struct
def lzw_encode(px, mcs=8):
    clear=1<<mcs; eoi=clear+1
    dic={bytes([i]):i for i in range(clear)}
    nxt=clear+2; size=mcs+1
    out=bytearray(); acc=0; nbits=0
    def emit(code):
        nonlocal acc,nbits
        acc |= code<<nbits; nbits+=size
        while nbits>=8:
            out.append(acc&0xFF); acc>>=8; nbits-=8
    emit(clear)
    cur=b''
    for ch in px:
        nc=cur+bytes([ch])
        if nc in dic: cur=nc; continue
        emit(dic[cur]); 
        if nxt < 4096:
            dic[nc]=nxt; nxt+=1
            if nxt> (1<<size) and size<12: size+=1
        else:
            emit(clear); dic={bytes([i]):i for i in range(clear)}; nxt=clear+2; size=mcs+1
        cur=bytes([ch])
    if cur: emit(dic[cur])
    emit(eoi)
    if nbits: out.append(acc&0xFF)
    return bytes(out)

def write_gif(path,w,h,pal,px):
    b=bytearray(b'GIF89a')
    b+=struct.pack('<HH',w,h)
    b+=bytes([0xF7,0,0])                     # GCT, 256 colors, 8bpp
    for i in range(256):
        c=pal[i] if i<len(pal) else (0,0,0)
        b+=bytes(c)
    b+=b'\x2C'+struct.pack('<HHHH',0,0,w,h)+b'\x00'   # image descriptor, no LCT
    b+=bytes([8])
    data=lzw_encode(px,8)
    for i in range(0,len(data),255):
        chunk=data[i:i+255]; b+=bytes([len(chunk)])+chunk
    b+=b'\x00\x3B'
    open(path,'wb').write(bytes(b))
