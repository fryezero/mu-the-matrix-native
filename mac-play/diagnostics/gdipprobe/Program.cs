// Reproduces the IGCN launcher default-design image pipeline step by step (dg.b / dg.a(BitmapImage) / dg.a(Bitmap)).
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Windows.Media.Imaging;

static class P {
    static int failures;
    static void Step(string name, Action a) {
        try { a(); Console.WriteLine("OK   " + name); }
        catch (Exception e) { failures++; Console.WriteLine("FAIL " + name + ": " + e.GetType().Name + ": " + e.Message); }
    }
    [STAThread]
    static int Main(string[] args) {
        string path = args.Length > 0 ? args[0] : null;
        Bitmap gdi = null, gray = null; MemoryStream png = null; BitmapImage wpf = null;
        Step("GDI+ new Bitmap(16,16) + Save PNG", () => { using (var b = new Bitmap(16, 16)) using (var ms = new MemoryStream()) b.Save(ms, ImageFormat.Png); });
        Step("GDI+ ImageConverter on MemoryBmp", () => { using (var b = new Bitmap(16, 16)) new ImageConverter().ConvertTo(b, typeof(byte[])); });
        if (path != null) {
            Step("WPF BitmapImage load " + path, () => { wpf = new BitmapImage(); wpf.BeginInit(); wpf.UriSource = new Uri(path, UriKind.Absolute); wpf.CacheOption = BitmapCacheOption.OnLoad; wpf.EndInit(); Console.WriteLine("     " + wpf.PixelWidth + "x" + wpf.PixelHeight + " " + wpf.Format); });
        } else {
            Step("WPF BitmapImage from generated PNG", () => { var ms = new MemoryStream(); using (var b = new Bitmap(32, 32)) b.Save(ms, ImageFormat.Png); ms.Position = 0; wpf = new BitmapImage(); wpf.BeginInit(); wpf.StreamSource = ms; wpf.CacheOption = BitmapCacheOption.OnLoad; wpf.EndInit(); });
        }
        Step("WPF PngBitmapEncoder.Save", () => { png = new MemoryStream(); var enc = new PngBitmapEncoder(); enc.Frames.Add(BitmapFrame.Create(wpf, null, null, null)); enc.Save(png); Console.WriteLine("     png bytes " + png.Length); });
        Step("GDI+ new Bitmap(new Bitmap(stream))", () => { gdi = new Bitmap(new Bitmap(png)); Console.WriteLine("     " + gdi.Width + "x" + gdi.Height + " " + gdi.PixelFormat); });
        Step("GDI+ ColorMatrix DrawImage", () => {
            gray = new Bitmap(gdi.Width, gdi.Height);
            using (var g = Graphics.FromImage(gray)) {
                var cm = new ColorMatrix(new float[][] { new float[]{.3f,.3f,.3f,0,0}, new float[]{.59f,.59f,.59f,0,0}, new float[]{.11f,.11f,.11f,0,0}, new float[]{0,0,0,1,0}, new float[]{0,0,0,0,1} });
                var ia = new ImageAttributes(); ia.SetColorMatrix(cm);
                g.DrawImage(gdi, new Rectangle(0, 0, gdi.Width, gdi.Height), 0, 0, gdi.Width, gdi.Height, GraphicsUnit.Pixel, ia);
            }
        });
        Step("ImageConverter.ConvertTo(gray)", () => { var bytes = (byte[])new ImageConverter().ConvertTo(gray, typeof(byte[])); Console.WriteLine("     " + bytes.Length + " bytes; raw " + gray.RawFormat.Guid); });
        Step("ImageConverter.ConvertTo(gdi)", () => { var bytes = (byte[])new ImageConverter().ConvertTo(gdi, typeof(byte[])); Console.WriteLine("     " + bytes.Length + " bytes; raw " + gdi.RawFormat.Guid); });
        return failures == 0 ? 0 : 1;
    }
}
