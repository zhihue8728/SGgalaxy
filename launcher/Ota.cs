// Shared OTA code (SGLauncher + SGPublish), 2026-10-22, claude/OTA_PLAN.md.
// C# 5 / .NET Framework 4.0 only (builds with the csc.exe that ships with Windows, or mono mcs).
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Numerics;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

namespace SGOta
{
    public static class Ota
    {
        public const int Chunk = 1 << 20;                 // delta unit: 1 MB
        public const string StampMark = "\n#SGOTA1#";      // launcher config appended to the exe

        public static string Hex(byte[] b)
        {
            StringBuilder s = new StringBuilder(b.Length * 2);
            foreach (byte x in b) s.Append(x.ToString("x2"));
            return s.ToString();
        }

        public static string Sha256(byte[] b, int off, int n)
        {
            using (SHA256 h = SHA256.Create()) return Hex(h.ComputeHash(b, off, n));
        }

        public static string Sha256File(string path)
        {
            using (SHA256 h = SHA256.Create())
            using (FileStream f = File.OpenRead(path)) return Hex(h.ComputeHash(f));
        }

        /// whole-file sha256 + 1 MB chunk hashes in one pass
        public static string HashFile(string path, List<string> chunks)
        {
            using (SHA256 whole = SHA256.Create())
            using (FileStream f = File.OpenRead(path))
            {
                byte[] buf = new byte[Chunk];
                while (true)
                {
                    int n = ReadFull(f, buf, Chunk);
                    if (n <= 0) break;
                    whole.TransformBlock(buf, 0, n, null, 0);
                    if (chunks != null) chunks.Add(Sha256(buf, 0, n));
                    if (n < Chunk) break;
                }
                whole.TransformFinalBlock(new byte[0], 0, 0);
                return Hex(whole.Hash);
            }
        }

        // ---- content-defined chunks (2026-10-27, user: "要下载200多MB比原版程式还多") ----------------------------------
        // A gear rolling hash cuts a file where (h & 0x1fff) == 0 (min 2 KB, max 64 KB, ~8 KB average), so an insert
        // only changes the chunks around it and the rest still match at their new offsets.  The launcher rebuilds a file
        // from the chunks it already has (the original 1.8.5 file or an older release) and downloads only the others:
        // a new player's first update went from ~290 MB to ~20 MB.  Signature object ("cdc" in the manifest):
        // "SGCDC1" + u32 count + count x {u32 length, 16 bytes = the first half of the chunk's sha256}.
        public const int CdcMin = 2048, CdcMax = 65536;
        public const uint CdcMask = (1u << 13) - 1;
        static readonly uint[] Gear = MakeGear();
        static uint[] MakeGear()
        {
            uint[] g = new uint[256];
            uint x = 2463534242u;
            for (int i = 0; i < 256; i++) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; g[i] = x; }
            return g;
        }

        public class CdcChunk { public long Off; public int Len; public string Key; }

        public static string CdcKey(byte[] b, int off, int n)
        {
            using (SHA256 h = SHA256.Create())
            {
                byte[] d = h.ComputeHash(b, off, n);
                StringBuilder s = new StringBuilder(32);
                for (int i = 0; i < 16; i++) s.Append(d[i].ToString("x2"));
                return s.ToString();
            }
        }

        public static List<CdcChunk> Cdc(string path)
        {
            List<CdcChunk> r = new List<CdcChunk>();
            byte[] cur = new byte[CdcMax];
            byte[] buf = new byte[1 << 22];
            int curLen = 0; uint h = 0; long start = 0;
            using (FileStream f = File.OpenRead(path))
            {
                while (true)
                {
                    int n = f.Read(buf, 0, buf.Length);
                    if (n <= 0) break;
                    for (int i = 0; i < n; i++)
                    {
                        byte b = buf[i];
                        cur[curLen++] = b;
                        h = (h << 1) + Gear[b];
                        if ((curLen >= CdcMin && (h & CdcMask) == 0) || curLen >= CdcMax)
                        {
                            CdcChunk c = new CdcChunk(); c.Off = start; c.Len = curLen; c.Key = CdcKey(cur, 0, curLen);
                            r.Add(c); start += curLen; curLen = 0; h = 0;
                        }
                    }
                }
            }
            if (curLen > 0) { CdcChunk c = new CdcChunk(); c.Off = start; c.Len = curLen; c.Key = CdcKey(cur, 0, curLen); r.Add(c); }
            return r;
        }

        public static byte[] CdcBlob(List<CdcChunk> l)
        {
            using (MemoryStream m = new MemoryStream())
            {
                m.Write(Encoding.ASCII.GetBytes("SGCDC1"), 0, 6);
                m.Write(BitConverter.GetBytes((uint)l.Count), 0, 4);
                foreach (CdcChunk c in l)
                {
                    m.Write(BitConverter.GetBytes((uint)c.Len), 0, 4);
                    for (int i = 0; i < 16; i++) m.WriteByte(Convert.ToByte(c.Key.Substring(i * 2, 2), 16));
                }
                return m.ToArray();
            }
        }

        public static List<CdcChunk> ParseCdc(byte[] b)
        {
            if (b.Length < 10 || Encoding.ASCII.GetString(b, 0, 6) != "SGCDC1") throw new IOException("bad cdc object");
            uint n = BitConverter.ToUInt32(b, 6);
            if (b.Length != 10 + 20L * n) throw new IOException("bad cdc object size");
            List<CdcChunk> r = new List<CdcChunk>((int)n);
            long off = 0;
            for (int i = 0; i < n; i++)
            {
                int p = 10 + 20 * i;
                CdcChunk c = new CdcChunk(); c.Off = off; c.Len = (int)BitConverter.ToUInt32(b, p);
                StringBuilder s = new StringBuilder(32);
                for (int k = 0; k < 16; k++) s.Append(b[p + 4 + k].ToString("x2"));
                c.Key = s.ToString();
                r.Add(c); off += c.Len;
            }
            return r;
        }

        public static int ReadFull(Stream s, byte[] buf, int n)
        {
            int got = 0;
            while (got < n)
            {
                int r = s.Read(buf, got, n - got);
                if (r <= 0) break;
                got += r;
            }
            return got;
        }

        // ---- JSON ------------------------------------------------------------------------------------------------
        public static JavaScriptSerializer Json()
        {
            JavaScriptSerializer j = new JavaScriptSerializer();
            j.MaxJsonLength = int.MaxValue;
            return j;
        }

        public static Dictionary<string, object> ParseObj(string text)
        {
            return (Dictionary<string, object>)Json().DeserializeObject(text);
        }

        public static string Str(Dictionary<string, object> d, string k, string def)
        {
            object v;
            return d != null && d.TryGetValue(k, out v) && v != null ? Convert.ToString(v, System.Globalization.CultureInfo.InvariantCulture) : def;
        }

        public static long Long(Dictionary<string, object> d, string k, long def)
        {
            object v;
            return d != null && d.TryGetValue(k, out v) && v != null ? Convert.ToInt64(v) : def;
        }

        public static Dictionary<string, object> Obj(Dictionary<string, object> d, string k)
        {
            object v;
            return d != null && d.TryGetValue(k, out v) ? v as Dictionary<string, object> : null;
        }

        public static List<object> Arr(Dictionary<string, object> d, string k)
        {
            object v;
            List<object> r = new List<object>();
            if (d != null && d.TryGetValue(k, out v) && v is IEnumerable && !(v is string))
                foreach (object x in (IEnumerable)v) r.Add(x);
            return r;
        }

        // ---- RSA PKCS#1 v1.5 + SHA-256, done with BigInteger (no CSP provider differences between Windows versions) --
        static readonly byte[] DigestInfo = { 0x30, 0x31, 0x30, 0x0d, 0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01, 0x05, 0x00, 0x04, 0x20 };

        public static BigInteger B(byte[] bigEndian)
        {
            byte[] le = new byte[bigEndian.Length + 1];          // + 0 byte = positive
            for (int i = 0; i < bigEndian.Length; i++) le[i] = bigEndian[bigEndian.Length - 1 - i];
            return new BigInteger(le);
        }

        public static byte[] BE(BigInteger v, int len)
        {
            byte[] le = v.ToByteArray();
            byte[] r = new byte[len];
            for (int i = 0; i < len && i < le.Length; i++) r[len - 1 - i] = le[i];
            return r;
        }

        static byte[] Encoded(byte[] data, int k)
        {
            byte[] h;
            using (SHA256 s = SHA256.Create()) h = s.ComputeHash(data);
            byte[] em = new byte[k];
            em[0] = 0; em[1] = 1;
            int t = DigestInfo.Length + h.Length;
            for (int i = 2; i < k - t - 1; i++) em[i] = 0xff;
            em[k - t - 1] = 0;
            Buffer.BlockCopy(DigestInfo, 0, em, k - t, DigestInfo.Length);
            Buffer.BlockCopy(h, 0, em, k - h.Length, h.Length);
            return em;
        }

        public static byte[] Sign(byte[] data, byte[] n, byte[] d)
        {
            int k = n.Length;
            BigInteger s = BigInteger.ModPow(B(Encoded(data, k)), B(d), B(n));
            return BE(s, k);
        }

        public static bool Verify(byte[] data, byte[] sig, byte[] n, byte[] e)
        {
            int k = n.Length;
            if (sig.Length != k) return false;
            BigInteger m = BigInteger.ModPow(B(sig), B(e), B(n));
            byte[] got = BE(m, k), want = Encoded(data, k);
            int diff = 0;
            for (int i = 0; i < k; i++) diff |= got[i] ^ want[i];
            return diff == 0;
        }

        public static byte[] Trim(byte[] b)
        {
            int i = 0;
            while (i < b.Length - 1 && b[i] == 0) i++;
            byte[] r = new byte[b.Length - i];
            Buffer.BlockCopy(b, i, r, 0, r.Length);
            return r;
        }

        // ---- launcher stamp (public key + download URLs appended to SGLauncher.exe) ----------------------------------
        public static Dictionary<string, object> ReadStamp(string exe)
        {
            byte[] all = File.ReadAllBytes(exe);
            byte[] mark = Encoding.ASCII.GetBytes(StampMark);
            for (int i = all.Length - mark.Length; i >= Math.Max(0, all.Length - 65536); i--)
            {
                bool ok = true;
                for (int j = 0; j < mark.Length && ok; j++) ok = all[i + j] == mark[j];
                if (ok)
                {
                    string js = Encoding.UTF8.GetString(all, i + mark.Length, all.Length - i - mark.Length);
                    return ParseObj(js);
                }
            }
            return null;
        }

        /// exe without a stamp (the build output), so stamping twice does not stack
        public static byte[] Unstamped(byte[] all)
        {
            byte[] mark = Encoding.ASCII.GetBytes(StampMark);
            for (int i = all.Length - mark.Length; i >= Math.Max(0, all.Length - 65536); i--)
            {
                bool ok = true;
                for (int j = 0; j < mark.Length && ok; j++) ok = all[i + j] == mark[j];
                if (ok)
                {
                    byte[] r = new byte[i];
                    Buffer.BlockCopy(all, 0, r, 0, i);
                    return r;
                }
            }
            return all;
        }

        public static int Cmp(string a, string b)
        {
            string[] x = (a ?? "0").Split(new char[] { '.' }), y = (b ?? "0").Split(new char[] { '.' });
            for (int i = 0; i < Math.Max(x.Length, y.Length); i++)
            {
                int p = 0, q = 0;
                if (i < x.Length) int.TryParse(x[i], out p);
                if (i < y.Length) int.TryParse(y[i], out q);
                if (p != q) return p < q ? -1 : 1;
            }
            return 0;
        }
    }
}
