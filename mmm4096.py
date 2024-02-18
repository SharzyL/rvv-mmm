import math
import sys

import colorama

# constants
N = 4096    # max bits
w = 16      # word bits
way = 64    # simd way (vl = way * w * 2)
w_2 = 2 ** w
n = N // w  # num of words
s = math.ceil((n + 1) / way)  # num of regs

def eprint(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)

eprint(f's={s}')

# utils
# convert scalar value to 2 ** w radix representation
def scalar_vec(val):
    vec = []
    for _ in range(s * way):
        vec.append(val % w_2)
        val = val // w_2
    return vec

# convert radix representation to column representation
def vec_column(vec):
    col = []
    for i in range(s):
        row = []
        for j in range(way):
            row.append(vec[j * s + i])
        col.append(row)
    return col

def column_vec(col):
    vec = []
    for j in range(way):
        for i in range(s):
            vec.append(col[i][j])
    return vec

def vec_scalar(vec):
    val = 0
    for i in range(s * way):
        val = w_2 * val + vec[s * way - 1  - i]
    return val

def scalar_column(val):
    return vec_column(scalar_vec(val))

def column_scalar(col):
    return vec_scalar(column_vec(col))

# util for a row in column (simd reg)
def row_plus(M, A):
    C = []
    for i in range(len(M)):
        C.append(A[i] + M[i])
    return C

def row_mac(M, A, B):
    C = []
    for i in range(len(M)):
        C.append(A[i] * B[i])
    return row_plus(M, C)

def row_mac_scalar(M, A, b):
    C = []
    for i in range(len(M)):
        C.append(b)
    return row_mac(M, A, C)

def row_carry(M):
    C = []
    for i in range(len(M)):
        C.append(M[i] // w_2)
    return C

def row_module_w_2(M):
    C = []
    for i in range(len(M)):
        C.append(M[i] % w_2)
    return C

def row_right_shift_1(M):
    return [0] + M[:-1]

def row_left_shift_1(M):
    return M[1:] + [0]

def column_zero():
    return scalar_column(0)

def modinv(R, p):
    t = 0
    r = p
    newt = 1
    newr = R
    while newr != 0:
        q = r // newr
        (t, newt) = (newt, t - q * newt)
        (r, newr) = (newr, r - q * newr)

    if r != 1:
        return 0
    if t < 0:
        return t + p
    return t

def main():
    # input
    #p = 2 ** 255 - 19
    p = 822403894949685941052460286880568280267015952000308719889576568438721328554878228148279674165615573420113632245787115644076842175584036845156076777116407163194678526843450668564300452501369163966535540893184973095168214143661117385634631393046590300521563384183720835190704702785281611405730004323149634880582139641799587428066521898449596588812720562755024312650664646564560384737212277659528370961363786902598622518269815755463658139088672082804173766572604432620314959589627100740387574349633264540304130249362268425405326331052724252098193350612224695440084760151385074157280738495586331580108638698105436438413792839440800172246120790326077813636742445833448294397951483323315743639355041876965043974100533118512216387191204435246317633555392622172121104925170595068415683328574029283188902065001609084034917492625034790341408716303608762554397674742673873946464746669049353114488453626799815891665053392515457506070014493622194755799836191228739958028324371561725528059549130126219647299320311384970693794313178128686420634136426664940767823110999192617213701919311477056672221357534659617850854575778467151933103289377620995943013514877790920602301796775684270047040421345181843904903355229975892036609709004199655476799709829
    a = 0xFFFFFFFF
    b = 0xFFFFFFFF

    #ps = hex(p)[2:]
    #ps4 = [ps[i:i+4] for i in range(0, len(ps), 4)]
    #ps4.reverse()
    #eprint("p", ps4)

    # mont constant
    mu = w_2 - modinv(p, w_2)
    R = 2 ** (w * (n + 1))
    Rinv = modinv(R, p)
    eprint(f'mu={mu:X}')
    #eprint("Rinv", Rinv)

    P = scalar_column(p)
    A = scalar_column(a)
    B = scalar_column(b)

    U = column_zero()

    for i in range(0, n + 1):
        # U = b_i*A + U
        k = column_vec(B)[i]
        for j in range(0, s):
            ij = (i + j) % s
            U[ij] = row_mac_scalar(U[ij], A[j], k)

        # propagate carry
        for j in range(0, s):
            ij = (i + j) % s
            ij1 = (i + j + 1) % s
            C = row_carry(U[ij])
            U[ij] = row_module_w_2(U[ij])
            # special propagate for s-1
            if j == s - 1:
                C = row_right_shift_1(C)
            U[ij1] = row_plus(U[ij1], C)

        # U = q*P + U
        ## least significant 16 bit of U
        u0 = U[i % s][0]
        q = (u0 * mu) % w_2
        for j in range(0, s):
            ij = (i + j) % s
            U[ij] = row_mac_scalar(U[ij], P[j], q)

        # propagate carry
        for j in range(0, s):
            ij = (i + j) % s
            ij1 = (i + j + 1) % s
            C = row_carry(U[ij])
            U[ij] = row_module_w_2(U[ij])
            # special propagate for s-1
            if j == s - 1:
                C = row_right_shift_1(C)
            U[ij1] = row_plus(U[ij1], C)

        # vshift 32 for lowest (highest in next iteration)
        U[i % s] = row_left_shift_1(U[i % s])
        #eprint("round:", U)

    for i in range(n + 1, 2 * n + 1 + 1):
        j = i % s
        k = (j + 1) % s
        d = i - (n + 1)
        C = row_carry(U[j])
        U[j] = row_module_w_2(U[j])
        # special for s-1 (cross boundary)
        if d % s == s - 1:
            # shift 32 higher
            C = row_right_shift_1(C)
        U[k] = row_plus(U[k], C)

    Z = column_zero()

    for j in range(0, s):
        Z[j] = U[(n + j + 1) % s]

    computed = column_scalar(Z)
    referenc = (a * b * Rinv) % p

    computed_str_builder = []
    referenc_str_builder = []
    is_correct = True
    for i, (computed_word, referenc_word) in enumerate(zip(scalar_vec(computed), scalar_vec(referenc))):
        if computed_word != referenc_word:
            computed_str_builder.append(f'{colorama.Fore.RED}{computed_word:04X}{colorama.Fore.RESET}')
            referenc_str_builder.append(f'{colorama.Fore.RED}{referenc_word:04X}{colorama.Fore.RESET}')
            is_correct = False
        else:
            computed_str_builder.append(f'{computed_word:04X}')
            referenc_str_builder.append(f'{referenc_word:04X}')
    print(f'{" ".join(computed_str_builder)}')
    if is_correct:
        eprint('Result correct')
    else:
        eprint(f'referenc: {" ".join(referenc_str_builder)}')


if __name__ == '__main__':
    colorama.init()
    main()
