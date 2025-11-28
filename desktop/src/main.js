import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import "@xterm/xterm/css/xterm.css";

// Initialize terminal
const terminal = new Terminal({
  cursorBlink: true,
  fontSize: 14,
  fontFamily: 'Menlo, Monaco, "Courier New", monospace',
  theme: {
    background: "#1e1e1e",
    foreground: "#d4d4d4",
    cursor: "#d4d4d4",
    cursorAccent: "#1e1e1e",
    black: "#1e1e1e",
    red: "#f44747",
    green: "#6a9955",
    yellow: "#dcdcaa",
    blue: "#569cd6",
    magenta: "#c586c0",
    cyan: "#4ec9b0",
    white: "#d4d4d4",
    brightBlack: "#808080",
    brightRed: "#f44747",
    brightGreen: "#6a9955",
    brightYellow: "#dcdcaa",
    brightBlue: "#569cd6",
    brightMagenta: "#c586c0",
    brightCyan: "#4ec9b0",
    brightWhite: "#ffffff",
  },
});

const fitAddon = new FitAddon();
terminal.loadAddon(fitAddon);

// Mount terminal to DOM
const terminalElement = document.getElementById("terminal");
terminal.open(terminalElement);
fitAddon.fit();

// Handle window resize
window.addEventListener("resize", () => {
  fitAddon.fit();
  const { cols, rows } = terminal;
  invoke("resize_pty", { cols, rows }).catch(console.error);
});

// Send initial size and spawn PTY
async function init() {
  const { cols, rows } = terminal;

  // Listen for PTY output
  await listen("pty-output", (event) => {
    terminal.write(event.payload);
  });

  // Listen for PTY exit
  await listen("pty-exit", (event) => {
    terminal.write(`\r\n[Process exited with code ${event.payload}]\r\n`);
  });

  // Spawn the PTY with initial size
  await invoke("spawn_pty", { cols, rows });
}

// Send user input to PTY
terminal.onData((data) => {
  invoke("write_pty", { data }).catch(console.error);
});

// Start
init().catch((err) => {
  terminal.write(`Error: ${err}\r\n`);
  console.error(err);
});
