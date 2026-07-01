import sys,os,subprocess


if __name__ == "__main__":
    HEXTITLE = f"{" "*10}00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F  Decoded Text\n"
    with open(sys.argv[1],'rb') as S,open("HEXEDITOR.txt","w") as D:
        D.write(HEXTITLE)
        address = 0x00000000
        chunk = []
        align   = 1
        D.write(f"{address:08X}  ")
        for byte in S.read():  
            D.write(f"{byte:02X} ")
            chunk.append(chr(byte) if 32 <= byte <= 126 else '.')
            align +=1
            if align % 17 == 0:
                for asci in chunk:
                    D.write(f" {asci} ")
                D.write('\n')
                chunk = []
                align = 1
                address += 0x10
                D.write(f"{address:08X}  ")
        if len(chunk) > 0:
          padding = (48 - (len(chunk)*2+(len(chunk)-1)))
          D.write(" "*padding)
          for i in chunk:
              D.write(f"{i}  ")
    vs = r"C:\Users\Compustore\AppData\Local\Programs\Microsoft VS Code\code"              
    subprocess.run([vs,"HEXEDITOR.txt"])
                

            

            
