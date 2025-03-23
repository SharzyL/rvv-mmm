#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#define r_log2 16
#define r (1 << 16)

void print_array(uint32_t *x, int n) {
  printf("[");
  for (int i = 0; i < n; i++) {
    if (i > 0) {
      printf(", ");
    }
    printf("%04lx", x[i]);
  }
  printf("]\n");
}

// X, Y and M are arrays of of uint16_t zero-extended into uint32_t of length n,
// representing a big integer, with MSB first (big endian),
// R = r^n
// X, Y < M < R
void mmm(const uint32_t *X, const uint32_t *Y, const uint32_t *M, int32_t n,
         uint32_t minus_M_inverse_mod_r, uint32_t *Z) {
  int vlenb;
  asm("csrr %0, vlenb" : "=r"(vlenb));
  assert(n <= vlenb * 8 /* vregs */ / 4 /* bytes */);

  // load X to v8-15
  // load M to v16-23
  // Z will be in v24-31, initialzed as 0
  asm volatile("vsetvli zero, %0, e32, m8, tu, mu\n"
               "vle32.v v8, 0(%1)\n"
               "vle32.v v16, 0(%2)\n"
               "vxor.vv v24, v24, v24\n"
               :
               : "r"(n), "r"(X), "r"(M));

  for (int i = 0; i < n; i++) {
    uint32_t z_msb = 0;
    int16_t yi = Y[n - 1 - i];
    // Z += X * yi
    asm volatile("vmacc.vx v24, %0, v8\n" : : "r"(yi));

    asm volatile(
        // first propagation
        // move higher bits of Z into v0-v7
        "vsrl.vi v0, v24, 16\n"
        // extract msb into z_msb
        "vmv.x.s %0, v24\n"
        // slidedown v0-v7 to align with lower bits in Z
        "vslide1down.vx v0, v0, zero\n"
        // remove higher bits in Z
        "vand.vx v24, v24, %1\n"
        // Z += v0-v7
        "vadd.vv v24, v24, v0\n"
        : "=r"(z_msb)
        : "r"((1 << 16) - 1));

    z_msb = z_msb >> 16;

    uint32_t z0; // Z % 16, used to calculate q
    asm volatile("vslidedown.vx v0, v24, %1\n"
                 "vmv.x.s %0, v0\n"
                 : "=r"(z0)
                 : "r"(n - 1));

    uint32_t q = (z0 * minus_M_inverse_mod_r) % r;

    // Z += M * q
    asm volatile("vmacc.vx v24, %0, v16\n" : : "r"(q));
    // second propagation
    asm volatile("vslide1up.vx v0, v24, %2\n"
                 "vand.vx v0, v0, %1\n"
                 "vsrl.vx v24, v24, %0\n"
                 "vadd.vv v24, v24, v0\n"
                 :
                 : "r"(16), "r"((1 << 16) - 1), "r"(z_msb));
  }

  // final propagation
  asm volatile(
      "vsrl.vi v0, v24, 16\n"
      "vmv.x.s %0, v24\n"
      "vslide1down.vx v0, v0, zero\n"
      "vand.vx v24, v24, %0\n"
      "vadd.vv v24, v24, v0\n"
      :
      : "r"((1 << 16) - 1));

  asm volatile("vse32.v v24, 0(%0)" : : "r"(Z));
}

int main() {
  uint32_t X[] = {0xb13e, 0x117a, 0x2de9, 0x3bd1};
  uint32_t Y[] = {0x383a, 0x338e, 0x3f19, 0xa39b};
  uint32_t M[] = {0xc125, 0x7b23, 0xe38a, 0x13a3};
  uint32_t Z[4];

  mmm(X, Y, M, 4, 0x47f5, Z);
  print_array(Z, 4);
}
