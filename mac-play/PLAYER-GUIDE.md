# Play Mu The Matrix on your Mac

This guide shows how to install and play Mu The Matrix on a Mac. It is free: you do not need CrossOver or any
other paid program. You download one file, **Mu The Matrix.dmg**. The **Mu The Matrix** app in it sets everything
up and starts the game. You never need Terminal unless something goes wrong.

> **Speed (October 2026):** the game reaches its maximum of 25 frames per second, also in crowded places such as
> boss areas, in our tests.

---

## Quick start

**Before you start**, check that you have:

- a Mac with an **Apple chip** (M1 or newer). Macs with an Intel processor do not work;
- **macOS 13 Ventura or newer**;
- about **12 GB of free disk space**;
- an **internet connection**: the game download is about 2.2 GB;
- your **Mu The Matrix account**, the same one you use on Windows;
- about **an hour** for the first installation. Most of that time is the game download, and you can keep using
  your Mac meanwhile.

**Steps:**

1. Download **Mu The Matrix.dmg** from the official website and open it. A window appears: drag **Mu The
   Matrix** onto the **Applications** folder next to it.
2. Open **Mu The Matrix** from your Applications folder. The first time, macOS says **"Mu The Matrix.app" Not
   Opened**: click **Done**, then open **Apple menu > System Settings > Privacy & Security**, scroll down to
   **Security**, click **Open Anyway** next to "Mu The Matrix.app" and confirm with Touch ID or your Mac password.
   Click **Open Anyway** again if asked. (Details: [step 3](#3-allow-the-app-to-open-first-time-only).)
3. Click **Install**. Wait until it has finished (about 45 minutes in our test). The game's launcher then opens
   by itself.
4. Click the launcher's big green **START** button, choose a server and log in.

**Next time:** open **Mu The Matrix** and the launcher opens straight away.

If something does not work, see [Troubleshooting](#troubleshooting).

---

## Step by step

### 1. Check your Mac

| What | Requirement | How to check |
|---|---|---|
| Chip | Apple chip (M1, M2, M3, M4, M5 or newer). Intel Macs are not supported. | **Apple menu > About This Mac**. The line **Chip** must start with "Apple". |
| macOS | 13 Ventura or newer. Only macOS 27 has been tested. | Same window, line **macOS**. |
| Free disk space | About 12 GB (about 6 GB if you already have the game files). After installation the game uses about 5 GB. | **Apple menu > System Settings > General > Storage**. |
| Internet | About 2.4 GB is downloaded: the game (2.2 GB) from the official Mu The Matrix server and Microsoft .NET Framework 4.8 from Microsoft. | — |
| Rosetta 2 | Apple's free translator for Intel programs. Many Macs already have it. | You do not need to check. When you click **Install**, the app checks for it and, if it is missing, offers to install it for you (see [Rosetta 2](#if-the-app-asks-for-rosetta-2)). |
| Account | Your Mu The Matrix account. If you do not have one yet, create it on the official Mu The Matrix website. | — |

### 2. Get the app

1. Download **Mu The Matrix.dmg** (about 130 MB) from the official website.
2. Open it (double-click it in your **Downloads** folder). A window titled **Mu The Matrix** appears, with the
   app on the left, the **Applications** folder on the right and the words **Drag Mu The Matrix to
   Applications**.
3. Drag **Mu The Matrix** onto **Applications**.

If you open the app straight from that window (or from Downloads) instead, it asks **Move Mu The Matrix to your
Applications folder?**. Click **Move to Applications**: it copies itself there, opens again from there and
closes the Mu The Matrix disk.

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

The first time Mu The Matrix opens, one window appears: *"Mu The Matrix needs to download the game (about 2.2 GB)
and set itself up. This takes about 45 minutes."*

1. Click **Install**. If Rosetta 2 is missing, the app first offers to install it: see
   [If the app asks for Rosetta 2](#if-the-app-asks-for-rosetta-2).

   If you already have the game files (for example copied from a Windows PC), click **Use a game folder I
   already have…** instead, select the folder that contains **MuTheMatrix.exe** and **main.exe**, and click **Use
   This Folder**. The folder is copied, not moved, and nothing is downloaded for the game.
2. Wait. The window shows what is happening (**Getting ready**, **Installing components from Microsoft**,
   **Downloading the game**, **Installing the game**, **Finishing**, **Checking that everything works**) and one
   progress bar for the whole installation. While the game downloads, the line under the bar shows how much has
   arrived, the speed and the time left, for example **812 MB of 2.18 GB (37%) · 4.2 MB/s · about 5 minutes
   left**. The window title and the app's Dock icon show the percentage.
   - The whole installation took **about 45 minutes** in our test; the game download is most of it and is
     quicker on a fast connection. With your own game folder it takes **about 5 to 10 minutes**.
   - The app keeps your Mac awake while it installs. Keep it plugged in and do not close the lid until the
     installation has finished.
   - If macOS asks whether Mu The Matrix may access a folder, click **Allow**.
3. When it has finished, the window says **Mu The Matrix is ready** and the game's launcher opens by itself.
   Continue with [step 5](#5-play).

**If the installation stops** (for example, because the internet connection dropped), the window says what went
wrong in plain words, for example **A download did not finish**, with two buttons: **Try Again** continues (the
parts that are already done are skipped, and an interrupted download continues where it stopped), and **Show
Details** shows what the installer did, for your server team.

**To stop an installation yourself**, click **Cancel**, then **Stop** (closing the window or quitting the app
asks the same question). After a few seconds the window says **The installation was stopped**. Click **Continue**
when you want to go on: finished steps and the part already downloaded are kept. You do not need to restart your
Mac.

#### If the app asks for Rosetta 2

Rosetta 2 is a free tool from Apple that lets a Mac with an Apple chip run programs made for Intel processors.
Mu The Matrix needs it. Many Macs already have it; if yours does not, a message **"Mu The Matrix needs
Rosetta 2"** appears when you click **Install**.

1. Click **Install Rosetta**.
2. macOS asks for permission in its standard window, with the text *Mu The Matrix wants to install Rosetta 2,
   Apple's free translator for Intel programs*. Type your Mac login password (or use **Touch ID** if the window
   offers it) and click **OK**.
3. Wait a minute or two. The installation then starts by itself.

If you click **Not Now**, or cancel the permission window, the window says **Rosetta 2 is needed first**: click
**Try Again** to be asked again, or install Rosetta in Terminal (see [Troubleshooting](#troubleshooting)).

### 5. Play

1. After the installation the launcher opens by itself; later, open **Mu The Matrix** from Applications (or the
   Dock). A small window says **Starting Mu The Matrix…**, then the app closes. The launcher appears a few seconds
   later; the first time, it can take up to a minute.
2. Wait until the launcher shows the **Server Time** at the top left and **Press GameStart to Play**.
3. Click the big green **START** button at the bottom right. The game window opens after about 20 seconds.
4. Choose a server, type your account name and password, and press **Return**.

Only one copy of the game can run at a time. The Mu The Matrix app never saves or reads your password.

The launcher's **–** button puts the launcher in the Dock (its Dock icon is called **wine**). Click that icon,
or the small launcher picture at the right end of the Dock, to bring the launcher back. While you play,
the launcher stays behind the game window.

**The next times:** open **Mu The Matrix** in Applications (or in the Dock). The launcher opens straight away.
For the settings, hold the **Option (⌥)** key while you open the app, and keep holding it until the window
appears, or choose **Mu The Matrix > Settings…** in the menu bar while the app is open.

---

## The Mu The Matrix window (settings)

Hold **Option (⌥)** while you open the app to see this window, or choose **Mu The Matrix > Settings…** in the
menu bar. You can also open it from the error messages. Most players never need it; some change **Resolution** or
turn on the **FPS counter**.

| Item | What it does | What to choose |
|---|---|---|
| **Runtime** | Technical: what runs the Windows game on your Mac. | Leave it on **Free Wine runtime (recommended, no CrossOver)**. |
| **Game** | Shows **Installed** or **Not installed yet**, with an **Install…** or **Repair…** button. **Repair…** opens a window with a **Repair** button: it fixes missing parts and installs updates, without downloading the game again. | Use **Repair…** after an app update, or if the game stopped starting. |
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
- **The app**: when a new **Mu The Matrix.dmg** is published, do this:
  1. Quit the game and the launcher.
  2. Download the new disk image, open it, and drag **Mu The Matrix** onto **Applications**. Click **Replace**
     when the Finder asks.
  3. Allow it once more, as in [step 3](#3-allow-the-app-to-open-first-time-only). macOS asks again for every
     newly downloaded copy.
  4. Hold **Option (⌥)** while you open the app, click **Repair…**, then click **Repair**. Finished parts are
     skipped and the game is not downloaded again; new parts are installed. Your game settings are kept. Then
     click **Play**.

## Uninstalling

1. Quit the game and the launcher.
2. Drag **Mu The Matrix** from Applications to the Trash.
3. In the Finder, choose **Go > Go to Folder…**, type the path from the table below, press **Return**, and drag
   the folder to the Trash. Do this for each folder.
4. Empty the Trash.

| Folder | What it contains | Size |
|---|---|---|
| `~/Library/Application Support/MuTheMatrix` | The game, what runs it on your Mac, your game and app settings | about 5 GB |
| `~/Library/Logs/MuTheMatrix` | Log files | small |
| `~/.cache/winetricks` | Saved copies of Microsoft's .NET installers (other Wine programs may share it) | a few hundred MB |

The app changes nothing else on your Mac.

---

## Troubleshooting

During the installation, problems appear in the Mu The Matrix window; **Show Details** shows the installer's own
messages. Problems at start-up open a message with the buttons **Settings…**, **Open Log** and **Quit**.

| What you see | What to do |
|---|---|
| **"Mu The Matrix.app" Not Opened** | Do [step 3](#3-allow-the-app-to-open-first-time-only). |
| No **Open Anyway** button in Privacy & Security | Open the app once more, click **Done**, then look again. The button only appears for about an hour after you try to open the app. |
| **"Mu The Matrix" is damaged and can't be opened** | Use the Terminal line under *Advanced* in [step 3](#3-allow-the-app-to-open-first-time-only). |
| **Move Mu The Matrix to your Applications folder?** | Click **Move to Applications**. If it says it could not copy itself, drag **Mu The Matrix** from the disk image into Applications yourself and open it from there. |
| **Mu The Matrix needs Rosetta 2**, or **Rosetta 2 is needed first** / **Rosetta 2 could not be installed** | Click **Install Rosetta** in the message (see [If the app asks for Rosetta 2](#if-the-app-asks-for-rosetta-2)). If that does not work: open **Terminal** (Applications > Utilities), paste `sudo softwareupdate --install-rosetta --agree-to-license` and press **Return**. Type your Mac password when asked (nothing appears while you type) and press **Return**. Wait until it says the install finished, then click **Try Again**. |
| **Not enough free space** (*Not enough free disk space: … GB free, about 12 GB needed.*) | Free up space, then click **Try Again**. |
| **A download did not finish** | Check your internet connection, then click **Try Again**. A download that was cut off continues where it stopped. If the game download fails again and again, the download link may have changed: tell your server team. Meanwhile you can download the game on another computer and use **Use a game folder I already have…**. |
| **The installation could not finish** | Click **Try Again**. If it fails again, click **Show Details** and send what it shows, or the logs (see below), to your server team. If the details say *Setup lock exists*, another installation is still running, for example in a second copy of the app: wait for it to finish or click **Cancel** there (if you are sure none runs, restart your Mac). If they say the game folder *must contain main.exe and MuTheMatrix.exe*, you chose the wrong folder. |
| **This copy of Mu The Matrix is incomplete** | The app you downloaded is not the complete one; the game would run very slowly. Download **Mu The Matrix.dmg** again from the official website, replace the app, then hold Option while opening it and click **Repair…**. |
| **The final check found a problem** | Click **Try Again**; if it happens again, click **Show Details** (the lines starting with **FAIL** say what) and send them to your server team. |
| The install window opens although the game was installed | The game folder is missing or was moved. Click **Install** (or **Use a game folder I already have…**). If it keeps happening, delete the folder `~/Library/Application Support/MuTheMatrix/prefix` and install again. |
| **Mu The Matrix is already running** | The game or the launcher is still open, maybe hidden. Close it (look in the Dock), then open the app again. If you cannot find it, restart your Mac. |
| **The launcher stopped right away** | Close the game and the launcher and open the app again. If it happens again, hold Option while opening the app, click **Repair…** and then **Repair**. |
| **This resolution is not available** | Hold Option while opening the app and set **Resolution** to **Keep launcher setting**. |
| The launcher does not appear | Wait a minute: the first start can be slow. If nothing appears, open the app again. If you get **Mu The Matrix is already running**, restart your Mac. |
| The launcher's news picture stays on top of the game window, or the launcher does not come back when you click it in the Dock | Fixed in the current app. Hold Option while opening the app, click **Repair…** and then **Repair**. |
| An error in the launcher after your Mac was asleep | Close the launcher and the game, then open Mu The Matrix again. Every start resets what runs the game. |
| macOS asks whether "wine" may accept incoming network connections | Click **Allow**. |
| The game is slow | Choose a smaller **Resolution**. Leave **Fast x87** ticked. The game shows at most 25 frames per second by design. |
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

1. **Publish the disk image.** Players download one file, `Mu The Matrix.dmg` (about 130 MB). Put it on the
   official website (for example next to the Windows installer on `dl.muthematrix.com`) and link it from the
   download page. Step 2 needs that link.
2. **Build it with `make player-dmg`.** It needs `EMBED_MUGL=…`, `EMBED_MSCOREE=…`, `EMBED_FAST_X87=…` and
   `EMBED_RUNTIME=…` (see `bundle/README.md`) and refuses to build without them; the runtime must be the tested
   CrossOver 26.3 build (`winecx-26.3.0-mu1.tar.xz`, SHA-256 `c50cb614…`). The app bundles that runtime, so players
   download no runtime and get 25 frames per second; nothing else has to be hosted. The bundled mugl (**v7.7**) is a
   private hotpatch build that contains client-derived bytes; giving it to players is your decision.
3. **The runtime's license.** The bundled Wine runtime is LGPL 2.1 or later. Its license and where its sources are
   (`SOURCES.txt`) ship inside the app (`Contents/Resources/runtime`, shown in the About window). If someone asks
   you for the sources, send them the CrossOver 26.3.0 source archive named there (or keep a copy to hand).
4. **Gatekeeper.** The app is ad-hoc signed. Every player has to do step 3 for every newly downloaded version. An
   Apple Developer ID with notarization (paid, `SIGN_IDENTITY=` and `NOTARY_PROFILE=` of `make player-dmg`) removes
   that step: players then just open the app.
5. **Game installer link.** The installer downloads `https://dl.muthematrix.com/MuTheMatrix-21.1.2.12.exe`.
   If that file is renamed or removed on the server, new installations stop at **Downloading the game** until
   `MUKIT_GAME_INSTALLER_URL` is updated and the disk image is rebuilt.
6. **Rosetta.** On a Mac without Rosetta 2, the app offers to install it (`softwareupdate --install-rosetta`
   through the standard macOS administrator prompt). This was tested with a stubbed check and install only: the
   test Mac already has Rosetta.
7. **Stopping an installation.** **Cancel > Stop** stops the installer's whole process group (downloads,
   winetricks, Wine), then this prefix's wineserver, and removes the setup lock, so **Continue** works at once.
