#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试 gmssl 库的问题"""

from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT

# 测试1: 使用16字节的key
key = b'0123456789abcdef'  # 16 bytes
plaintext = b'hello'

print(f"Key: {key}")
print(f"Key length: {len(key)}")
print(f"Plaintext: {plaintext}")
print(f"Plaintext length: {len(plaintext)}")

# 测试不同的padding_mode
for padding_mode in [0, 1, 2, 3, 4]:
    print(f"\n--- Testing padding_mode={padding_mode} ---")
    try:
        sm4 = CryptSM4(padding_mode=padding_mode)
        sm4.set_key(key, SM4_ENCRYPT)

        if padding_mode == 0:
            # NoPadding 需要数据是16字节的倍数
            padded = plaintext + b'\x0b' * 11  # 手动填充到16字节
            encrypted = sm4.crypt_ecb(padded)
        else:
            encrypted = sm4.crypt_ecb(plaintext)

        print(f"Encrypted (hex): {encrypted.hex()}")
        print(f"Success!")
    except Exception as e:
        print(f"Failed with error: {e}")
        import traceback
        traceback.print_exc()
