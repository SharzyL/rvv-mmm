n = 128
seed = 0

DEBUG =

.PHONY: run
run: build/mmm
	spike --isa=rv32gcv_zvl4096b_zve32f $(PK) $^

mmm_main.c: ref.py
	./ref.py -n $(n) --seed $(seed) --gen-main > $@

build/mmm: mmm_main.c mmm.c
ifdef DEBUG
	riscv32-none-elf-cc -O2 -march=rv32gcv $< -o $@ -DDEBUG
else
	riscv32-none-elf-cc -O2 -march=rv32gcv $< -o $@
endif
	riscv32-none-elf-objdump -d $@ > build/mmm.objdump

.PHONY: ref
ref:
ifdef DEBUG
	./ref.py -n $(n) --seed $(seed) --debug
else
	./ref.py -n $(n) --seed $(seed)
endif

.PHONY: clean
clean:
	rm build/* mmm_main.c -f
