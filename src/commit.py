# this file shall be identical anywhere else.
# TODO: fallback to default commit message when git commit failed (just add another line `git commit -m 'update'` right after `git commit --noedit`
import pytz
import datetime
import os
import shutil

from easyprocess import EasyProcess
import traceback
import filelock
from hashlib import md5

# this is equivalent to commandline 'md5sum' command
def md5sum(filename, buf_size=8192):
    m = md5()
    # the with statement makes sure the file will be closed
    with open(filename, 'rb') as f:
        # We read the file in small chunk until EOF
        data = f.read(buf_size)
        while data:
            # We had data to the md5 hash
            m.update(data)
            data = f.read(buf_size)
    # We return the md5 hash in hexadecimal format
    return m.hexdigest()

# from easyprocess import EasyProcessError, log
# from typing import Any
# import tempfile
# import subprocess

# def start(self) -> "EasyProcess":
#     """start command in background and does not wait for it.

#     :rtype: self

#     """
#     if self.is_started:
#         raise EasyProcessError(self, "process was started twice!")

#     stdout: Any = None
#     stderr: Any = None
#     if self.use_temp_files:
#         self._stdout_file = tempfile.TemporaryFile(prefix="stdout_")
#         self._stderr_file = tempfile.TemporaryFile(prefix="stderr_")
#         stdout = self._stdout_file
#         stderr = self._stderr_file

#     else:
#         stdout = subprocess.PIPE
#         stderr = subprocess.PIPE
#     # cmd = list(map(uniencode, self.cmd))

#     try:
#         self.popen = subprocess.Popen(
#             self.cmd,
#             stdout=stdout,
#             stderr=stderr,
#             cwd=self.cwd,
#             env=self.env,
#             shell=True,  # override shell support.
#         )
#     except OSError as oserror:
#         log.debug("OSError exception: %s", oserror)
#         self.oserror = oserror
#         raise EasyProcessError(self, "start error")
#     self.is_started = True
#     log.debug("process was started (pid=%s)", self.pid)
#     return self


# EasyProcess.start = start

# on windows nt, alert us (using tkinter or native api?) if commit has failed.
# on other platforms, please improvise.

base_repo = os.path.basename(os.curdir)
repo_basedir = os.path.abspath(".")
os_name = os.name
import platform
platform_name = platform.system()
toast_title = f"commit error at '{base_repo}'"


def raise_exception(msg):
    raise Exception(msg)


def check_proc_exit_status_base(proc: EasyProcess, action: str, printer):
    if proc.return_code != 0:
        printer(f"Abnormal exit code {proc.return_code} during {action}.")


def run_and_check_proc_base(cmd, action, printer=raise_exception):
    proc = EasyProcess(cmd).call()
    print(f"Stdout:\n{proc.stdout}\nStderr:\n{proc.stderr}")
    check_proc_exit_status_base(proc, action, printer)


def check_if_executable_in_path(
    executable: str, extra_info="", raise_exception: bool = True
):
    lookup_result = shutil.which(executable)
    if lookup_result:
        print("executable {} found in path: {}".format(executable, lookup_result))
        return True
    elif raise_exception:
        base_exc = "executable {} not found in path.".format(executable)
        if extra_info:
            base_exc = "\n".join([base_exc, extra_info])
        raise Exception(base_exc)
    return False


if platform_name == "Windows":
    from win10toast import ToastNotifier

    toaster = ToastNotifier()

    def show_toast(msg):
        toaster.show_toast(title=toast_title, msg=msg)

elif platform_name == "Darwin":
    notifier_exec = "terminal-notifier"
    check_if_executable_in_path(notifier_exec)

    def show_toast(msg):
        cmd = [notifier_exec, "-title", toast_title, "-message", msg]
        run_and_check_proc_base(cmd, "sending macos toast")

elif platform_name == "Linux":
    notifier_exec = "notify-send"
    check_if_executable_in_path(notifier_exec)

    def show_toast(msg):
        cmd = [notifier_exec, toast_title, msg]
        run_and_check_proc_base(cmd, "sending linux toast")

else:
    raise Exception(f"\nunable to show toast message due to unknown os: {platform_name}")


def emit_message_and_raise_exception(exc_info: str):
    show_toast(exc_info)
    raise Exception(exc_info)


import sys
import better_exceptions


def excepthook(exc_type, exc_value, tb):
    better_exceptions.SUPPORTS_COLOR = False
    formatted = "".join(better_exceptions.format_exception(exc_type, exc_value, tb))
    formatted_exc = ["<TOPLEVEL EXCEPTION>", formatted]
    msg = "\n".join(formatted_exc)
    with open(os.path.join(repo_basedir, ".last_failed_commit"), "w+") as f:
        f.write(msg)
    better_exceptions.SUPPORTS_COLOR = True
    better_exceptions.excepthook(exc_type, exc_value, tb)


sys.excepthook = excepthook

# currently only enable gitcommit support for each (sub)repo. no recursive commit support yet.
repodirs = []

for path, dirpath, filepath in os.walk("."):
    if ".git" in dirpath:
        repodirs.append(path)


def get_script_path_and_exec_cmd(script_prefix):
    if os.name == "nt":
        script_suffix = "cmd"
        exec_prefix = "cmd /C"
    else:
        script_suffix = "sh"
        exec_prefix = "bash"
    script_path = f"{script_prefix}.{script_suffix}"
    cmd = f"{exec_prefix} {script_path}"
    try:
        assert os.path.exists(script_path)
        return script_path, cmd
    except:
        emit_message_and_raise_exception(
            "script {} not found in path.".format(script_path)
        )


_, COMMIT_EXEC = get_script_path_and_exec_cmd("commit")

try:
    assert "." in repodirs
except:
    emit_message_and_raise_exception(
        f"current directory is not a git repo root dir!\nLocation: {repo_basedir}"
    )

base_repo_name_and_location = f"repo {base_repo}\nLocation: {repo_basedir}"

# CHECK_GPTCOMMIT_KEYS = "gptcommit config keys"

# check_if_exist_keylist = ["openai.apibase", "openai.api_key"]


def check_proc_exit_status(proc, action):
    check_proc_exit_status_base(proc, action, emit_message_and_raise_exception)


def run_and_check_proc(cmd, action):
    run_and_check_proc_base(cmd, action, emit_message_and_raise_exception)

reserved_repos = ['.git_backup']
repo_absdirs = [os.path.abspath(p) for p in repodirs if os.path.basename(p) not in reserved_repos]

check_if_executable_in_path(
    "gptcommit", "please install by running `cargo install --locked gptcommit`."
)
last_commit_time_filepath = ".last_commit_time"

# import pathlib
# GPTCOMMIT_HOOKED = ".gptcommit_hooked"
GPTCOMMIT_HOOK_MD5SUM = '69de652c2f76f0c3a209363c4943821c'
GPTCOMMIT_HOOK_PATH = '.git/hooks/prepare-commit-msg'

total_modification = 0
repo_absdir_to_modification = {}
for repo_absdir in repo_absdirs:  # is there anything needed to commit?
    os.chdir(repo_absdir)
    proc = EasyProcess("git status -s").call()
    check_proc_exit_status(proc, "checking git status at %s" % repo_absdir)
    git_status_lines = proc.stdout.split("\n")
    modification = 0
    for line in git_status_lines:
        line = line.strip()
        if last_commit_time_filepath == line.split(" ")[-1].strip():
            continue
        else:
            modification += 1

    print("Location:", repo_absdir)
    repo_reldir = os.path.basename(repo_absdir)
    # proc = EasyProcess(CHECK_GPTCOMMIT_KEYS).call()
    # check_proc_exit_status(proc, "checking gptcommit config keys")

    repo_name_and_location = f"repo {repo_reldir}\nLocation: {repo_absdir}"

    # if any([k for k in check_if_exist_keylist if k not in proc.stdout]):
    repo_absdir_to_modification[repo_absdir] = modification
    total_modification += modification

    # TODO: checksum the '.git/hooks/prepare-commit-msg' file if exists

    # if not os.path.exists(GPTCOMMIT_HOOKED):
    hooked = False
    if os.path.exists(GPTCOMMIT_HOOK_PATH):
        if md5sum(GPTCOMMIT_HOOK_PATH) == GPTCOMMIT_HOOK_MD5SUM:
            hooked = True
        else:
            print("WARNING: md5sum mismatch.")
            print("Installing the hook will overwrite the existing hook.")
    else:
        print("Could not find the hook.")
    if not hooked:
        print(
            f"setting up gptcommmit locally at repo {repo_reldir}.\nLocation: {repo_absdir}"
        )
        setup_file, SETUP_GPTCOMMIT = get_script_path_and_exec_cmd("setup_gptcommit")

        if not os.path.exists(setup_file):
            emit_message_and_raise_exception(
                f"setup file '{setup_file}' does not exist in {repo_name_and_location}"
            )
        run_and_check_proc(SETUP_GPTCOMMIT, "setting up gptcommit")
        # pathlib.Path(GPTCOMMIT_HOOKED).touch()
    else:
        print(f"assume gptcommit already setup at repo {repo_reldir}.\nLocation: {repo_absdir}")



if total_modification == 0:
    print("no modification, no need to commit")
    exit(0)

# exit()
os.chdir(repo_basedir)

# setup timezone as Shanghai

timezone_str = "Asia/Shanghai"
timezone = pytz.timezone(timezone_str)

print("using timezone:", timezone)


def get_time_now():
    return datetime.datetime.now(tz=timezone)


commit_min_interval = datetime.timedelta(minutes=30)


def get_last_commit_time():
    read_from_file = False
    last_commit_time = datetime.datetime.fromtimestamp(0, tz=timezone)
    if os.path.exists(last_commit_time_filepath):
        with open(last_commit_time_filepath, "r") as f:
            content = f.read()
        try:
            last_commit_time = datetime.datetime.fromisoformat(content)
            print("last commit time:", last_commit_time)
            read_from_file = True
        except:
            traceback.print_exc()

    if not read_from_file:
        print("using default last commit time:", last_commit_time)

    return last_commit_time


def check_if_commitable():
    last_commit_time = get_last_commit_time()
    time_now = get_time_now()
    commitable = False
    await_interval = last_commit_time + commit_min_interval - time_now
    if await_interval.total_seconds() < 0:
        print("able to commit.")
        commitable = True
    else:
        print(
            f"need to wait for {await_interval.total_seconds() // 60} minutes till next commit."
        )
    return commitable


def commit():
    if check_if_commitable():
        with filelock.FileLock(f".commit_lock{'_nt' if os.name == 'nt' else ''}" , timeout=1):
            exit_code = os.system(COMMIT_EXEC)
            if exit_code != 0:
                emit_message_and_raise_exception(
                    f"commit changes at {base_repo_name_and_location}"
                )

            with open(last_commit_time_filepath, "w+") as f:
                time_now = get_time_now()
                print(f"successfully commited at: {time_now}\nLocation: {repo_basedir}")
                content = time_now.isoformat()
                f.write(content)


if __name__ == "__main__":
    commit()
