#include <math.h>
#include <stdint.h>
#include <stdio.h>

const int N = 1000;
const int REPEAT = 100;

const int vl = 128;

const int max_bits = 256;
const int word_bits = 16;
const int way = vl / word_bits / 2; // 32
const int s = 5; // ceil((max_bits / word_bits + 1) / way)

// 256 / 16 = 16
// 16 + 4 comes from s * way = 20
const uint32_t a[16 + 4] = {0xFFFF, 0xFFFF};
const uint32_t b[16 + 4] = {0xFFFF, 0xFFFF};
const uint32_t p[16 + 4] = {0xffed, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x7fff};
uint32_t abr1[16 + 4] = {0};
// imported from mmm.py
const uint32_t mu = 0xca1b;


// 32 = 2 * word_bits
// mu is of 16 bits
// R is 2 ** (max_bits + word_bits)
// n = 20
//                     a0                 a1                  a2                a3                 a4                    a5
void mmm_rvv16(uint64_t n, const uint32_t mu, const uint32_t* p, const uint32_t* a, const uint32_t* b, const uint32_t* abr1);

int main() {
  mmm_rvv16(20, mu, p, a, b, abr1);
  for(int i = 0; i != 20; ++i) {
    printf("%04X ", abr1[i]);
  }
  return 0;
}
