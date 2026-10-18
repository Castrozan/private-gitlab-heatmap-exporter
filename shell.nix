{
  pkgs ? import <nixpkgs> { },
}:
pkgs.mkShell {
  packages = [
    pkgs.nodejs_22
    (pkgs.python312.withPackages (packages: [
      packages.python-gitlab
      packages.svgwrite
    ]))
  ];
}
