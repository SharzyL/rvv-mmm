build/mmm_neo: mmm_neo.c
	riscv32-none-elf-cc -O2 -march=rv32gcv $^ -o $@
	riscv32-none-elf-objdump -d $@ > build/mmm_neo.objdump

.PHONY: run_mmm_neo
run_mmm_neo: build/mmm_neo
	spike --isa=rv32gcv_zvl4096b_zve32f $(PK) build/mmm_neo
