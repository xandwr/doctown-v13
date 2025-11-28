// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use portable_pty::{native_pty_system, CommandBuilder, PtySize};
use std::io::{Read, Write};
use std::sync::{Arc, Mutex};
use std::thread;
use tauri::{AppHandle, Emitter, State};

struct PtyState {
    writer: Arc<Mutex<Option<Box<dyn Write + Send>>>>,
    master: Arc<Mutex<Option<Box<dyn portable_pty::MasterPty + Send>>>>,
}

#[tauri::command]
fn spawn_pty(cols: u16, rows: u16, app: AppHandle, state: State<PtyState>) -> Result<(), String> {
    let pty_system = native_pty_system();

    let pair = pty_system
        .openpty(PtySize {
            rows,
            cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .map_err(|e| e.to_string())?;

    // Build the command to run docpack deck
    // Use uv run to work with the local project without needing global install
    let mut cmd = CommandBuilder::new("uv");
    cmd.args(["run", "docpack", "deck"]);

    // Set working directory to the project root (parent of desktop/)
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()));

    // In dev mode, exe is in desktop/src-tauri/target/debug
    // We need to go up to the project root
    if let Some(dir) = exe_dir {
        // Try to find pyproject.toml by walking up
        let mut search_dir = dir.as_path();
        for _ in 0..10 {
            let pyproject = search_dir.join("pyproject.toml");
            if pyproject.exists() {
                cmd.cwd(search_dir);
                break;
            }
            if let Some(parent) = search_dir.parent() {
                search_dir = parent;
            } else {
                break;
            }
        }
    }

    // Spawn the command in the PTY
    let mut child = pair.slave.spawn_command(cmd).map_err(|e| e.to_string())?;

    // Get reader from master before moving it
    let mut reader = pair.master.try_clone_reader().map_err(|e| e.to_string())?;

    // Store the writer for sending input
    let writer = pair.master.take_writer().map_err(|e| e.to_string())?;
    *state.writer.lock().unwrap() = Some(writer);

    // Store the master for resize operations
    *state.master.lock().unwrap() = Some(pair.master);

    // Spawn a thread to read PTY output and send to frontend
    let app_handle = app.clone();

    thread::spawn(move || {
        let mut buf = [0u8; 4096];
        loop {
            match reader.read(&mut buf) {
                Ok(0) => break, // EOF
                Ok(n) => {
                    let data = String::from_utf8_lossy(&buf[..n]).to_string();
                    let _ = app_handle.emit("pty-output", data);
                }
                Err(_) => break,
            }
        }
    });

    // Spawn a thread to wait for child exit
    let app_handle = app.clone();
    thread::spawn(move || {
        if let Ok(status) = child.wait() {
            let code = status.exit_code();
            let _ = app_handle.emit("pty-exit", code);
        }
    });

    Ok(())
}

#[tauri::command]
fn write_pty(data: String, state: State<PtyState>) -> Result<(), String> {
    if let Some(ref mut writer) = *state.writer.lock().unwrap() {
        writer
            .write_all(data.as_bytes())
            .map_err(|e| e.to_string())?;
        writer.flush().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn resize_pty(cols: u16, rows: u16, state: State<PtyState>) -> Result<(), String> {
    if let Some(ref master) = *state.master.lock().unwrap() {
        master
            .resize(PtySize {
                rows,
                cols,
                pixel_width: 0,
                pixel_height: 0,
            })
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(PtyState {
            writer: Arc::new(Mutex::new(None)),
            master: Arc::new(Mutex::new(None)),
        })
        .invoke_handler(tauri::generate_handler![spawn_pty, write_pty, resize_pty])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
