build/mmm4096.S: mmm_mem.pl
	perl $^ > $@

build/mmm4096_scratch.S: mmm_mem.pl
	perl $^ --scratch > $@

build/mmm4096.elf: build/mmm4096.S mmm_main4096.c
	riscv32-none-elf-cc -march=rv32gcv -static -o $@ $^

build/mmm4096_scratch.elf: build/mmm4096_scratch.S mmm_main4096.c
	riscv32-none-elf-cc -DSCRATCHPAD -march=rv32gcv -static -o $@ $^

.PHONY: run4096
run4096: build/mmm4096.elf
	spike --isa=rv32gcv --varch=vlen:2048,elen:32 build/pk32 $^

.PHONY: run4096_scratch
run4096_scratch: build/mmm4096_scratch.elf
	spike --isa=rv32gcv --varch=vlen:2048,elen:32 build/pk32 $^

.PHONY: ref
ref: mmm.py
	python $^

.PHONY: ref4096
ref4096: mmm4096.py
	python $^
