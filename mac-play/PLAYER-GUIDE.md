# Play Mu The Matrix on your Mac

This guide shows you how to install and play Mu The Matrix on a Mac. It is free: you do not need CrossOver or
any other paid program. You need about 15 minutes of your time, plus the time the game takes to download.

## What you need

- A Mac with an Apple chip (M1, M2, M3, M4, M5 or newer). To check: Apple menu  > **About This Mac**. The line
  "Chip" must say "Apple". Macs with an Intel processor are not supported.
- macOS 13 Ventura or newer. This guide was tested on macOS 27.
- About **12 GB of free disk space**. To check: Apple menu  > **System Settings** > **General** > **Storage**.
- An internet connection. The game download is about 2.2 GB.
- Your Mu The Matrix account (the same as on Windows).

## Step 1: Get the app

1. Download **Mu The Matrix.zip** from the link your server team gives you (website or Discord).
2. Open your **Downloads** folder and double-click **Mu The Matrix.zip**. A **Mu The Matrix** app appears.
3. Drag **Mu The Matrix** into your **Applications** folder.

## Step 2: Allow the app to open (only the first time)

The app is not registered with Apple, so the first time you open it your Mac asks you to confirm.

1. Open your **Applications** folder and double-click **Mu The Matrix**.
2. A message says **"Mu The Matrix.app" Not Opened**. Click **Done**. Do not click "Move to Trash".
3. Open Apple menu  > **System Settings** > **Privacy & Security**.
4. Scroll down to **Security**. Next to the line about "Mu The Matrix.app", click **Open Anyway**.
5. Enter your Mac password (or use Touch ID). If another message appears, click **Open Anyway** again.

From now on, Mu The Matrix opens with a normal double-click.

If you prefer, you can do the same in one step with the **Terminal** app (in Applications > Utilities). Copy
this line, paste it into Terminal, press Return and close Terminal:

```
xattr -dr com.apple.quarantine "/Applications/Mu The Matrix.app"
```

## Step 3: Install the game

The first time Mu The Matrix opens, the **Install Mu The Matrix** window appears.

1. Choose where the game comes from:
   - **Download the game from the official site** (recommended), or
   - **Use a Mu The Matrix folder I already have…** if you already have the game files, for example copied from a
     Windows PC. Select the folder that contains **MuTheMatrix.exe**. It is copied, not moved.
2. Click **Install**.
3. Wait. The window shows each step (there are 14) and a progress bar. You can keep using your Mac.
   - In our test the whole installation took about **45 minutes**; 35 of them were the game download.
     With a faster connection, or with your own game folder, it takes about **5 to 10 minutes**.
   - During the installation, Microsoft .NET Framework 4.8 is downloaded from Microsoft. The game's launcher
     needs it.
4. When the window says **"Done. Mu The Matrix is installed."**, click **Close**.

If the installation stops (for example, because the internet connection dropped), click **Try Again**. It
continues where it stopped, and a download that was cut off resumes.

## Step 4: Play

1. In the Mu The Matrix window, click **Play**. The app closes and the Mu The Matrix launcher appears a few
   seconds later.
2. Wait until the launcher shows the **Server Time** and **Press GameStart to Play**.
3. Click **GAME START**. The game window opens after about 20 seconds.
4. Choose a server, then type your account name and password, and press Return.

Only one copy of the game can run at a time. Your password is never saved by the app.

**The next times:** double-click **Mu The Matrix** in Applications (or in the Dock). The launcher opens
directly. To see the Mu The Matrix window again, hold the **Option (⌥)** key while you open the app.

## Choosing the window size (resolution)

The installer picks the largest window that fits your screen. To change it:

- Hold **Option (⌥)** while you open the app, choose a size in **Resolution**, then click **Play**; or
- In the launcher, click **Settings** and choose a size there.

The sizes in both lists are the same, and all of them fit your screen.

## If something goes wrong

| What you see | What to do |
|---|---|
| "Mu The Matrix.app" Not Opened | Do Step 2. |
| "Rosetta 2 is not installed" during the installation | Open **Terminal**, paste `softwareupdate --install-rosetta --agree-to-license`, press Return, wait until it says it is done, then click **Try Again**. |
| "Not enough free disk space" | Free up space (12 GB), then click **Try Again**. |
| "Mu The Matrix is not installed yet" when you click Play | Click **Install…** in that message, or hold Option while opening the app and click **Install…**. |
| "Mu The Matrix is already running" | The game or launcher is still open. Close it (if you cannot see it, look in the Dock), then open the app again. |
| The launcher does not appear | Wait a minute: the first start can be slow. If nothing appears, hold Option while opening the app and click **Open Log**, then send the file **app.log** to your server team. |
| An error in the launcher after your Mac was asleep | Close the launcher and the game, then open Mu The Matrix again. Every start resets the game's environment. |
| The game is slow | In the Mu The Matrix window (hold Option while opening), keep **Fast x87 math** ticked and choose a smaller **Resolution**. The game shows at most 25 frames per second by design. |
| The game window does not fit the screen | Choose a smaller resolution (see above). |
| The installation fails again and again | Hold Option while opening the app, click **Open Log**, and send **app.log** to your server team. |

## Uninstall

1. Quit the game and the launcher.
2. Drag **Mu The Matrix** from Applications to the Trash.
3. In the Finder, choose **Go** > **Go to Folder…**, type `~/Library/Application Support/` and press Return.
   Drag the folder **MuTheMatrix** to the Trash. It holds the game, the free Windows environment and your game
   settings, about 4.5 GB.
4. Optional: in the same way, delete `~/Library/Logs/MuTheMatrix` (logs) and `~/.cache/winetricks` (the saved
   Microsoft installers).
5. Empty the Trash.

## How this guide was tested

On 2026-10-18, on a Mac with an M5 chip and macOS 27.0.1, the installation was run from scratch: from the app's
Install window with an existing game folder, and with the official download (about 45 minutes in total). After
that, the game was started from the app, the account logged in and the character entered the world.
Step 2 was checked up to the "Not Opened" message. The Terminal line in Step 2 was used successfully. The "Open
Anyway" button in System Settings could not be clicked in this test; it is the standard way macOS offers for apps
that are not registered with Apple.
