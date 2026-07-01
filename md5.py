#############################################

#[                   from                    ]

#https://en.wikipedia.org/wiki/MD5#:~:text=The%20MD5%20message%2Ddigest%20algorithm,in%201992%20as%20RFC%201321.

#############################################
import math,struct
def md5(message:str):
        
    M =message.encode()
    padded_M = M + b'\x80'
    while (len(padded_M) % 64) != 56:
        padded_M += b'\x00'

    orig_len_bits = len(M) * 8
    padded_M += struct.pack('<Q', orig_len_bits)  
    s = [7, 12, 17, 22,  7, 12, 17, 22,  7, 12, 17, 22,  7, 12, 17, 22,
         5,  9, 14, 20,  5,  9, 14, 20,  5,  9, 14, 20,  5,  9, 14, 20,
         4, 11, 16, 23,  4, 11, 16, 23,  4, 11, 16, 23,  4, 11, 16, 23,
         6, 10, 15, 21,  6, 10, 15, 21,  6, 10, 15, 21,  6, 10, 15, 21]
    k = []
    for i in range(64):
        k.append(math.floor(2**32 * abs(math.sin(i + 1))))
    a0 = 0x67452301   
    b0 = 0xefcdab89   
    c0 = 0x98badcfe   
    d0 = 0x10325476     
    def leftrotate(x, amount):
        x &= 0xFFFFFFFF
        return ((x << amount) | (x >> (32 - amount))) & 0xFFFFFFFF

    for chunk_offset in range(0, len(padded_M), 64):
        chunk = padded_M[chunk_offset:chunk_offset + 64]
        words = list(struct.unpack('<16I', chunk))
        A  = a0
        B  = b0
        C  = c0
        D  = d0
        for i in range(64):
            if 0 <= i <= 15:
                F = (B & C) | ((~ B) & D)
                g = i
            elif 16 <= i <= 31:
                F = (D & B) | ((~ D) & C)
                g = (5*i + 1) % 16
            elif 32 <= i <= 47:
                F = B ^ C ^ D
                g = (3*i + 5) % 16
            elif 48 <= i <= 63:
                F = C ^ (B | (~ D))
                g = (7*i) % 16
            F = (F + A + k[i] + words[g])&0xFFFFFFFF 
            A = D
            D = C
            C = B
            B = (B + leftrotate(F, s[i])) & 0xFFFFFFFF
        
        a0 = (a0 + A) & 0xFFFFFFFF
        b0 = (b0 + B) & 0xFFFFFFFF
        c0 = (c0 + C) & 0xFFFFFFFF
        d0 = (d0 + D) & 0xFFFFFFFF
    digest_bytes = struct.pack('<4I', a0, b0, c0, d0)
    print("MD5 Hash:", digest_bytes.hex())


if __name__ == "__main__":    
    message = "The quick brown fox jumps over the lazy dog"    
    md5(message)    