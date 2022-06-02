import math

# constants
N = 256 # max bits
w = 16 # word bits
way = 4 # simd way
w_2 = 2 ** w
n = N // w # e.g 4
s = math.ceil((n + 1) / way)
print("s", s)

# utils
# convert scalar value to 2 ** w radix representation
def scalar_vec(val):
    vec = []
    for i in range(s * way):
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
    C = [0]
    for i in range(len(M) - 1):
        C.append(M[i])
    return C

def row_left_shift_1(M):
    C = []
    for i in range(len(M) - 1):
        C.append(M[i + 1])
    C.append(0)
    return C

def column_zero():
    return scalar_column(0)

# input
p = 2 ** 255 - 19
a = 0xFFFFFFFF
b = 0xFFFFFFFF

# for exporing p to mmm_main.C
#ps = hex(p)[2:]
#ps4 = [ps[i:i+4] for i in range(0, len(ps), 4)]
#ps4.reverse()
#print("p", ps4)

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
# mont constant
mu = w_2 - modinv(p, w_2)
R = 2 ** (w * (n + 1))
Rinv = modinv(R, p)
# mu should be exported to mmm_main.c
print("mu", hex(mu));
#print("Rinv", Rinv)

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
    #print("round:", U)

for i in range(n + 1, 2 * n + 1 + 1):
    j = i % s
    k = (j + 1) % s
    d = i - (n + 1)
    C = row_carry(U[j])
    U[j] = row_module_w_2(U[j])
    # special for s-1 (cross boundary)
    if d != 0 and d % (s - 1) == 0:
        # shift 32 higher
        C = row_right_shift_1(C)
    U[k] = row_plus(U[k], C)

Z = column_zero()

for j in range(0, s):
    Z[j] = U[(n + j + 1) % s]

print("computed", hex(column_scalar(Z)))
print("referenc", hex((a * b * Rinv) % p))
