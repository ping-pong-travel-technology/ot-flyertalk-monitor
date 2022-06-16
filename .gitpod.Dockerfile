FROM gitpod/workspace-full

# Install homebrew packages
RUN brew update && brew install black starship poetry