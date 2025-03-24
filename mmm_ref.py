#!/usr/bin/env python3

import random
from typing import Callable
from argparse import ArgumentParser
import sys

import numpy as np
from loguru import logger

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

        self.n: int = n
        self.M: int = M
        self.minus_M_inverse_mod_r: int = pow(-M, -1, mod=r)
        logger.info(f'{self.minus_M_inverse_mod_r=:0x}')

        self.R: int = R
        self.R_log2: int = R_log2
        self.r: int = r
        self.r_log2: int = r_log2

    def decompose_base_r(self, x: int) -> np.ndarray:
        return np.asarray([(x >> ((self.n - 1 - i) * self.r_log2)) % self.r for i in range(self.n)])

    def compose_base_r(self, xs: np.ndarray, msb: int = 0) -> int:
        return sum(int(xi) * (self.r ** (self.n - 1 - i)) for i, xi in enumerate(xs)) + (msb << (len(xs) * self.r_log2))

    def mmm(self, X: int, Y: int) -> int:
        assert 0 <= X < self.M and 0 <= Y < self.M
        ys = self.decompose_base_r(Y)

        Z = 0
        for i in range(self.n):
            logger.debug(f'\n{i=}, yi={int(ys[i]):01x}')
            Z = Z + int(ys[self.n - 1 - i]) * X

            logger.debug(f'z1={Z:04x}')
            q = (Z * self.minus_M_inverse_mod_r) % self.r
            logger.debug(f'{q=:0x}')
            Z = Z + q * self.M
            assert Z % self.r == 0
            logger.debug(f'z2={Z:04x}')
            Z = Z // self.r
            logger.debug(f'z3={Z:04x}')

        if Z >= self.M:
            Z -= self.M
        return Z

    def mmm_v1(self, X: int, Y: int) -> int:
        assert 0 <= X < self.M and 0 <= Y < self.M

        ys = self.decompose_base_r(Y)
        xs = self.decompose_base_r(X)
        ms = self.decompose_base_r(self.M)

        zs = np.repeat(0, self.n)
        zs_msb: int = 0

        def propagate():
            nonlocal zs, zs_msb
            logger.debug(f'zs           ={zs_msb:0x}, {zs}')
            zs_msb += zs[0] // self.r
            zs = (zs % self.r) + slideup1(zs // self.r)
            logger.debug(f'zs_propagated={zs_msb:0x}, {zs}')
            assert all(zs <= 2 * self.r - 2)

        for i in range(self.n):
            yi = ys[self.n - 1 - i]
            logger.debug(f'\n{i=}, yi={int(yi):0x}')
            zs += xs * yi
            propagate()

            q = (zs[-1] * self.minus_M_inverse_mod_r) % self.r
            logger.debug(f'q={int(q):0x}')
            zs += q * ms
            propagate()
            zs = slidedown1(zs, zs_msb % self.r)
            zs_msb = zs_msb // self.r
            logger.debug(f'zs           ={zs_msb:0x}, {zs}')

        logger.debug('\nfinal')
        propagate()
        zs_msb = int(zs_msb)  # convert numpy type to python int type
        return self.compose_base_r(zs, zs_msb)

def random_int_with_filter(k: int, filter: Callable[[int], bool]):
    while True:
        r = random.randrange(2 ** k)
        if filter(r):
            return r

def main():
    parser = ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('-n', type=int, default=32)
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args()

    if args.seed:
        random.seed(args.seed)

    np.set_printoptions(formatter={'int': lambda x: hex(x)[2:]})
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format='<green>{time}</green> <level>{message}</level>',
        level='DEBUG' if args.debug else 'INFO'
    )

    R_log2 = args.n
    r_log2 = 16

    M = random_int_with_filter(R_log2, lambda x: x % 2 > 0 and x > 2 ** (R_log2 - r_log2))
    X = random_int_with_filter(R_log2, lambda x: x < M)
    Y = random_int_with_filter(R_log2, lambda x: x < M)
    logger.info(f'{M=:0x}')
    logger.info(f'{X=:0x}')
    logger.info(f'{Y=:0x}')

    mmm = MMM(M=M, n=R_log2 // r_log2, R_log2=R_log2, r_log2=r_log2)
    res = mmm.mmm(X, Y)

    res1 = mmm.mmm_v1(X, Y)

    expected = (X * Y * pow(1 << R_log2, -1, mod=M)) % M
    logger.info(f'{res      = :x}')
    assert(res == expected)
    assert(res1 == expected)

if __name__ == '__main__':
    main()
