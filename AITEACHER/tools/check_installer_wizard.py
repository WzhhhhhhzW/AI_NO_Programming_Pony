"""Validate the real Inno wizard with a fixture isolated from the installed app.

The production UI code and artwork are compiled unchanged, except that its
InitializeWizard is wrapped with native control assertions. The fixture installs
only a text file under build/, uses a fresh AppId, and has no registry,
uninstaller, shortcut, application-closing, or application-running actions.
This checks native geometry and /DIR handling; it does not automate UI input or
claim to visually verify a silent wizard.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "build" / "v16_21_installer_validation"
DEFAULT_COMPILER = (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" /
                    "Inno Setup 6" / "ISCC.exe")
REMOVED_SECTIONS = {"icons", "run", "uninstalldelete", "registry", "installdelete",
                    "uninstallrun"}
ALLOWED_SECTIONS = {"setup", "languages", "tasks", "messages", "custommessages",
                    "langoptions", "files", "code"}
NATIVE_CHECKS = r"""
procedure ValidateAssert(Passed: Boolean; const CheckName: String);
begin
  if Passed then
    ValidationReport := ValidationReport + 'PASS=' + CheckName + #13#10
  else begin
    ValidationReport := ValidationReport + 'FAIL=' + CheckName + #13#10;
    SaveStringToFile('__REPORT__', ValidationReport, False);
    RaiseException('Native installer validation failed: ' + CheckName);
  end;
end;

function ValidationWithin(Control: TControl; Page: TWinControl): Boolean;
begin
  Result := (Control.Parent = Page) and
    (Control.Left >= 0) and (Control.Top >= 0) and
    (Control.Width > 0) and (Control.Height > 0) and
    (Control.Left + Control.Width <= Page.ClientWidth) and
    (Control.Top + Control.Height <= Page.ClientHeight);
end;

function ValidationSeparate(A, B: TControl): Boolean;
begin
  Result := (A.Left + A.Width <= B.Left) or
    (B.Left + B.Width <= A.Left) or
    (A.Top + A.Height <= B.Top) or
    (B.Top + B.Height <= A.Top);
end;

procedure InitializeWizard;
begin
  InitializeBrandWizard;
  ValidationReport :=
    'FORM_WIDTH=' + IntToStr(WizardForm.Width) + #13#10 +
    'FORM_HEIGHT=' + IntToStr(WizardForm.Height) + #13#10 +
    'CLIENT_WIDTH=' + IntToStr(WizardForm.ClientWidth) + #13#10 +
    'CLIENT_HEIGHT=' + IntToStr(WizardForm.ClientHeight) + #13#10 +
    'FONT=' + WizardForm.Font.Name + #13#10 +
    'FONT_SIZE=' + IntToStr(WizardForm.Font.Size) + #13#10 +
    'FONT_DPI=' + IntToStr(WizardForm.Font.PixelsPerInch) + #13#10 +
    'SCALE_X_100=' + IntToStr(ScaleX(100)) + #13#10 +
    'SCALE_Y_100=' + IntToStr(ScaleY(100)) + #13#10;
  ValidateAssert(CompareText(WizardForm.Font.Name,
    'Microsoft YaHei UI') = 0, 'font_name');
  ValidateAssert(WizardForm.DirEdit.Enabled and
    not WizardForm.DirEdit.ReadOnly, 'directory_editable');
  ValidateAssert(WizardForm.DirEdit.Width >= ScaleX(100),
    'directory_edit_width');
  ValidateAssert(WizardForm.DirEdit.Visible and
    WizardForm.DirBrowseButton.Visible and
    WizardForm.DirBrowseButton.Enabled, 'directory_controls_visible');
  ValidateAssert(ValidationWithin(WizardForm.DirEdit,
    WizardForm.SelectDirPage), 'directory_edit_within_page');
  ValidateAssert(ValidationWithin(WizardForm.DirBrowseButton,
    WizardForm.SelectDirPage), 'browse_button_within_page');
  ValidateAssert(ValidationSeparate(WizardForm.DirEdit,
    WizardForm.DirBrowseButton), 'directory_browse_no_overlap');
  ValidateAssert(ValidationWithin(DirectoryInfoPanel,
    WizardForm.SelectDirPage), 'directory_panel_within_page');
  ValidateAssert(ValidationSeparate(DirectoryInfoPanel,
    WizardForm.DirEdit) and ValidationSeparate(DirectoryInfoPanel,
    WizardForm.DirBrowseButton), 'directory_panel_no_overlap');
  ValidateAssert(ValidationWithin(WizardForm.DiskSpaceLabel,
    WizardForm.SelectDirPage), 'disk_space_label_within_page');
  ValidateAssert(ValidationSeparate(DirectoryInfoPanel,
    WizardForm.DiskSpaceLabel), 'directory_panel_disk_space_no_overlap');
  ValidateAssert(ValidationWithin(TaskInfoPanel,
    WizardForm.SelectTasksPage), 'task_panel_within_page');
  ValidateAssert(ValidationWithin(WizardForm.TasksList,
    WizardForm.SelectTasksPage), 'tasks_list_within_page');
  ValidateAssert(ValidationSeparate(TaskInfoPanel,
    WizardForm.TasksList), 'tasks_panel_no_overlap');
  ValidateAssert(WizardForm.TasksList.Visible,
    'tasks_list_visible');
  ValidateAssert(WizardForm.WelcomeLabel1.Visible and
    WizardForm.WelcomeLabel2.Visible and
    (WizardForm.WelcomeLabel1.Width > 0) and
    (WizardForm.WelcomeLabel2.Width > 0), 'welcome_labels_visible');
  ValidateAssert(ValidationWithin(WizardForm.WelcomeLabel1,
    WizardForm.WelcomeLabel1.Parent) and
    ValidationWithin(WizardForm.WelcomeLabel2,
    WizardForm.WelcomeLabel2.Parent), 'welcome_labels_within_page');
  ValidateAssert(ValidationSeparate(WizardForm.WelcomeLabel1,
    WizardForm.WelcomeLabel2), 'welcome_labels_no_overlap');
  ValidateAssert(WizardForm.PageNameLabel.Visible and
    WizardForm.PageDescriptionLabel.Visible, 'page_heading_visible');
  ValidateAssert(StepLabel.Visible and (StepLabel.Width > 0) and
    (StepLabel.Height > 0), 'step_label_visible');
  CurPageChanged(wpSelectDir);
  ValidateAssert(DirectoryInfoPanel.Visible,
    'directory_panel_visible_on_directory_page');
  CurPageChanged(wpSelectTasks);
  ValidateAssert(TaskInfoPanel.Visible,
    'task_panel_visible_on_tasks_page');
  CurPageChanged(wpWelcome);
  ValidateAssert(WizardForm.WelcomeLabel1.Visible and
    WizardForm.WelcomeLabel2.Visible, 'welcome_labels_after_page_change');
  ValidationReport := ValidationReport + 'STATUS=PASS' + #13#10;
  if not SaveStringToFile('__REPORT__', ValidationReport, False) then
    RaiseException('Could not save native wizard validation report');
end;
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside_project(path: Path) -> Path:
    path = path.resolve()
    if not path.is_relative_to(ROOT.resolve()) or path == ROOT.resolve():
        raise ValueError(f"Validation output must be inside the project: {path}")
    return path


def sections(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^\s*\[([^]\r\n]+)\]\s*$", text))
    if not matches:
        raise ValueError("Installer has no sections")
    result = [("preamble", text[:matches[0].start()])]
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result.append((match.group(1).strip().casefold(), text[match.end():end]))
    return result


def setup_values(body: str) -> dict[str, str]:
    result = {}
    for line in body.splitlines():
        if line.strip().startswith((";", "#")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip().casefold()] = value.strip()
    return result


def replace_setup(body: str, overrides: dict[str, str]) -> str:
    pending = dict(overrides)
    lines = []
    for line in body.splitlines():
        key = line.split("=", 1)[0].strip().casefold() if "=" in line else ""
        if key in overrides:
            if key in pending:
                lines.append(f"{key}={pending.pop(key)}")
        else:
            lines.append(line)
    lines.extend(f"{key}={value}" for key, value in pending.items())
    return "\n".join(lines).strip() + "\n"


def prepare(script: Path, output: Path, font_size: int = 9) -> dict:
    script = script.resolve()
    output = inside_project(output)
    text = script.read_text(encoding="utf-8-sig")
    parsed = sections(text)
    mapping = dict(parsed)
    setup = setup_values(mapping.get("setup", ""))
    for directive in ("disabledirpage", "disablewelcomepage"):
        if setup.get(directive, "").casefold() != "no":
            raise ValueError(f"Production {directive} must explicitly be no")
    if setup.get("privilegesrequired", "").casefold() != "lowest":
        raise ValueError("Fixture requires a production per-user installer")
    if "modern" not in setup.get("wizardstyle", "").casefold().split():
        raise ValueError("Production must use modern wizard styling")
    langoptions = setup_values(mapping.get("langoptions", ""))
    if langoptions.get("dialogfontname", "").casefold() != "microsoft yahei ui":
        raise ValueError("Production must set Microsoft YaHei UI as its dialog font")
    if "tasks" not in mapping or not mapping["tasks"].strip():
        raise ValueError("Production tasks must exist to validate the checkbox page")
    code = mapping.get("code", "")
    forbidden_code = r"\b(?:Exec|ShellExec|RegWrite\w*|RegDelete\w*|DeleteFile|DelTree|RemoveDir|CreateDir|SaveStringToFile|external)\b"
    if re.search(forbidden_code, code, re.IGNORECASE):
        raise ValueError("Production Code contains a non-UI operation; fixture refused")
    if re.search(r"(?mi)^\s*#\s*(?:include|expr|emit)\b", text):
        raise ValueError("Fixture refuses executable preprocessor expressions/includes")
    code, count = re.subn(r"(?i)\bprocedure\s+InitializeWizard\b",
                         "procedure InitializeBrandWizard", code)
    if count != 1 or not re.search(r"(?i)\bprocedure\s+CurPageChanged\b", code):
        raise ValueError("Production UI event procedures are not ready")
    for variable in ("DirectoryInfoPanel", "TaskInfoPanel", "StepLabel"):
        if not re.search(rf"\b{variable}\b", code):
            raise ValueError(f"Missing production control {variable}")

    output.mkdir(parents=True, exist_ok=True)
    session = output / str(uuid.uuid4())
    session.mkdir()
    default_dir = session / "default" / "application"
    selected_dir = session / "selected_path"
    native_report = session / "native_report.txt"
    fixture_id = f"RenesasHorseTutor.Validation.{uuid.uuid4()}"
    overrides = {
        "appid": fixture_id,
        "sourcedir": str(script.parent),
        "defaultdirname": str(default_dir),
        "usepreviousappdir": "no",
        "useprevioustasks": "no",
        "uninstallable": "no",
        "createuninstallregkey": "no",
        "closeapplications": "no",
        "restartapplications": "no",
        "outputdir": str(session),
        "outputbasefilename": "native_wizard_fixture",
        "setuplogging": "yes",
        "appmutex": "",
    }
    # Explicit signing directives may run external tools at compile time.
    setup_body = re.sub(r"(?mi)^\s*SignTool\s*=.*$", "", mapping["setup"])
    blocks = [mapping["preamble"].strip()]
    for name, body in parsed[1:]:
        if name in REMOVED_SECTIONS:
            continue
        if name not in ALLOWED_SECTIONS:
            raise ValueError(f"Fixture refuses unsupported section [{name}]")
        if name == "setup":
            body = replace_setup(setup_body, overrides)
        elif name == "files":
            body = 'Source: "安装说明.txt"; DestDir: "{app}"; Flags: ignoreversion\n'
        elif name == "langoptions":
            body = replace_setup(body, {"dialogfontsize": str(font_size)})
        elif name == "code":
            report_literal = str(native_report).replace("'", "''")
            body = ("\nvar\n  ValidationReport: String;\n" + code + "\n" +
                    NATIVE_CHECKS.replace("__REPORT__", report_literal))
        blocks.append(f"[{name}]\n{body.strip()}\n")
    fixture = session / "native_wizard_fixture.iss"
    fixture.write_text("\n\n".join(blocks) + "\n", encoding="utf-8-sig")
    manifest = {
        "production_script": str(script), "production_sha256": sha256(script),
        "fixture_script": str(fixture), "fixture_app_id": fixture_id,
        "session": str(session), "default_directory": str(default_dir),
        "selected_directory": str(selected_dir), "native_report": str(native_report),
        "dummy_source": str(script.parent / "安装说明.txt"),
        "fixture_exe": str(session / "native_wizard_fixture.exe"),
        "setup_log": str(session / "setup.log"),
        "fixture_font_size": font_size,
    }
    return manifest


def run(manifest: dict, compiler: Path, output: Path) -> dict:
    output = inside_project(output)
    session = inside_project(Path(manifest["session"]))
    if not session.is_relative_to(output):
        raise ValueError("Manifest session is outside the validation output")
    for key in ("fixture_script", "default_directory", "selected_directory",
                "native_report", "fixture_exe", "setup_log"):
        if not Path(manifest[key]).resolve().is_relative_to(session):
            raise ValueError(f"Manifest {key} escapes the fixture session")
    script = Path(manifest["production_script"])
    if sha256(script) != manifest["production_sha256"]:
        raise ValueError("Production script changed; prepare a new fixture")
    if not compiler.is_file():
        raise FileNotFoundError(compiler)
    compile_result = subprocess.run([str(compiler), manifest["fixture_script"]],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (session / "compiler.log").write_bytes(compile_result.stdout)
    if compile_result.returncode:
        raise RuntimeError(f"Fixture compilation failed; see {session / 'compiler.log'}")
    command = [manifest["fixture_exe"], "/VERYSILENT", "/SUPPRESSMSGBOXES",
               "/NORESTART", f"/DIR={manifest['selected_directory']}",
               f"/LOG={manifest['setup_log']}"]
    installed = subprocess.run(command, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=90)
    (session / "installer_process.log").write_bytes(installed.stdout)
    native = Path(manifest["native_report"])
    if installed.returncode:
        raise RuntimeError(f"Fixture exited {installed.returncode}; see {manifest['setup_log']}")
    if not native.is_file():
        raise RuntimeError("Fixture did not produce native control validation")
    lines = native.read_bytes().decode("utf-8", errors="replace").splitlines()
    native_values = dict(line.split("=", 1) for line in lines
                         if "=" in line and not line.startswith(("PASS=", "FAIL=")))
    checks = [line[5:] for line in lines if line.startswith("PASS=")]
    failures = [line[5:] for line in lines if line.startswith("FAIL=")]
    if native_values.get("STATUS") != "PASS" or failures or len(checks) < 23:
        raise RuntimeError(f"Native assertions failed/incomplete: {lines}")
    for key in ("FORM_WIDTH", "FORM_HEIGHT", "CLIENT_WIDTH", "CLIENT_HEIGHT",
                "SCALE_X_100", "SCALE_Y_100"):
        if int(native_values.get(key, "0")) <= 0:
            raise RuntimeError(f"Native report has no usable {key}")
    selected = Path(manifest["selected_directory"])
    dummy = selected / "安装说明.txt"
    if not dummy.is_file() or sha256(dummy) != sha256(Path(manifest["dummy_source"])):
        raise RuntimeError("/DIR did not install the dummy at the explicitly selected path")
    if Path(manifest["default_directory"]).exists():
        raise RuntimeError("Installer unexpectedly wrote to its default application path")
    if sorted(path.name for path in selected.iterdir()) != ["安装说明.txt"]:
        raise RuntimeError("Fixture installed unexpected files")
    report = {**manifest, "status": "PASS", "native_geometry": native_values,
              "native_checks": checks, "chosen_directory_honored": True,
              "validation_scope": "native controls and silent /DIR; no UI automation"}
    (session / "report.json").write_text(json.dumps(report, ensure_ascii=False,
                                                    indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, default=ROOT / "installer" / "RenesasHorseTutor.iss")
    parser.add_argument("--compiler", type=Path, default=DEFAULT_COMPILER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path,
                        default=ROOT / "build" / "v16_21_validation" / "installer_report.json")
    parser.add_argument("--font-sizes", default="9,12",
                        help="Comma-separated font metrics to test without changing Windows settings")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare", action="store_true", help="Generate the isolated fixture only")
    mode.add_argument("--run", action="store_true", help="Compile and run the already prepared fixture")
    args = parser.parse_args()
    output = inside_project(args.output)
    if args.run:
        manifests = json.loads((output / "manifest.json").read_text(encoding="utf-8"))["cases"]
    else:
        font_sizes = [int(value) for value in args.font_sizes.split(",")]
        if not font_sizes or any(not 8 <= size <= 16 for size in font_sizes):
            raise ValueError("Validation font sizes must be between 8 and 16")
        manifests = [prepare(args.script, output, size) for size in font_sizes]
        (output / "manifest.json").write_text(json.dumps({"cases": manifests},
            ensure_ascii=False, indent=2), encoding="utf-8")
    if args.prepare:
        for manifest in manifests:
            print(f"FIXTURE_READY={manifest['fixture_script']}")
        return
    reports = [run(manifest, args.compiler.resolve(), output) for manifest in manifests]
    report_path = inside_project(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {"status": "PASS", "cases": reports,
               "validation_scope": "native controls and silent /DIR; no UI automation"}
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("NATIVE_INSTALLER_CHECKS=PASS")
    for report in reports:
        print(f"FONT={report['fixture_font_size']} CHECK_COUNT={len(report['native_checks'])} "
              f"FORM={report['native_geometry']['FORM_WIDTH']}x{report['native_geometry']['FORM_HEIGHT']}")
    print(f"REPORT={report_path}")


if __name__ == "__main__":
    main()
