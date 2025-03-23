#!/usr/bin/env python3

import numpy as np
from colorama import Fore

def slideup1(xs: np.ndarray) -> np.ndarray:
    # [xs[1], xs[2], ..., 0]
    return np.concatenate((xs[1:], [0]))

def slidedown1(xs: np.ndarray, msb: int) -> np.ndarray:
    # [msb, xs[1], xs[2], ..., xs[n-1]]
    return np.concatenate(([msb], xs[:-1]))

class MMM:
    def __init__(self, M: int, n: int, R_log2: int, r_log2: int):
        assert M % 2 != 0, f'{M=} should be odd'
        r = 1 << r_log2
        R = 1 << R_log2
        assert r ** (n - 1) <= M < r ** n

        self.n = n
        self.M = M
        self.minus_M_inverse_mod_r = pow(-M, -1, mod=r)
        print(f'{self.minus_M_inverse_mod_r=:0x}')

        self.R = R
        self.R_log2 = R_log2
        self.r = r
        self.r_log2 = r_log2

    def decompose_base_r(self, x: int) -> np.ndarray:
        return np.asarray([(x >> ((self.n - 1 - i) * self.r_log2)) % self.r for i in range(self.n)])

    def compose_base_r(self, xs: np.ndarray, msb: int = 0) -> int:
        return sum(xi * (self.r ** (self.n - 1 - i)) for i, xi in enumerate(xs)) + (msb << (len(xs) * self.r_log2))

    def mmm(self, X: int, Y: int) -> int:
        assert 0 <= X < self.M and 0 <= Y < self.M
        ys = self.decompose_base_r(Y)

        print(ys)
        Z = 0
        for i in range(self.n):
            print(f'\n{i=}, yi={int(ys[i]):01x}')
            Z = Z + int(ys[self.n - 1 - i]) * X

            print(f'z1={Z:04x}')
            q = (Z * self.minus_M_inverse_mod_r) % self.r
            print(f'{q=:0x}')
            Z = Z + q * self.M
            assert Z % self.r == 0
            print(f'z2={Z:04x}')
            Z = Z // self.r
            print(f'z3={Z:04x}')

        if Z >= self.M:
            Z -= self.M
        return Z

    def mmm_v1(self, X: int, Y: int) -> int:
        assert 0 <= X < self.M and 0 <= Y < self.M

        ys = self.decompose_base_r(Y)
        xs = self.decompose_base_r(X)
        ms = self.decompose_base_r(self.M)

        zs = np.repeat(0, self.n)
        zs_msb = 0

        def propagate():
            nonlocal zs, zs_msb
            print(f'zs           ={zs_msb:0x}, {zs}')
            zs_msb += zs[0] // self.r
            zs = (zs % self.r) + slideup1(zs // self.r)
            print(f'zs_propagated={zs_msb:0x}, {zs}')
            assert all(zs <= 2 * self.r - 2)

        for i in range(self.n):
            yi = ys[self.n - 1 - i]
            print(f'\n{i=}, yi={int(yi):0x}')
            zs += xs * yi
            propagate()

            q = (zs[-1] * self.minus_M_inverse_mod_r) % self.r
            print(f'q={int(q):0x}')
            zs += q * ms
            propagate()
            zs = slidedown1(zs, zs_msb % self.r)
            zs_msb = zs_msb // self.r
            print(f'zs           ={zs_msb:0x}, {zs}')

        print(f'\nfinal')
        propagate()
        return self.compose_base_r(zs, zs_msb)

def main():
    np.set_printoptions(formatter={'int': lambda x: hex(x)[2:]})
    M = 0xc125_7b23_e38a_13a3
    X = 0xb13e_117a_2de9_3bd1
    Y = 0x383a_338e_3f19_a39b
    R_log2 = 64
    r_log2 = 16

    mmm = MMM(M=M, n=R_log2 // r_log2, R_log2=R_log2, r_log2=r_log2)
    print(Fore.YELLOW + 'begin mmm' + Fore.RESET)
    res = mmm.mmm(X, Y)

    print(Fore.YELLOW + '\nbegin mmm v1' + Fore.RESET)
    res1 = mmm.mmm_v1(X, Y)

    expected = (X * Y * pow(1 << R_log2, -1, mod=M)) % M
    print(f'{res=:x}, {res1=:x}, {expected=:x}')
    assert(res == expected)
    assert(res1 == expected)

if __name__ == '__main__':
    main()
