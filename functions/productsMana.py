from hashids import Hashids

hashids = Hashids(salt="my-secret-salt", min_length=8)

# Encode number
def encode_id(value):
    if isinstance(value, int):
        return hashids.encode(value)
    elif isinstance(value, str):
        char_codes = [ord(c) for c in value]
        return hashids.encode(*char_codes)

# Decode
def decode_id(hash_str):
    decoded = hashids.decode(hash_str)
    if len(decoded) == 1:
        return decoded[0]  # number
    return "".join(chr(n) for n in decoded)  # string
