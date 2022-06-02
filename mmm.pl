#! /usr/bin/env perl
use POSIX;
use warnings;

# $output is the last argument if it looks like a file (it has an extension)
# $flavour is the first argument if it doesn't look like a file
$output = $#ARGV >= 0 && $ARGV[$#ARGV] =~ m|\.\w+$| ? pop : undef;
#$flavour = $#ARGV >= 0 && $ARGV[0] !~ m|\.| ? shift : undef;

$output and open STDOUT,">$output";

my $code = "";

################################################################################
# Constants
################################################################################

my $xl = 64; # XLEN
my $vl = 128; # VLEN should be at least $vl
my $el = 32; # ELEN should be at least $el
# we only support LMUL = 1
my $lmul = 1;

my $bn = 256; # bits of Big Number
my $word = 16; # number of bits in one SEW
my $R = $bn + $word; # log(montgomery radix R). 
# e.g. when bn = 256, word = 16, then R = log(2 ** (256 + 16)) = 272
# the result of this mmm is A*B*2^{-R} mod P

my $sew = $word * 2; # SEW
if ($sew > $el) {
    die "SEW must not be greater than ELEN! params: vl $vl, el $el, word $word, sew $sew";
}

my $way = $vl / $sew; # simd way
my $niter = $bn / $word; # number of iterations
my $nreg = $niter / $way + 1; # number of vreg for one bn
# max nreg = 8 as restraint by seg8
# thus max possible value for bn is 8 * (VLEN / 2) - word >= 496, suitable for most ECC (not P521, though)
# of couse with greater VLEN=2048 we can compute RSA 4096 here
if ($nreg > 8) {
    die "nreg must not be greater than 8! params: vl $vl, sew $sew, bn $bn, word $word, nreg $nreg";
}
my $nelement = $nreg * $way; # number of elements should be in A, B, P and AB
# actual bits used for one bn: $nreg * $vl
# we use vlseg to load data
# e.g, when BN = 256, VLEN = 128 and SEW = 32
# nreg is 5 instead of 4, thus nelement is 20 instead of 16

################################################################################
# Register assignment
################################################################################

my ($N,$MU,$P,$A,$B,$AB) = ("a0", "a1", "a2", "a3", "a4", "a5");

my ($T0) = ("t0"); # happy that it is caller-saved

my ($PVN, $AVN, $ABVN) = (0, 10, 20);
my ($PV, $AV, $ABV) = ("v$PVN", "v$AVN", "v$ABVN");

# temporary reg
my $TV = "v30";
my $TV2 = "v31";

################################################################################
# utility
################################################################################

sub propagate {
    my $i = shift;
    my $j = shift;
    my $f = shift;
    my $ij = ($i + $j) % $nreg;
    my $ij1 = ($i + $j + 1) % $nreg;
    my $ABVIJ = "v@{[$ABVN + $ij]}";
    my $ABVIJ1 = "v@{[$ABVN + $ij1]}";
    $code .= <<___;
    # save carry in TV
    vsrl.vi $TV, $ABVIJ, $word
    # mod 2 ** $word
    # !!!!! important: here we assume elen = 2 * word
    vsll.vi $ABVIJ, $ABVIJ, $word
    vsrl.vi $ABVIJ, $ABVIJ, $word
___
    if ($j == $nreg - 1) {
    # carry of AB_s-1 does not add to AB_0
        if ($f == 1) {
        $code .= <<___;
    # for final round, instead of slide1up, add then slide1down
    # we can just slide1down and add
    # generally slide is expensive
    vslide1down.vx $TV2, $ABVIJ1, zero
    vadd.vv        $TV2, $TV2, $TV
    vmv.v.v        $ABVIJ1, $TV2
___
        } else {
        $code .= <<___;
    vslide1up.vx $TV2, $TV, zero
    vadd.vv $ABVIJ1, $ABVIJ1, $TV2
___
        }
    } else {
        $code .= <<___;
    vadd.vv $ABVIJ1, $ABVIJ1, $TV
___
    }
}

################################################################################
# function
################################################################################
$code .= <<___;
.text
.balign 16
.globl mmm_rvv${word}
.type mmm_rvv${word},\@function
# assume VLEN >= $vl, BN = $bn, SEW = $word * 2 = $sew
# we only support LMUL = 1 for now
# P, A, B, AB should have $nelement elements
mmm_rvv${word}:
    # quite SIMD
    li  $T0, $way # in case way > 31
    vsetvli zero, $T0, e$sew, m$lmul, ta, ma

    # load values from arg
    vlseg${nreg}e$sew.v $PV, ($P)
    vlseg${nreg}e$sew.v $AV, ($A)
___

    # set ABV to 0
for (my $j = 0; $j != $nreg; $j++) {
    my $ABVJ = "v@{[$ABVN + $j]}";
    $code .= <<___;
    vmv.v.i            $ABVJ, 0
___
}

for (my $i = 0; $i <= $niter; $i++) {
    # AB = B_i*A + AB
    $code .= <<___;
    # !!!!!! important: lw here assumes SEW = 32
    lw $T0, @{[$i * 4]}($B)
___
    for (my $j = 0; $j != $nreg; $j++) {
        my $ij = ($i + $j) % $nreg;
        my $ABVIJ = "v@{[$ABVN + $ij]}";
        my $AVJ = "v@{[$AVN + $j]}";
        $code .= <<___;
        vmacc.vx $ABVIJ, $T0, $AVJ
___
    }

    # propagate carry for nreg round
    for (my $j = 0; $j != $nreg; $j++) {
        propagate($i, $j, 0);
    }

    # AB = q*P + AB
    my $is = $i % $nreg;
    my $ABVI = "v@{[$ABVN + $is]}";
    $code .= <<___;
    vmv.x.s $T0, $ABVI
    mul     $T0, $T0, $MU
    # mod 2 ** $word
    # !!!! important: here we assume SEW = 32 and XLEN = 64
    sllw    $T0, $T0, $word
    srlw    $T0, $T0, $word
___
    for (my $j = 0; $j != $nreg; $j++) {
        my $ij = ($i + $j) % $nreg;
        my $ABVIJ = "v@{[$ABVN + $ij]}";
        my $PVJ = "v@{[$PVN + $j]}";
        $code .= <<___;
        vmacc.vx $ABVIJ, $T0, $PVJ
___
    }

    # propagate carry for nreg round
    for (my $j = 0; $j != $nreg - 1; $j++) {
        propagate($i, $j, 0);
    }
    propagate($i, $nreg - 1, 1);
}

# propagate carry for niter round
for (my $k = $niter + 1; $k <= 2 * $niter + 1; $k++) {
    my $i = $niter + 1;
    my $j = ($k - $i) % $nreg;
    propagate($i, $j, 0);
}

# restore order of AB: move AB[i] to A[0]
# AB[i+1] to A[1], etc..
my $is = ($niter+1) % $nreg;
for (my $j = 0; $j != $nreg; $j++) {
    my $AVJ = "v@{[$AVN + $j]}";
    my $ji = ($j + $is) % $nreg;
    my $ABVJI = "v@{[$ABVN + $ji]}";
    $code .= <<___;
    vmv.v.v $AVJ, $ABVJI
___
}

$code .= <<___;
    vsseg${nreg}e$sew.v $AV, ($AB)
    ret
___

print $code;
close STDOUT or die "error closing STDOUT: $!";
