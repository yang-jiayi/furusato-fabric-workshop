"""Private-file permissions are checked through each platform's real mechanism."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import measured_contract_profile as private_output


def assert_private_file(testcase, path):
    if os.name != "nt":
        testcase.assertEqual(path.stat().st_mode & 0o777, 0o600)
        return
    script = """
$ErrorActionPreference = 'Stop'
$acl = Get-Acl -LiteralPath $env:FURUSATO_TEST_PRIVATE_FILE
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$rules = @($acl.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier]))
if (-not $acl.AreAccessRulesProtected -or $rules.Count -ne 1) { throw 'DACL is not protected/single-principal' }
$rule = $rules[0]
if ($rule.IdentityReference -ne $sid -or $rule.IsInherited -or
    $rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow -or
    $rule.FileSystemRights -ne [System.Security.AccessControl.FileSystemRights]::FullControl) {
    throw 'DACL is not current-user-only FullControl'
}
"""
    env = os.environ.copy()
    env["FURUSATO_TEST_PRIVATE_FILE"] = str(path)
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                            env=env, text=True, capture_output=True)
    testcase.assertEqual(result.returncode, 0, result.stderr)


class PrivateOutputTests(unittest.TestCase):
    def test_private_permissions_and_exclusive_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "new.json"
            with private_output.private_text(path) as output:
                output.write('{"private": true}\n')
            assert_private_file(self, path)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                private_output.private_text(path)
            self.assertEqual(path.read_bytes(), before)

    def test_links_and_linked_parents_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_bytes(b"preserved")
            alias = root / "alias"
            alias.symlink_to(target)
            with self.assertRaises(ValueError):
                private_output.private_text(alias)
            folder = root / "folder"
            folder.mkdir()
            linked = root / "linked"
            linked.symlink_to(folder, target_is_directory=True)
            with self.assertRaises(ValueError):
                private_output.private_text(linked / "never-created")
            self.assertFalse((folder / "never-created").exists())
            self.assertEqual(target.read_bytes(), b"preserved")

    def test_permission_failure_is_not_a_writable_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "never-written"
            if os.name == "nt":
                with patch.object(private_output, "_windows_create", side_effect=PermissionError("DACL failed")):
                    with self.assertRaises(PermissionError):
                        private_output.private_text(path)
            else:
                with patch.object(private_output.os, "open", side_effect=PermissionError("mode failed")):
                    with self.assertRaises(PermissionError):
                        private_output.private_text(path)
            self.assertFalse(path.exists())

    def test_native_acl_readback_failure_leaves_only_empty_private_file(self):
        if os.name != "nt":
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "new"
                with private_output.private_text(path):
                    pass
                assert_private_file(self, path)
            return
        import ctypes
        load_library = ctypes.WinDLL

        class FailReadback:
            def __init__(self, library):
                self.library = library

            def __getattr__(self, name):
                if name == "GetSecurityInfo":
                    def denied(*args):
                        return 5
                    return denied
                return getattr(self.library, name)

        def library(name, **kwargs):
            native = load_library(name, **kwargs)
            return FailReadback(native) if name == "advapi32" else native

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "no-content"
            with patch.object(ctypes, "WinDLL", side_effect=library), self.assertRaises(OSError):
                private_output.private_text(path)
            self.assertEqual(path.read_bytes(), b"")
            assert_private_file(self, path)

    def test_posix_creation_keeps_exclusive_owner_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mocked-posix"
            with patch.object(private_output.os, "name", "posix"), \
                    patch.object(private_output, "Path", return_value=path), \
                    patch.object(private_output.os, "open", return_value=123) as create, \
                    patch.object(private_output.os, "fdopen", return_value="stream"):
                self.assertEqual(private_output.private_text(path), "stream")
                create.assert_called_once_with(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
