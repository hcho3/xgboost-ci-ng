"""
Wrapper script to run a command inside a Docker container
"""

import argparse
import grp
import itertools
import os
import pathlib
import pwd
import subprocess
import sys
import textwrap

SCRIPT_DIR = pathlib.Path(__file__).expanduser().resolve().parent
PROJECT_ROOT_DIR = SCRIPT_DIR.parent
LINEWIDTH = 88
TEXT_WRAPPER = textwrap.TextWrapper(
    width=LINEWIDTH,
    initial_indent="",
    subsequent_indent="    ",
    break_long_words=False,
    break_on_hyphens=False,
)


def parse_run_args(raw_run_args: str) -> list[str]:
    return [x for x in raw_run_args.split() if x]


def compute_container_id(container_name: str, build_args: list[dict[str, str]]) -> str:
    container_id = f"xgb-ci.{container_name}"
    # For some build arguments, append special suffixies
    for arg_name, suffix in [
        ("CUDA_VERSION_ARG", "cuda"),
        ("RAPIDS_VERSION_ARG", "rapids"),
        ("JDK_VERSION_ARG", "jdk"),
    ]:
        if arg_name in build_args:
            container_id += f"_{suffix}{build_args[arg_name]}"
    return container_id


def get_user_ids() -> dict[str, str]:
    uid = os.getuid()
    gid = os.getgid()
    return {
        "CI_BUILD_UID": str(uid),
        "CI_BUILD_USER": pwd.getpwuid(uid).pw_name,
        "CI_BUILD_GID": str(gid),
        "CI_BUILD_GROUP": grp.getgrgid(gid).gr_name,
    }


def fancy_print_cli_args(cli_args: list[str]) -> None:
    print(
        "=" * LINEWIDTH
        + "\n"
        + "  \\\n".join(TEXT_WRAPPER.wrap(" ".join(cli_args)))
        + "\n"
        + "=" * LINEWIDTH
        + "\n",
        flush=True,
    )


def docker_run(
    container_id: str,
    command_args: list[str],
    *,
    use_gpus: bool,
    workdir: pathlib.Path,
    user_ids: dict[str, str],
    extra_args: list[str],
) -> None:
    # Command-line arguments to be passed to `docker run`
    docker_run_cli_args = ["--rm", "--pid=host"]

    if use_gpus:
        docker_run_cli_args.extend(["--gpus", "all"])

    docker_run_cli_args.extend(["-v", f"{workdir}:/workspace", "-w", "/workspace"])
    docker_run_cli_args.extend(
        itertools.chain.from_iterable([["-e", f"{k}={v}"] for k, v in user_ids.items()])
    )
    docker_run_cli_args.extend(extra_args)
    docker_run_cli_args.append(container_id)
    docker_run_cli_args.extend(command_args)

    cli_args = ["docker", "run"] + docker_run_cli_args
    fancy_print_cli_args(cli_args)
    subprocess.run(cli_args, check=True, encoding="utf-8")


def main(args: argparse.Namespace) -> None:
    run_args = parse_run_args(args.run_args)
    user_ids = get_user_ids()

    if args.use_gpus:
        print("Using NVIDIA GPUs for `docker run`")
    if args.interactive:
        print("Using interactive mode for `docker run`")
        run_args.append("-it")

    docker_run(
        args.container_id,
        args.command_args,
        use_gpus=args.use_gpus,
        workdir=args.workdir,
        user_ids=user_ids,
        extra_args=run_args,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        usage=(
            f"{sys.argv[0]} --container-id CONTAINER_ID [--use-gpus] [--interactive] "
            "[--workdir WORKDIR] [--run-args RUN_ARGS] -- COMMAND_ARG "
            "[COMMAND_ARG ...]"
        ),
        description="Run tasks inside a Docker container",
    )
    parser.add_argument(
        "--container-id",
        type=str,
        required=True,
        help="String ID of the container to run.",
    )
    parser.add_argument(
        "--use-gpus",
        action="store_true",
        help=(
            "Grant the container access to NVIDIA GPUs; requires the NVIDIA "
            "Container Toolkit."
        ),
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help=(
            "Run the container in the interactive mode; requires an interactive shell "
            "(TTY). With this flag, you can use Ctrl-C to interrupt an long-running "
            "command."
        ),
    )
    parser.add_argument(
        "--workdir",
        type=lambda p: pathlib.Path(p).expanduser().resolve(),
        default=PROJECT_ROOT_DIR,
        help="Path to working directory; if unset, use the project's root",
    )
    parser.add_argument(
        "--run-args",
        type=str,
        default="",
        help=(
            "Argument(s) to be passed to `docker run`. When passing multiple "
            "arguments, use single quotes to wrap them. Example: "
            "--run-args '--cap-add SYS_PTRACE --shm-size=4g'"
        ),
    )
    parser.add_argument(
        "command_args",
        metavar="COMMAND_ARG",
        type=str,
        nargs="+",
        help=(
            "Argument(s) for the command to execute. NOTE. Make sure to specify "
            "double-dash (--) to clearly distinguish between the command and the "
            "preceding parameters. Example: --run-args '--cap-add SYS_PTRACE "
            "--shm-size=4g' -- ./myprog"
        ),
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    parsed_args = parser.parse_args()
    main(parsed_args)
