{
  inputs.nixpkgs.url = "nixpkgs";
  inputs.makeShell.url = "github:ursi/nix-make-shell";

  outputs = { self, nixpkgs, makeShell }:
    let
      supportedSystems = [ "x86_64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      pkgs = forAllSystems (system: nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAllSystems (system: {
        default = pkgs.${system}.poetry2nix.mkPoetryApplication { projectDir = self; };
      });

      devShells = forAllSystems (system: 
      let 
        make-shell = import makeShell { inherit system; pkgs = pkgs.${system};};
      in
      {
        default = make-shell {
          packages = with pkgs.${system}; [
            python310
            jetbrains.pycharm-community
            telegram-bot-api 
            vscode-fhs
          ];
        };
      });
    };
}
