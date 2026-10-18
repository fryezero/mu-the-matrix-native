//! Local movie loading for the GFx movies (NATIVE-GFX-003).
//!
//! The client's movies load other movies at run time with
//! `MovieClipLoader.loadClip`: base.swf loads `ExternalBase.swf`, the UI
//! loader (`core.MovieLoader`) loads `main`, `Chat`, `ImageData`, ... from the
//! list the game sends with `LoadFrameFiles`, and the item windows load
//! `Icons.swf` (`MUComponent.SetIconFile`) for `loadBitmapFromLib`.  GFx
//! resolves those names through the game's file opener; the installed movies
//! all sit flat in `Data/Interface/GFx`, while the names in the movies carry
//! Windows sub-directories (`frame\main`, `datas\ImageData`).
//!
//! This navigator resolves a relative name against the directory of the root
//! movie (the converted movies), with backslashes as separators, and falls
//! back to the file name alone and to a case-insensitive match (the client
//! runs on a case-insensitive file system).  Everything else behaves like
//! Ruffle's `NullNavigatorBackend`: no network, no sockets, futures run on a
//! local executor that mugfx polls after each player step.

use std::path::{Path, PathBuf};
use std::time::Duration;

use async_channel::{Receiver, Sender};
use ruffle_core::backend::navigator::{
    ErrorResponse, NavigationMethod, NavigatorBackend, NullExecutor, NullSpawner, OwnedFuture, Request,
    SuccessResponse, fetch_path, resolve_url_with_relative_base_path,
};
use ruffle_core::indexmap::IndexMap;
use ruffle_core::loader::Error;
use ruffle_core::socket::{ConnectionState, SocketAction, SocketHandle};
use url::{ParseError, Url};

pub struct MuNavigator {
    spawner: NullSpawner,
    base: PathBuf,
}

impl MuNavigator {
    pub fn new(base: &Path, executor: &NullExecutor) -> Self {
        let base = base.canonicalize().unwrap_or_else(|_| base.to_path_buf());
        Self { spawner: executor.spawner(), base }
    }

    /// The local file a movie-relative name refers to, if it exists.
    pub fn local_file(&self, name: &str) -> Option<PathBuf> {
        local_file(&self.base, name)
    }
}

/// Resolve `name` (as written in a movie) inside `base`: the path with `\`
/// read as `/`, then the file name alone, each also case-insensitively.
pub fn local_file(base: &Path, name: &str) -> Option<PathBuf> {
    if name.contains("://") {
        return None;
    }
    let name = name.split(['?', '#']).next().unwrap_or(name).replace('\\', "/");
    let trimmed = name.trim_start_matches("./");
    let mut candidates = vec![trimmed.to_string()];
    if let Some(file) = trimmed.rsplit('/').next() {
        if file != trimmed {
            candidates.push(file.to_string());
        }
    }
    for candidate in &candidates {
        let path = base.join(candidate);
        if path.is_file() {
            return Some(path);
        }
        // Case-insensitive match of the last component in its directory.
        let (dir, file) = match candidate.rsplit_once('/') {
            Some((d, f)) => (base.join(d), f.to_string()),
            None => (base.to_path_buf(), candidate.clone()),
        };
        if let Ok(entries) = std::fs::read_dir(&dir) {
            for entry in entries.flatten() {
                if entry.file_name().to_string_lossy().eq_ignore_ascii_case(&file) && entry.path().is_file() {
                    return Some(entry.path());
                }
            }
        }
    }
    None
}

impl NavigatorBackend for MuNavigator {
    fn navigate_to_url(&self, _url: &str, _target: &str, _vars: Option<(NavigationMethod, IndexMap<String, String>)>) {
    }

    fn fetch(&self, request: Request) -> OwnedFuture<Box<dyn SuccessResponse>, ErrorResponse> {
        fetch_path(self, "MuNavigator", request.url(), None)
    }

    fn resolve_url(&self, url: &str) -> Result<Url, ParseError> {
        if let Some(path) = self.local_file(url) {
            if let Ok(u) = Url::from_file_path(&path) {
                return Ok(u);
            }
        }
        resolve_url_with_relative_base_path(self, self.base.clone(), &url.replace('\\', "/"))
    }

    fn spawn_future(&mut self, future: OwnedFuture<(), Error>) {
        self.spawner.spawn_local(future);
    }

    fn pre_process_url(&self, url: Url) -> Url {
        url
    }

    fn connect_socket(
        &mut self,
        _host: String,
        _port: u16,
        _timeout: Duration,
        handle: SocketHandle,
        _receiver: Receiver<Vec<u8>>,
        sender: Sender<SocketAction>,
    ) {
        let _ = sender.try_send(SocketAction::Connect(handle, ConnectionState::Failed));
    }
}
