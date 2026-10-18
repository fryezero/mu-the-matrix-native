# Play Mu The Matrix on your Mac

This guide shows how to install and play Mu The Matrix on a Mac. It is free: you do not need CrossOver or any
other paid program. The **Mu The Matrix** app sets everything up for you. You only use Terminal if something
goes wrong.

> **Speed today (October 2026):** in quiet places the game reaches its maximum of 25 frames per second. In
> crowded places, such as boss areas, expect about 15. A faster version of the free Windows layer (25 frames
> per second everywhere in our tests) comes once the server team publishes it. You then get it through
> [Updating](#updating). If your server team already gave you the file, see
> [Using a faster Windows layer file](#using-a-faster-windows-layer-file).

---

## Quick start

**Before you start**, check that you have:

- a Mac with an **Apple chip** (M1 or newer). Macs with an Intel processor do not work;
- **macOS 13 Ventura or newer**;
- about **12 GB of free disk space**;
- an **internet connection**: about 2.6 GB is downloaded;
- your **Mu The Matrix account**, the same one you use on Windows;
- about **an hour** for the first installation. Most of that time is the game download, and you can keep using
  your Mac while it runs.

**Steps:**

1. Download **Mu The Matrix.zip** from your server team's link. Open it, then drag **Mu The Matrix** into your
   **Applications** folder.
2. Double-click **Mu The Matrix** in Applications. A message says **"Mu The Matrix.app" Not Opened**. Click
   **Done**.
3. Open **Apple menu > System Settings > Privacy & Security**. Scroll down to **Security**, click **Open
   Anyway** next to "Mu The Matrix.app", and confirm with Touch ID or your Mac password. If another message
   appears, click **Open Anyway** again.
4. The **Install Mu The Matrix** window opens. Keep **Download the game from the official site** selected and
   click **Install**. Wait until it says **"Done. Mu The Matrix is installed."** (about 45 minutes in our test),
   then click **Close**.
5. Click **Play**. The game's launcher opens. Click **GAME START**, choose a server, and log in.

**Next time:** double-click **Mu The Matrix** and the launcher opens straight away. To get the settings window
back, hold the **Option (⌥)** key while you open the app.

If something does not work, see [Troubleshooting](#troubleshooting).

---

## Step by step

### 1. Check your Mac

| What | Requirement | How to check |
|---|---|---|
| Chip | Apple chip (M1, M2, M3, M4, M5 or newer). Intel Macs are not supported. | **Apple menu > About This Mac**. The line **Chip** must start with "Apple". |
| macOS | 13 Ventura or newer. Only macOS 27 has been tested. | Same window, line **macOS**. |
| Free disk space | About 12 GB (about 6 GB if you already have the game files). After installation the game uses about 5 GB. | **Apple menu > System Settings > General > Storage**. |
| Internet | About 2.6 GB is downloaded: the game (2.2 GB) from the official Mu The Matrix server, the free Windows layer ("Wine") from GitHub, and Microsoft .NET Framework 4.8 from Microsoft. | — |
| Rosetta 2 | Apple's free translator for Intel programs. Many Macs already have it. | You do not need to check. When you click **Install**, the app checks for it and, if it is missing, offers to install it for you (see [Rosetta 2](#if-the-app-asks-for-rosetta-2)). |
| Account | Your Mu The Matrix account. If you do not have one yet, create it on the official Mu The Matrix website. | — |

### 2. Get the app

1. Download **Mu The Matrix.zip** from the link your server team gives you (website or Discord).
2. Open your **Downloads** folder and double-click **Mu The Matrix.zip**. The **Mu The Matrix** app appears next
   to it. Safari may already have unzipped the file for you; in that case you will see the app straight away.
3. Drag **Mu The Matrix** into your **Applications** folder. Do this *before* you open it for the first time.

### 3. Allow the app to open (first time only)

The app is not registered with Apple, so macOS asks you to confirm it once. This is normal for free apps from
outside the App Store.

1. Open your **Applications** folder and double-click **Mu The Matrix**.
2. A message appears: **"Mu The Matrix.app" Not Opened**. Under it, it says: *Apple could not verify "Mu The
   Matrix.app" is free of malware that may harm your Mac or compromise your privacy.* It has two buttons:
   **Move to Trash** and **Done**. Click **Done**. Do not click "Move to Trash".
3. Open **Apple menu > System Settings…**, then click **Privacy & Security** in the sidebar.
4. Scroll down the right side to the heading **Security**. Under the line **Allow applications from**, there is
   now a line saying that **"Mu The Matrix.app"** was blocked, with an **Open Anyway** button. Click **Open
   Anyway**.
5. macOS asks you to confirm. Use **Touch ID**, or type your **Mac login password** and click **OK**. If a
   message asks again whether you want to open "Mu The Matrix.app", click **Open Anyway**.

From now on, Mu The Matrix opens with a normal double-click.

- The **Open Anyway** button only appears after you have tried to open the app (step 1), and only for about an
  hour. If you do not see it, do steps 1 and 2 again, then look again.
- **On macOS 13 or 14**, the steps above also work. There is also a shorter way: hold **Control**, click
  **Mu The Matrix**, choose **Open**, then click **Open** in the message.

<details>
<summary>Advanced: do the same with Terminal</summary>

If the steps above do not work, or if macOS says the app "is damaged and can't be opened", open **Terminal**
(in **Applications > Utilities**). Copy the line below, paste it into Terminal, press **Return**, then close
Terminal:

```
xattr -dr com.apple.quarantine "/Applications/Mu The Matrix.app"
```

Nothing is printed when it works. Then double-click Mu The Matrix as usual.
</details>

### 4. Install the game

The first time Mu The Matrix opens, two windows appear. The **Install Mu The Matrix** window is in front, and
the **Mu The Matrix** settings window is behind it.

1. Choose where the game comes from:
   - **Download the game from the official site (about 2.2 GB)**. This is selected already and is the right
     choice for most players.
   - **Use a Mu The Matrix folder I already have…**, if you already have the game files, for example copied
     from a Windows PC. In the window that opens, select the folder that contains **MuTheMatrix.exe** and
     **main.exe**, and click **Open**. The folder is copied, not moved.
2. Click **Install**. If Rosetta 2 is missing, the app first offers to install it: see
   [If the app asks for Rosetta 2](#if-the-app-asks-for-rosetta-2).
3. Wait. The line above the progress bar shows the current step, for example **Step 7 of 14: game files**.
   While something downloads, the line under the bar shows how much has arrived, the speed and the time left,
   for example **Downloading MuTheMatrix-21.1.2.12.exe: 812 MB of 2.18 GB (37%) · 4.2 MB/s · about 5 minutes
   left**. The window title and the app's Dock icon show the overall percentage. The box below lists what the
   installer is doing.
   - The whole installation took **about 45 minutes** in our test. The game download alone took 35 minutes; it
     is quicker on a fast connection. With your own game folder, it takes **about 5 to 10 minutes**.
   - The two long steps are **Step 5 of 14: Microsoft .NET Framework 4.8** (about 4 minutes; Microsoft's
     installer is downloaded from Microsoft) and **Step 7 of 14: game files** (the 2.2 GB download, then about 2
     to 4 minutes to install).
   - Lines that start with **WARNING** are normal; only an **Error:** line stops the installation.
   - The app keeps your Mac awake while it installs. Keep it plugged in and do not close the lid until the
     installation has finished.
   - If macOS asks whether Mu The Matrix may access a folder, click **Allow**.
4. When the window says **"Done. Mu The Matrix is installed. Close this window and press Play."**, click
   **Close**.

**If the installation stops** (for example, because the internet connection dropped), the line above the
progress bar says **"The installation stopped:"** followed by the reason, for example *"The installation
stopped: game installer download failed: …"*. Find the reason in [Troubleshooting](#troubleshooting). Then click
**Try Again**. The installer skips the parts that are already done, and an interrupted download continues where
it stopped.

**To stop an installation yourself**, click **Cancel**, then **Stop** (closing the window or quitting the app
asks the same question). The window shows **"Stopping the installation…"** for a few seconds while the app ends
everything the installer started, downloads included, and then **"The installation was stopped."** Click **Try
Again** when you want to continue: finished steps and the part already downloaded are kept. You do not need to
restart your Mac.

#### If the app asks for Rosetta 2

Rosetta 2 is a free tool from Apple that lets a Mac with an Apple chip run programs made for Intel processors.
The game's Windows layer needs it. Many Macs already have it; if yours does not, a message **"Mu The Matrix needs
Rosetta 2"** appears when you click **Install**.

1. Click **Install Rosetta**.
2. macOS asks for permission in its standard window, with the text *Mu The Matrix wants to install Rosetta 2,
   Apple's free translator for Intel programs*. Type your Mac login password (or use **Touch ID** if the window
   offers it) and click **OK**.
3. Wait a minute or two. The installation then starts by itself.

If you click **Not Now**, or cancel the permission window, the Install window explains how to install Rosetta in
Terminal instead (see [Troubleshooting](#troubleshooting)). Then click **Try Again**.

### 5. Play

1. In the **Mu The Matrix** window, click **Play**. A small window says **Starting the launcher…**, then the app
   closes. The Mu The Matrix launcher appears a few seconds later; the first time, it can take up to a minute.
2. Wait until the launcher shows the **server time** and **Press GameStart to Play**.
3. Click **GAME START**. The game window opens after about 20 seconds.
4. Choose a server, type your account name and password, and press **Return**.

Only one copy of the game can run at a time. The Mu The Matrix app never saves or reads your password.

The launcher's **–** button puts the launcher in the Dock (its Dock icon is called **wine**). Click that icon,
or the small launcher picture at the right end of the Dock, to bring the launcher back. While you play,
the launcher stays behind the game window.

**The next times:** double-click **Mu The Matrix** in Applications (or in the Dock). The launcher opens
straight away, without the settings window. To see the settings window again, hold the **Option (⌥)** key
while you open the app, and keep holding it until the window appears.

---

## The Mu The Matrix window (settings)

Hold **Option (⌥)** while you open the app to see this window. You can also open it from the error messages.
Most players only ever change **Resolution**.

| Item | What it does | What to choose |
|---|---|---|
| **Runtime** | Which Windows layer runs the game. | Leave it on **Free Wine runtime (recommended, no CrossOver)**. |
| **Game** | Shows **Installed** or **Not installed yet**, with an **Install…** or **Repair…** button. **Repair…** runs the installer again: it fixes missing parts and installs updates, without downloading the game again. | Use **Repair…** after an app update, or if the game stopped starting. |
| **Resolution** | The size of the game window. | See [Choosing the window size](#choosing-the-window-size). |
| **Fast x87** | A speed-up for the game's 3D maths. It is used when your installation supports it; otherwise it changes nothing. | Leave it ticked. |
| **FPS counter** | Shows the frames per second in the top-left corner of the game. | Tick it if you want to see it. See [The FPS counter](#the-fps-counter). |
| **Start the game right away when the app opens** | When this is ticked, double-clicking the app starts the launcher directly. | Untick it if you want to see this window every time. |
| **Open Log** | Shows the app's log file in the Finder. | Use it when your server team asks for the log. |
| **Save** / **Play** | **Save** stores your choices and checks them. **Play** stores them and starts the launcher. | — |

## Choosing the window size

The installer picks the largest window size that fits your screen. To change it, use either of these:

- Hold **Option (⌥)** while you open the app, choose a size in **Resolution**, then click **Play**. Your choice is
  applied every time the game starts. Choose **Keep launcher setting** to stop that.
- In the launcher, click **Settings** and choose a size there. This only lasts if the app's **Resolution** is set
  to **Keep launcher setting**, which is the default.

The list offers the sizes that fit your screen, plus the three smallest ones.

## The FPS counter

The game can show how smoothly it runs: a small box in the top-left corner with the frames per second (FPS) and
the time per frame, for example **25.0 FPS 40.0 MS**. 25 FPS is the game's maximum. The number is green from 24
FPS, yellow from 15 and red below 15.

To turn it on or off, open the **Mu The Matrix** app (hold **Option (⌥)** while you open it if it starts the game
right away) and tick or untick **FPS counter**. This also works while you are playing: open the app, change the
tick, and the game shows or hides the counter within a second.

Your choice is kept for the next time you play. The counter is off until you turn it on.

## Updating

- **The game** updates itself: the launcher downloads game updates when it starts, as on Windows.
- **The app**: when your server team publishes a new **Mu The Matrix.zip**, do this:
  1. Quit the game and the launcher.
  2. Download the new zip, open it, and drag the new **Mu The Matrix** into Applications. Click **Replace** when
     the Finder asks.
  3. Allow it once more, as in [step 3](#3-allow-the-app-to-open-first-time-only). macOS asks again for every
     newly downloaded copy.
  4. Hold **Option (⌥)** while you open the app, click **Repair…**, then click **Install**. Finished parts are
     skipped and the game is not downloaded again; new parts, such as a faster Windows layer, are installed.
     Your game settings are kept.

## Using a faster Windows layer file

Your server team may give you a file named **winecx-26.3.0-mu1.tar.xz** (about 130 MB). It is a faster version
of the free Windows layer: crowded places reach 25 frames per second instead of about 15.

1. Quit the game and the launcher.
2. Open the app. In the menu bar, click **Mu The Matrix** > **Use Windows Layer File…**.
3. Choose the file (it is usually in your Downloads folder) and click **Open**.
4. Click **Install**. If the game is already installed, this takes about a minute: only the Windows layer
   changes; the game and your settings stay.

You can also tick **Use a faster Windows layer file I already have…** in the Install window when you install
the game for the first time.

Later repairs keep using the faster layer. If the app says **This Windows layer file is not the one Mu The
Matrix was tested with**, the file is damaged or a different version: click **Cancel** and ask your server team
for the file again.

## Uninstalling

1. Quit the game and the launcher.
2. Drag **Mu The Matrix** from Applications to the Trash.
3. In the Finder, choose **Go > Go to Folder…**, type the path from the table below, press **Return**, and drag
   the folder to the Trash. Do this for each folder.
4. Empty the Trash.

| Folder | What it contains | Size |
|---|---|---|
| `~/Library/Application Support/MuTheMatrix` | The game, the free Windows layer, your game and app settings | about 5 GB |
| `~/Library/Logs/MuTheMatrix` | Log files | small |
| `~/.cache/winetricks` | Saved copies of Microsoft's .NET installers (other Wine programs may share it) | a few hundred MB |

The app changes nothing else on your Mac.

---

## Troubleshooting

The installer's messages appear in the box in the **Install Mu The Matrix** window. Problems at start-up open a
message with the buttons **Settings…**, **Open Log** and **Quit** (and sometimes **Install…**).

| What you see | What to do |
|---|---|
| **"Mu The Matrix.app" Not Opened** | Do [step 3](#3-allow-the-app-to-open-first-time-only). |
| No **Open Anyway** button in Privacy & Security | Open the app once more, click **Done**, then look again. The button only appears for about an hour after you try to open the app. |
| **"Mu The Matrix" is damaged and can't be opened** | Use the Terminal line under *Advanced* in [step 3](#3-allow-the-app-to-open-first-time-only). |
| **Mu The Matrix needs Rosetta 2**, or **Rosetta 2 is needed before the installation can start.** / **Rosetta 2 could not be installed.** | Click **Install Rosetta** in the message (see [If the app asks for Rosetta 2](#if-the-app-asks-for-rosetta-2)). If that does not work: open **Terminal** (Applications > Utilities), paste `sudo softwareupdate --install-rosetta --agree-to-license` and press **Return**. Type your Mac password when asked (nothing appears while you type) and press **Return**. Wait until it says the install finished, then click **Try Again**. |
| **Error: Not enough free disk space: … GB free, about 12 GB needed.** | Free up space, then click **Try Again**. |
| **Error: … download failed** (runtime, runtime library, winetricks or game installer) | Check your internet connection, then click **Try Again**. A download that was cut off continues where it stopped. If the *game installer* download fails again and again, the download link may have changed: tell your server team. Meanwhile you can download the game on another computer and use **Use a Mu The Matrix folder I already have…**. |
| **Error: winetricks dotnet48 failed** | Click **Try Again**. If it fails again, send the logs (see below). |
| **Error: Setup lock exists: …** | Another installation is still running, for example in a second copy of the app. Wait for it to finish or click **Cancel** there. A lock left by an installation that was stopped is removed automatically, so this message only stays if an installation really runs. If you are sure none does, restart your Mac and try again. If the message says *"left by an older version"*, delete the folder named in the message (in Finder, press **Shift-Command-.** to show hidden folders) and try again. |
| **Error: The game folder (--game-dir) must contain main.exe and MuTheMatrix.exe** | You chose the wrong folder. Choose the folder that contains both files. |
| **This copy of Mu The Matrix is incomplete** (when you click Install), or **The game was installed, but this copy of Mu The Matrix is incomplete.** | The app you downloaded was built without the files that make the game fast; the game would run at about 4 frames per second. Tell your server team and download **Mu The Matrix.zip** again. After replacing the app, hold Option while opening it and click **Repair…**. |
| **The installation finished, but the final check found a problem.** | The lines starting with **FAIL** in the box say what. Click **Try Again**; if it happens again, send the logs to your server team. |
| **Mu The Matrix is not installed yet** (when you click Play) | Click **Install…** in that message, or hold Option while opening the app and click **Install…**. |
| **The game folder is missing or damaged** | Click **Install…**. If the message says *"is not a 32-bit prefix"*, delete the folder `~/Library/Application Support/MuTheMatrix/prefix` first, then install again. |
| **Mu The Matrix is already running** | The game or the launcher is still open, maybe hidden. Close it (look in the Dock), then open the app again. If you cannot find it, restart your Mac. |
| **The launcher stopped right away** | Close the game and the launcher and open the app again. If it happens again, hold Option while opening the app, click **Repair…** and then **Install**. |
| **This resolution is not available** | Hold Option while opening the app and set **Resolution** to **Keep launcher setting**. |
| The launcher does not appear | Wait a minute: the first start can be slow. If nothing appears, open the app again. If you get **Mu The Matrix is already running**, restart your Mac. |
| The launcher's news picture stays on top of the game window, or the launcher does not come back when you click it in the Dock | Fixed in the current app. Hold Option while opening the app, click **Repair…** and then **Install**: this installs the updated launcher helper (`mscoree.dll`). |
| An error in the launcher after your Mac was asleep | Close the launcher and the game, then open Mu The Matrix again. Every start resets the game's Windows layer. |
| macOS asks whether "wine" may accept incoming network connections | Click **Allow**. |
| The game is slow | Choose a smaller **Resolution**. Leave **Fast x87** ticked. The game shows at most 25 frames per second by design; see the speed note at the top. |
| The game window does not fit on the screen | Choose a smaller [resolution](#choosing-the-window-size). |
| Anything else | Send the logs to your server team. |

**Sending the logs:** hold Option while you open the app and click **Open Log**. A Finder window opens with
**app.log** selected. Send that file, plus **wine-prefix.log** from the same folder
(`~/Library/Logs/MuTheMatrix`). For installation problems, also send the files in
`~/Library/Application Support/MuTheMatrix/prefix/.mukit` that end in **.log**. The logs do not contain your
password.

---

## How this guide was tested

On 2026-10-18, on a Mac with an M5 chip and macOS 27.0.1:

- The installation was run from scratch twice: from the app's Install window with an existing game folder
  (about 5 minutes), and with the official download (about 45 minutes in total, 35 of them for the 2.2 GB
  download). Afterwards the game was started from the app, the account logged in, and the character entered the
  world.
- Step 3 was checked up to the **"Not Opened"** message, and the **Security** section of Privacy & Security
  was viewed. The **Open Anyway** button there was not clicked in this test; it is the standard way macOS
  offers for apps that are not registered with Apple. The Terminal line under *Advanced* was used successfully.
- The app's own checks (`--check`, `--dry-run`, `--status`, `--install-dry-run`) were run against an empty folder.
- Cancel (MAC-APP-002) was tested with the app's command-line install, which uses the same code as the Install
  window, in an empty scratch folder: stopped three times during the Wine runtime download. Each time no process
  was left, the lock was gone and the next run continued the download. Cancel during a Wine step, the Rosetta
  install and the "incomplete app" messages were tested with stand-ins only.

---

## Notes for the server team (remove this section before publishing)

These points decide what players actually get. Check them before you share the link.

1. **Publish the zip.** No public download exists yet. Step 2 needs a real link.
2. **Build the player app with `make player-app`.** It needs `EMBED_MUGL=…`, `EMBED_MSCOREE=…` and
   `EMBED_FAST_X87=…` (see `bundle/README.md`) and refuses to build without them. A plain `make` builds a
   development app without them: on a player's Mac (no MinGW) it installs without mugl and the mscoree proxy,
   the game runs at about 4 frames per second, the window size is capped at 1280×800 and the final check fails.
   Such an app warns the player before installing ("This copy of Mu The Matrix is incomplete"). The rehearsed
   build bundled mugl **v7.6**, a private hotpatch build that contains client-derived bytes; giving it to
   players is your decision. With the public batching-only mugl, larger window sizes are not offered in the game
   (DevModeIndex capped at 2).
3. **Host the faster runtime.** `MUKIT_RT_ARCHIVE_URL` in `installer/lib/mukit.sh` is still empty. Until the
   CrossOver 26.3 Wine archive is hosted and its URL and SHA-256 are set, players get the CrossOver 24.0.7
   fallback. It is about 20% slower, and fast x87 does not work with it. During installation the log shows
   "fast x87 installed, but runtime cx24.0.7-7 has no inner loader". The speed note at the top of this guide
   describes that state. Once the archive is hosted, rebuild the app and update the note; existing players get
   the faster runtime with **Repair…**. Until then you can hand players the archive itself: **Use Windows Layer
   File…** installs it (see [Using a faster Windows layer file](#using-a-faster-windows-layer-file)); the app
   warns when a file does not match the tested SHA-256 (`RuntimeFile.testedSHA256` in `bundle/Sources/Core.swift`).
4. **Gatekeeper.** The app is ad-hoc signed. Every player has to do step 3 for every newly downloaded version.
   An Apple Developer ID with notarization (paid) would remove that step.
5. **Game installer link.** The installer downloads `https://dl.muthematrix.com/MuTheMatrix-21.1.2.12.exe`.
   If that file is renamed or removed on the server, new installations fail at step 7 until `MUKIT_GAME_INSTALLER_URL`
   is updated and the app is rebuilt.
6. **Rosetta.** On a Mac without Rosetta 2, the app offers to install it (`softwareupdate --install-rosetta`
   through the standard macOS administrator prompt). This was tested with a stubbed check and install only: the
   test Mac already has Rosetta.
7. **Stopping an installation.** **Cancel > Stop** stops the installer's whole process group (downloads,
   winetricks, Wine), then this prefix's wineserver, and removes the setup lock, so **Try Again** works at once.
