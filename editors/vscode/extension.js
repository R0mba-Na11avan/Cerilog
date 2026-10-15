// Cerilog VS Code extension.
//
// Runs the Cerilog CLI for everything: `--check` on save for squiggles, and a
// normal compile for the ▶ button. The output target comes from the
// `cerilog.target` setting, which the status bar item switches.

const vscode = require("vscode");
const cp = require("child_process");
const fs = require("fs");
const path = require("path");

const TARGETS = {
  sv: { label: "SystemVerilog (.sv)", short: "SV", ext: ".sv" },
  v: { label: "Verilog-2005 (.v)", short: "V", ext: ".v" },
};

// file:LINE:COL: error|warning: message   (the file part may contain ':' on Windows)
const DIAGNOSTIC_LINE = /^(.*):(\d+):(\d+): (error|warning): (.*)$/;
const HINT_LINE = /^\s+hint: (.*)$/;

let diagnostics;
let statusItem;
let output;
let warnedMissingCli = false;

function config() {
  return vscode.workspace.getConfiguration("cerilog");
}

function currentTarget() {
  const target = config().get("target", "sv");
  return TARGETS[target] ? target : "sv";
}

function isCerilog(doc) {
  return doc && doc.languageId === "cerilog" && doc.uri.scheme === "file";
}

// "python -m cerilog" -> ["python", "-m", "cerilog"]; double quotes group words.
function splitCommand(command) {
  const parts = command.match(/"[^"]*"|\S+/g) || ["cerilog"];
  return parts.map((p) => p.replace(/^"(.*)"$/, "$1"));
}

function runCli(args, cwd) {
  const [exe, ...prefix] = splitCommand(config().get("command", "cerilog"));
  output.appendLine(`> ${exe} ${[...prefix, ...args].join(" ")}`);
  return new Promise((resolve) => {
    cp.execFile(exe, [...prefix, ...args], { cwd }, (err, stdout, stderr) => {
      if (stderr) output.append(stderr);
      if (err && typeof err.code === "string") {
        // Spawn failure (e.g. ENOENT): the CLI isn't installed or not on PATH.
        resolve({ code: -1, stdout, stderr, spawnError: err });
        return;
      }
      resolve({ code: err ? err.code : 0, stdout, stderr });
    });
  });
}

function reportMissingCli(err) {
  output.appendLine(`Could not start the Cerilog CLI: ${err.message}`);
  if (warnedMissingCli) return;
  warnedMissingCli = true;
  vscode.window
    .showErrorMessage(
      "Cerilog: could not run the compiler. Install it (pip install -e .) or set cerilog.command, e.g. \"python -m cerilog\".",
      "Open Settings"
    )
    .then((choice) => {
      if (choice) vscode.commands.executeCommand("workbench.action.openSettings", "cerilog.command");
    });
}

function parseDiagnostics(stderr, doc) {
  const result = [];
  let last = null;
  for (const line of stderr.split(/\r?\n/)) {
    const m = DIAGNOSTIC_LINE.exec(line);
    if (m) {
      const lineNo = Math.max(0, Number(m[2]) - 1);
      const col = Math.max(0, Number(m[3]) - 1);
      const pos = new vscode.Position(lineNo, col);
      const range =
        doc.getWordRangeAtPosition(pos) || new vscode.Range(pos, pos.translate(0, 1));
      const severity =
        m[4] === "error" ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Warning;
      last = new vscode.Diagnostic(range, m[5], severity);
      last.source = "cerilog";
      result.push(last);
      continue;
    }
    const hint = HINT_LINE.exec(line);
    if (hint && last) last.message += `\nhint: ${hint[1]}`;
  }
  return result;
}

async function check(doc) {
  if (!isCerilog(doc)) return;
  const res = await runCli(
    [doc.fileName, "--check", "--target", currentTarget()],
    path.dirname(doc.fileName)
  );
  if (res.spawnError) return reportMissingCli(res.spawnError);
  diagnostics.set(doc.uri, parseDiagnostics(res.stderr, doc));
}

function outputPathFor(doc, target) {
  const file = doc.fileName;
  let dir = path.dirname(file);
  const outDir = config().get("outDir", "").trim();
  if (outDir) {
    if (path.isAbsolute(outDir)) {
      dir = outDir;
    } else {
      const folder = vscode.workspace.getWorkspaceFolder(doc.uri);
      dir = path.join(folder ? folder.uri.fsPath : path.dirname(file), outDir);
    }
  }
  return path.join(dir, path.basename(file, path.extname(file)) + TARGETS[target].ext);
}

async function compile(target) {
  const editor = vscode.window.activeTextEditor;
  const doc = editor && editor.document;
  if (!isCerilog(doc)) {
    vscode.window.showWarningMessage("Cerilog: open a saved .cel file to compile it.");
    return;
  }
  if (doc.isDirty) await doc.save();

  const out = outputPathFor(doc, target);
  fs.mkdirSync(path.dirname(out), { recursive: true });

  const res = await runCli(
    [doc.fileName, "-o", out, "--target", target],
    path.dirname(doc.fileName)
  );
  if (res.spawnError) return reportMissingCli(res.spawnError);
  diagnostics.set(doc.uri, parseDiagnostics(res.stderr, doc));

  if (res.code === 0) {
    const shown = vscode.workspace.asRelativePath(out);
    const choice = await vscode.window.showInformationMessage(`Cerilog: compiled to ${shown}`, "Open");
    if (choice === "Open") {
      vscode.window.showTextDocument(await vscode.workspace.openTextDocument(out), {
        viewColumn: vscode.ViewColumn.Beside,
        preview: true,
      });
    }
  } else {
    vscode.window.showErrorMessage("Cerilog: compile failed. See the Problems panel.");
  }
}

async function selectTarget() {
  const items = Object.entries(TARGETS).map(([value, t]) => ({
    label: t.label,
    value,
    picked: value === currentTarget(),
    description: value === currentTarget() ? "current" : undefined,
  }));
  const choice = await vscode.window.showQuickPick(items, { placeHolder: "Cerilog output target" });
  if (!choice) return;
  const scope = vscode.workspace.workspaceFolders
    ? vscode.ConfigurationTarget.Workspace
    : vscode.ConfigurationTarget.Global;
  await config().update("target", choice.value, scope);
}

function updateStatus() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== "cerilog") {
    statusItem.hide();
    return;
  }
  const t = TARGETS[currentTarget()];
  statusItem.text = `$(circuit-board) Cerilog: ${t.short}`;
  statusItem.tooltip = `Output target: ${t.label}. Click to change.`;
  statusItem.show();
}

function activate(context) {
  diagnostics = vscode.languages.createDiagnosticCollection("cerilog");
  output = vscode.window.createOutputChannel("Cerilog");
  statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusItem.command = "cerilog.selectTarget";

  context.subscriptions.push(
    diagnostics,
    output,
    statusItem,
    vscode.commands.registerCommand("cerilog.compile", () => compile(currentTarget())),
    vscode.commands.registerCommand("cerilog.compileSv", () => compile("sv")),
    vscode.commands.registerCommand("cerilog.compileV", () => compile("v")),
    vscode.commands.registerCommand("cerilog.selectTarget", selectTarget),
    vscode.commands.registerCommand("cerilog.check", () => {
      const editor = vscode.window.activeTextEditor;
      if (editor) check(editor.document);
    }),
    vscode.workspace.onDidSaveTextDocument((doc) => {
      if (config().get("checkOnSave", true)) check(doc);
    }),
    vscode.workspace.onDidOpenTextDocument((doc) => {
      if (config().get("checkOnSave", true)) check(doc);
    }),
    vscode.workspace.onDidCloseTextDocument((doc) => diagnostics.delete(doc.uri)),
    vscode.window.onDidChangeActiveTextEditor(updateStatus),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (!e.affectsConfiguration("cerilog")) return;
      updateStatus();
      // Target-specific errors depend on the target: re-check open files.
      vscode.workspace.textDocuments.forEach((doc) => check(doc));
    })
  );

  updateStatus();
  vscode.workspace.textDocuments.forEach((doc) => check(doc));
}

function deactivate() {}

module.exports = { activate, deactivate };
