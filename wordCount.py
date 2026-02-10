#!/opt/homebrew/bin/python3
import os
import re
import sys

WORD_RE = re.compile(r"[A-Za-z0-9]+")

def count_words_posix(in_path: str) -> dict[str, int]:
    #open input file read only using POSIX syscall
    fd = os.open(in_path, os.O_RDONLY)
    counts: dict[str, int] = {}

    try:
         #if a chunk ends in the middle of a word we store that partial word here
        tail = ""
        while True:           
            #read up to 8192 bytes from the file descriptor
            chunk = os.read(fd, 8192)
            #empty bytes means end of file
            if not chunk:
                break
            
            #convert bytes to text and prepend any leftover partial word from last read
            text = tail + chunk.decode("utf-8", errors="ignore")
            lower = text.lower()

            #if the chunk ends with a letter/digit, it may end mid word
            if lower and lower[-1].isalnum():
                #capture the trailing run of alphanumeric chars at the end of the partial word
                m = re.search(r"[A-Za-z0-9]+$", lower)
                tail = m.group(0) if m else ""
                
                #remove the tail from 'lower' so we don't count an incomplete word yet
                if tail:
                    lower = lower[:-len(tail)]
            else:
                #if ends on punctuation/whitespace there is no partial word
                tail = ""
            
            #count all complete words found in this chunk
            for w in WORD_RE.findall(lower):
                counts[w] = counts.get(w, 0) + 1

        #after reading the whole file if there's a leftover final word count it once
        if tail:
            counts[tail] = counts.get(tail, 0) + 1

    finally:
        os.close(fd)

    return counts

def write_results_posix(out_path: str, counts: dict[str, int]) -> None:
    #open output file for writing, create if missing, truncate if it exists overwrite
    fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

    try:
        #alphabetical sort by word kv[0]
        items = sorted(counts.items(), key=lambda kv: kv[0])
        
        buf = bytearray()
        FLUSH_LIMIT = 64 * 1024 

        for word, c in items:
            buf.extend(f"{word} {c}\n".encode("utf-8"))

            if len(buf) >= FLUSH_LIMIT:
                os.write(fd, buf)
                buf.clear

        if buf:
            os.write(fd, buf)

    finally:
        os.close(fd)

def main() -> int:
    #expect: scriptname inputfile outputfile 
    if len(sys.argv) != 3:
        msg = f"Usage: {sys.argv[0]} <input_file> <output_file>\n"
        os.write(2, msg.encode("utf-8"))
        return 2

    in_path, out_path = sys.argv[1], sys.argv[2]

    try:
        counts = count_words_posix(in_path)
        write_results_posix(out_path, counts)
    except OSError as e:
        #handles file not found, permission denied etc
        err = f"OS error: {e}\n"
        os.write(2, err.encode("utf-8"))
        return 1

    return 0

#program only runs when executed directly
if __name__ == "__main__":
    #runs main function and exits the program
    raise SystemExit(main())
