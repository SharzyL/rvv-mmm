.PHONY: all
all: mmm

mmm.S: mmm_loop.pl
	perl $^ > $@

mmm4096.S: mmm_mem.pl
	perl $^ > $@

mmm: mmm.S mmm_main.c
	clang --target=riscv64 -march=rv64gcv -static -o $@ $^

mmm4096: mmm4096.S mmm_main4096.c
	clang --target=riscv64 -march=rv64gcv -static -o $@ $^

.PHONY: run
run: mmm
	./spike --isa=rv64gcv --varch=vlen:128,elen:32 pk mmm

.PHONY: run4096
run4096: mmm4096
	./spike --isa=rv64gcv --varch=vlen:128,elen:32 pk mmm4096

.PHONY: ref
ref: mmm.py
	python $^

.PHONY: ref
ref4096: mmm4096.py
	python $^
