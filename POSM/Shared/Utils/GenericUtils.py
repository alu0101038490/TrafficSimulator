def nextString(s):
    strip_zs = s.rstrip('z')
    if strip_zs:
        return strip_zs[:-1] + chr(ord(strip_zs[-1]) + 1) + 'a' * (len(s) - len(strip_zs))
    else:
        return 'a' * (len(s) + 1)
