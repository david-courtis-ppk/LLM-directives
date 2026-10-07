# Set up Windows (WSL2) for PrecisePK development

This guide covers what is different on Windows. All PrecisePK tooling runs inside an Ubuntu distribution under WSL2 (Windows Subsystem for Linux, version 2), and Docker Desktop provides the Docker engine. Do the Windows-specific steps below, then follow the shared steps in [setup-macos.md](setup-macos.md) from the Ubuntu shell.

## Install WSL2 and Ubuntu

Run these in PowerShell as Administrator, then restart Windows:

```powershell
wsl --install -d Ubuntu-24.04
```

- Launch Ubuntu once from the Start menu to create your Linux user.
- Check that the distribution runs under WSL 2 with `wsl --list --verbose`. If it shows version 1, run `wsl --set-version Ubuntu-24.04 2`.
- Make it the default distribution with `wsl --set-default Ubuntu-24.04`. Docker Desktop and VS Code attach to the default distribution unless you choose another.
- If WSL fails with a virtualization error, enable virtualization in the PC's firmware (BIOS or UEFI) settings. See [Troubleshooting WSL](https://learn.microsoft.com/en-us/windows/wsl/troubleshooting).
- Docker Desktop's containers run inside WSL's memory allowance. To cap it, create `%UserProfile%\.wslconfig`, choose values that leave room for Windows, then run `wsl --shutdown`. The options are described in [WSL configuration](https://learn.microsoft.com/en-us/windows/wsl/wsl-config).

```ini
[wsl2]
memory=8GB
processors=4
```

## Install Docker Desktop

- Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) with the WSL 2 backend.
- In Docker Desktop, open Settings, then Resources, then WSL integration, and enable `Ubuntu-24.04`.
- Run `docker version` in the Ubuntu shell to confirm that the CLI reaches the engine.
- Use Docker Desktop's engine. Do not install a separate Docker Engine inside Ubuntu. The local gateway proxies every request to `kubernetes.docker.internal` (`PreciseRx-Web-PK/src/services/nginx/api_backends.conf:1-29`), a host name that Docker Desktop resolves and a plain Docker Engine does not.
- If Docker commands fail with a permission error, add your Windows account to the `docker-users` group from an Administrator PowerShell, then sign out and back in:

```powershell
net localgroup docker-users <your-windows-user> /add
```

## Install the tools inside Ubuntu

Every make target and script runs in the Ubuntu shell. Install the Linux builds of each tool, not the Windows installers.

```sh
sudo apt update
sudo apt install -y git make jq curl unzip
```

- Install AWS CLI version 2.15 or newer with AWS's [Linux installer](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
- Install Node 24 with [nvm](https://github.com/nvm-sh/nvm) (`nvm install 24`), then run `corepack enable` so each repository gets the pnpm version it pins.
- For PK-Library's C++ tests, run `sudo apt install -y build-essential cmake ninja-build ccache`.
- For Database tests, run `sudo apt install -y python3-pip python3-venv`. Ubuntu 24.04's `python3` is 3.12, which matches the Database image.
- The version table and the reason for each tool are in [setup-macos.md](setup-macos.md#install-the-tools).

## Clone inside the Linux file system

Clone the repositories into your Ubuntu home directory, for example `~/precisepk`, not under `/mnt/c`.

- Docker bind mounts and file watching are fast and reliable only on the Linux file system. Code under `/mnt/c` makes nodemon and Vite miss changes. See Docker's [WSL best practices](https://docs.docker.com/desktop/features/wsl/best-practices/).
- Git tools running on the Windows side drop the executable bit and can convert line endings. Bash scripts then fail with `Permission denied` or `bad interpreter`. This is why `make link-pk-library-js` re-applies the executable bit to PK-Library's prebuild scripts (`PreciseRx-Web-PK/Makefile:164-167`).
- Run git inside Ubuntu. For GitHub credentials, run `gh auth login` and then `gh auth setup-git`, or share [Git Credential Manager](https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-git#git-credential-manager-setup) from Git for Windows.
- Install VS Code on Windows with the WSL extension, then run `code .` from the Ubuntu shell to open a folder.

## Continue with the shared steps

From the Ubuntu shell, follow these sections of the macOS guide as written:

1. [Get the code](setup-macos.md#get-the-code).
2. [Sign in to AWS](setup-macos.md#sign-in-to-aws). If `aws sso login` cannot open a browser from WSL, copy the URL it prints into a Windows browser.
3. [Create the GitHub token](setup-macos.md#create-the-github-token).
4. [First run](setup-macos.md#first-run).
5. [Start the frontend](setup-macos.md#start-the-frontend). Vite tries to open a browser when it starts (`PreciseRx-Web/vite.config.ts:84`), which can fail quietly from WSL. Browse to `http://localhost:3000` in Windows yourself. WSL forwards `localhost` ports to Windows by default.
6. [Editor and browser](setup-macos.md#editor-and-browser). The C/C++ compiler path in the shared settings is a macOS path, so set `C_Cpp.default.compilerPath` to `/usr/bin/g++` in your user settings.

The same [common failures](setup-macos.md#common-failures) apply, with `brew` replaced by the Ubuntu equivalents.

## Windows-specific failures

| Symptom | Cause and fix |
| --- | --- |
| The `API-Gateway-*` container exits with `host not found in upstream "kubernetes.docker.internal"` | Docker is not Docker Desktop's engine. Remove any Docker Engine installed inside Ubuntu and enable WSL integration in Docker Desktop. |
| A script fails with `Permission denied` or `/bin/bash^M: bad interpreter` | The repository was cloned or edited by a Windows-side git tool. Clone it again inside Ubuntu. |
| Containers or Vite do not reload when you save | The code is under `/mnt/c`. Move the clone into your Ubuntu home directory. |
| The gateway cannot bind port 80 | A Windows service holds port 80. Find it with `netstat -ano \| findstr :80` in PowerShell and stop it. |
| WSL memory stays high while the stack is idle | Run `sudo make clear_cache` in `PreciseRx-Web-PK` to drop the Linux page cache (`Makefile:225-228`), or cap WSL memory in `.wslconfig`. |
| Docker reports `permission denied` on the Docker socket | Add your account to `docker-users` as shown above, then sign out and back in. |
| Ubuntu cannot be installed from the Microsoft Store | Use the [manual installation steps](https://learn.microsoft.com/en-us/windows/wsl/install-manual). |
