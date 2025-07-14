{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  buildInputs = [
    pkgs.python3
    pkgs.python3Packages.python-gitlab
    pkgs.python3Packages.svgwrite
  ];

  shellHook = ''
    # Source your existing shell configuration
    if [ -f ~/.bashrc ]; then
      source ~/.bashrc
    fi

    # Store original PS1
    OLD_PS1=$PS1
    # Add red (nix_shell) to the existing PS1
    export PS1="\[$OLD_PS1\]\[\033[31m\](nix_shell)\[\033[00m\]$ "
  '';
}
