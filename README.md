# rvv-mmm

Montgomery Modular Multiplication (MMM) in RISC-V Vector Extension (RVV).

MMM is common in RSA/ECC/PQC/ZKP

This is an implementation of [Montgomery Multiplication on the Cell](https://link.springer.com/chapter/10.1007/978-3-642-14390-8_50). We use perlasm here for more parameterized code generation (e.g. for different VLEN and BN) instead of intrinsics.

You can see all the parameters in `mmm.pl`. More document on this will be added.

`mmm.pl` is fully unrolled, and we dont need stack in this implementation. The only memory access is the first two loads and last one store. But the code size is a concern. when VLEN=2048 and BN=4096 for RSA4096, the code size is 65KiB. You can learn the detail of the algorithm from this file and `mmm.py`. Versions below is quite complex and they are based on `mmm.pl`.

`mmm_loop.pl` is a version with loops thus it reduces code size, but then there is overhead on move data between vregs (`vmv.v.v`).

`mmm_mem.pl` is a version capable of bigger BN with limited VLEN (e.g. RSA4096 with VLEN=128). During computation it saves/restores BN to/from the variable, The efficiency could be problem if the cache is not big enough, but the code size is pretty good now.

## usage

To run the RVV program, you can try

```bash
perl mmm_loop.pl > mmm.S
# clang 14 is suggested
clang --target=riscv64 -march=rv64gcv -static -o mmm mmm.S mmm_main.c
spike --isa=rv64gcv --varch=vlen:128,elen:32 pk mmm
# or you can use make run for all these above
```

We have a reference implementation of the above paper in Python, just try the following command and you will find the answer as above

```bash
python mmm.py
# or make ref
```

## 4096

The biggest ever MMM is for RSA4096. A demo for 4096-bit mmm is given by `mmm_mem.pl`

```bash
perl mmm_mem.pl > mmm4096.S
# clang 14 is suggested
clang --target=riscv64 -march=rv64gcv -static -o mmm4096 mmm4096.S mmm_main4096.c
spike --isa=rv64gcv --varch=vlen:128,elen:32 pk mmm4096
# or make run4096
```

And the reference for it
```bash
python mmm4096.py
# or make ref4096
```
