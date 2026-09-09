import halftone

def halftone(filename):
    h = halftone.Halftone(filename)
    h.make()

def main():
    filePath = input("File path: ")
    halftone(filePath)

if __name__ == "__main__":
    main()

