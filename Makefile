.PHONY: all
all: mmm

mmm.S: mmm.pl
	perl $^ > $@

mmm: mmm.S mmm_main.c
	clang --target=riscv64 -march=rv64gcv -static -o $@ $^

.PHONY: run
run: mmm
	./spike --isa=rv64gcv --varch=vlen:128,elen:32 pk mmm

.PHONY: ref
ref: mmm.py
	python $^
