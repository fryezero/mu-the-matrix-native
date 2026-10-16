// Synthetic Win32 check for the display APIs used by WPF window placement.
// Compiled by the bottle's installed .NET Framework compiler, without an SDK.
using System;
using System.Runtime.InteropServices;

internal static class MonitorCheck
{
    [StructLayout(LayoutKind.Sequential)]
    private struct Rect { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct MonitorInfo
    {
        public int Size;
        public Rect Monitor, Work;
        public uint Flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string Device;
    }
    [StructLayout(LayoutKind.Explicit, Size = 220)]
    private struct DisplayMode
    {
        [FieldOffset(68)] public ushort Size;
        [FieldOffset(172)] public uint Width;
        [FieldOffset(176)] public uint Height;
    }
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateWindowExW(uint ex, string cls, string name,
        uint style, int x, int y, int width, int height, IntPtr parent,
        IntPtr menu, IntPtr instance, IntPtr param);
    [DllImport("user32.dll")]
    private static extern bool DestroyWindow(IntPtr window);
    [DllImport("user32.dll")]
    private static extern IntPtr MonitorFromWindow(IntPtr window, uint flags);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern bool GetMonitorInfoW(IntPtr monitor, ref MonitorInfo info);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern bool EnumDisplaySettingsW(string device, int index, ref DisplayMode mode);

    private static int Main()
    {
        IntPtr window = CreateWindowExW(0, "STATIC", "Mu display check", 0x80000000,
            0, 0, 16, 16, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero);
        if (window == IntPtr.Zero)
        {
            Console.Error.WriteLine("Display check failed: cannot create a window.");
            return 1;
        }
        try
        {
            IntPtr monitor = MonitorFromWindow(window, 2); // MONITOR_DEFAULTTONEAREST
            MonitorInfo info = new MonitorInfo();
            info.Size = Marshal.SizeOf(typeof(MonitorInfo));
            DisplayMode mode = new DisplayMode();
            mode.Size = (ushort)Marshal.SizeOf(typeof(DisplayMode));
            if (monitor == IntPtr.Zero || !GetMonitorInfoW(monitor, ref info) ||
                !EnumDisplaySettingsW(null, -1, ref mode) || mode.Width == 0 || mode.Height == 0)
            {
                Console.Error.WriteLine("Display check failed: missing monitor or primary display mode. " +
                    "Close this bottle's programs and retry Play.command.");
                return 1;
            }
            Console.WriteLine("Display check passed: {0}, {1}x{2}, monitor 0x{3:x}",
                info.Device, mode.Width, mode.Height, monitor.ToInt64());
            return 0;
        }
        finally { DestroyWindow(window); }
    }
}
