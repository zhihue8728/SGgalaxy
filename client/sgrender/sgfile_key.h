/* AES-128 key of the encrypted game files (.dat, SGHud.pak; tools/sgcrypt_files.py).  It has to be inside the
   client to decrypt - it only keeps the files from being opened by hand. */
static const unsigned char SGFILE_KEY[16] = { 0x26, 0x0b, 0x76, 0x17, 0xa7, 0xd1, 0x8d, 0xa2, 0x39, 0xc1, 0x0e, 0x2b, 0x83, 0x58, 0x19, 0x3e };
