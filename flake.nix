{
  inputs = {
    nixpkgs.url = "nixpkgs";
    flake-utils.url = "flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }@inputs:
    flake-utils.lib.eachDefaultSystem
      (system:
        let
          pkgs = import nixpkgs { inherit system; };
          pythonEnv = pkgs.python3.withPackages (ps: with ps; [ colorama numpy ipython ]);
        in
        {
          legacyPackages = pkgs;
          devShell = pkgs.mkShell {
            nativeBuildInputs = with pkgs; [
              spike
              dtc
              pkgs.pkgsCross.riscv32-embedded.stdenv.cc

              pythonEnv
            ];
            env = {
              PK = "${pkgs.pkgsCross.riscv32-embedded.riscv-pk}/bin/pk";
            };
          };
        }
      )
    // { inherit inputs; };
}
