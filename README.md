# rvv-mmm

Montgomery Modular Multiplication (MMM) in RISC-V Vector Extension (RVV).

MMM is extensively used in RSA/ECC/PQC/ZKP.

This is based on [Montgomery Multiplication on the Cell](https://link.springer.com/chapter/10.1007/978-3-642-14390-8_50). We have a reference implementation of the algorithm in `ref.py`

## Usage

Enter the environment with `nix`:
```console
$ nix develop
```

Run reference implementation:

```console
$ make ref
```

Compile C code and simulate with Spike:

```console
$ make run
```

We can specify MMM size with variable `n`, and output verbose debug message with variable `DEBUG` in GNU Make.

```console
$ make ref n=4096 DEBUG=1
$ make run n=4096 DEBUG=1
```
