# rvv-mmm

Montgomery Modular Multiplication (MMM) in RISC-V Vector Extension (RVV).

MMM is common in RSA/ECC/PQC/ZKP

This is an implementation of [Montgomery Multiplication on the Cell](https://link.springer.com/chapter/10.1007/978-3-642-14390-8_50). We use perlasm here for more parameterized code generation (e.g. for different VLEN and BN) instead of intrinsics.

You can see all the parameters in `mmm.pl`. More document on this will be added.

Currently MMM is fully unrolled, and we dont have a stack now. The only memory access is the first two loads and last one store.

We will add a version with loops thus reducing code size (when VLEN=2048 and BN=4096 for RSA4096, the code size is 65K), but then there are data move between vregs.

We will add a version with stack capable of bigger BN with limited VLEN, but since there are a lot of saving/restoring BN to/from the stack, the efficiency will be a problem.

## usage

To run the RVV program, you can try

```bash
perl mmm.pl > mmm.S
# clang 14 is suggested
clang --target=riscv64 -march=rv64gcv -static -o mmm mmm.S mmm_main.c
spike --isa=rv64gcv --varch=vlen:128,elen:32 pk mmm
```

We have a reference implementation of the above paper in Python, just try the following command and you will find the answer as above

```bash
python mmm.py
```
