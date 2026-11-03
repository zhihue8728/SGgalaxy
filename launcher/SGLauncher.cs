// GOLauncher (source SGLauncher.cs): update + start Galactic Overlord (银河霸主, formerly Shattered Galaxy) (2026-10-22,
// claude/OTA_PLAN.md).  In the game folder as GOLauncher.exe (next to GO.exe; 2026-11-02 the SG names became GO names -
// an old SGLauncher.exe copies itself to GOLauncher.exe and moves the shortcuts, see Program.MoveToGoName).
//   1. downloads manifest-<channel>.json (+ .sig) and checks the RSA signature (public key stamped into this exe)
//   2. rebuilds every changed file from content-defined chunks the player already has (the file itself or its .orig,
//      e.g. the original 1.8.5 game) and downloads only the rest (HTTP Range, sha256-checked); old manifests without
//      "cdc": 1 MB aligned chunks
//   3. installs the files (2026-11-01: no backup copies; the old *.orig copies are removed once the files are
//      correct); Program Files -> asks for administrator rights once.  Files the release lists under "remove" (left
//      from older releases, e.g. the loose SGHud-* art now in SGHud.pak) are deleted from the game folder.
//   4. writes HKCU\SOFTWARE\Galactic Overlord REG_SG_IP (client patch F23 connects there; F54 renamed the key, was SOFTWARE\Nexon\TacticalCommanders), starts GO.exe
// Command line:  --dir GAMEDIR   --url URL (instead of the stamped ones)   --channel cn|tw|en
//                --check (no window: update, print, do not start the game)   --apply STAGE (internal, elevated)
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace SGOta
{
    class Txt
    {
        public static string Lang = "en";
        static readonly Dictionary<string, string[]> T = new Dictionary<string, string[]>
        {
            //                 zh-cn                                  zh-tw                                  en
            {"title",   new[] {"银河霸主 启动器", "銀河霸主 啟動器", "Galactic Overlord Launcher"}},
            {"check",   new[] {"正在检查更新…", "正在檢查更新…", "Checking for updates…"}},
            {"scan",    new[] {"正在检查游戏文件…", "正在檢查遊戲檔案…", "Checking game files…"}},
            {"dl",      new[] {"正在下载更新 {0}", "正在下載更新 {0}", "Downloading {0}"}},
            {"apply",   new[] {"正在安装更新…", "正在安裝更新…", "Installing…"}},
            {"ready",   new[] {"游戏已是最新版本 {0}", "遊戲已是最新版本 {0}", "Game is up to date ({0})"}},
            {"updated", new[] {"已更新到 {0}", "已更新到 {0}", "Updated to {0}"}},
            {"offline", new[] {"无法连接更新服务器，可直接进入游戏（若版本过旧，服务器会提示）。", "無法連線更新伺服器，可直接進入遊戲（若版本過舊，伺服器會提示）。", "Update server unreachable - you can still start the game."}},
            {"badsig",  new[] {"更新文件签名错误（可能被篡改），已停止更新。", "更新檔案簽章錯誤（可能被竄改），已停止更新。", "Bad update signature (tampered?) - update stopped."}},
            {"nogame",  new[] {"请把 GOLauncher.exe 放到银河霸主游戏目录（GO.exe 所在的文件夹）再执行。", "請把 GOLauncher.exe 放到銀河霸主遊戲目錄（GO.exe 所在的資料夾）再執行。", "Put GOLauncher.exe into the Galactic Overlord folder (where GO.exe is)."}},
            {"running", new[] {"请先关闭正在执行的游戏，再按重试。", "請先關閉正在執行的遊戲，再按重試。", "Close the running game first, then press Retry."}},
            {"admin",   new[] {"游戏装在受保护的文件夹，安装更新需要管理员权限。", "遊戲裝在受保護的資料夾，安裝更新需要系統管理員權限。", "The game folder is protected - installing needs administrator rights."}},
            {"fail",    new[] {"更新失败：{0}", "更新失敗：{0}", "Update failed: {0}"}},
            {"play",    new[] {"开始游戏", "開始遊戲", "Play"}},
            {"retry",   new[] {"重试", "重試", "Retry"}},
            {"exit",    new[] {"退出", "離開", "Exit"}},
            {"notes",   new[] {"更新说明", "更新說明", "Release notes"}},
            {"self",    new[] {"启动器已更新，正在重新启动…", "啟動器已更新，正在重新啟動…", "Launcher updated - restarting…"}},
        };

        public static string Get(string k) { return Get(k, new object[0]); }

        public static string Get(string k, params object[] a)
        {
            string[] v;
            if (!T.TryGetValue(k, out v)) return k;
            int i = Lang == "zh-cn" ? 0 : Lang == "zh-tw" ? 1 : 2;
            return a.Length > 0 ? string.Format(v[i], a) : v[i];
        }
    }

    class UpdateException : Exception
    {
        public string Key;
        public UpdateException(string key, string msg) : base(msg) { Key = key; }
    }

    class Updater
    {
        public string GameDir, SelfExe, Channel, StateDir;
        public string[] Urls;
        public Dictionary<string, object> Manifest, State;
        public Action<string> OnStatus = delegate { };
        public Action<long, long> OnProgress = delegate { };
        public Action<string> OnLog = delegate { };
        public bool SelfUpdated, Offline, ChannelFixed;
        byte[] keyN, keyE;

        public Updater(string gameDir, string selfExe, string urlOverride, string channel)
        {
            GameDir = Path.GetFullPath(gameDir);
            SelfExe = selfExe;
            DeleteOld();                                                    // (before anything that may fail)
            string la = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            StateDir = Path.Combine(la, "GOLauncher");
            string oldState = Path.Combine(la, "SGLauncher");          // (11-02 GO names) the old state, once
            if (!Directory.Exists(StateDir) && Directory.Exists(oldState))
                try { Directory.CreateDirectory(StateDir); foreach (string f in Directory.GetFiles(oldState)) File.Copy(f, Path.Combine(StateDir, Path.GetFileName(f)), true); } catch { }
            Directory.CreateDirectory(StateDir);
            string sp = Path.Combine(StateDir, "state.json");
            try { State = File.Exists(sp) ? Ota.ParseObj(File.ReadAllText(sp)) : null; } catch { State = null; }
            if (State == null) State = new Dictionary<string, object>();
            Dictionary<string, object> stamp = null;
            try { stamp = Ota.ReadStamp(selfExe); } catch { }
            if (stamp != null)
            {
                keyN = Convert.FromBase64String(Ota.Str(stamp, "n", ""));
                keyE = Convert.FromBase64String(Ota.Str(stamp, "e", ""));
                List<string> u = new List<string>();
                foreach (object o in Ota.Arr(stamp, "urls")) u.Add(((string)o).TrimEnd(new char[] { '/' }));
                Urls = u.ToArray();
            }
            if (!string.IsNullOrEmpty(urlOverride)) Urls = new[] { urlOverride.TrimEnd(new char[] { '/' }) };
            if (keyN == null) throw new UpdateException("fail", "launcher has no signing key (not stamped by SGPublish)");
            ChannelFixed = channel != null;
            Channel = channel ?? Ota.Str(State, "channel", null);
            if (Channel == null)
            {
                int acp = Encoding.Default.CodePage;
                Channel = acp == 936 ? "cn" : acp == 950 ? "tw" : "en";
            }
            Txt.Lang = Channel == "cn" ? "zh-cn" : Channel == "tw" ? "zh-tw" : "en";
        }

        public void SaveState()
        {
            State["channel"] = Channel;
            File.WriteAllText(Path.Combine(StateDir, "state.json"), Ota.Json().Serialize(State));
        }

        public static bool LooksLikeGameDir(string dir)
        {
            return File.Exists(Path.Combine(dir, "GO.exe")) || File.Exists(Path.Combine(dir, "SG.exe")) || File.Exists(Path.Combine(dir, "tc.dat"));
        }

        // ---- HTTP ---------------------------------------------------------------------------------------------------
        static byte[] Get(string url, long from, long to)
        {
            HttpWebRequest r = (HttpWebRequest)WebRequest.Create(url);
            r.Timeout = 30000; r.ReadWriteTimeout = 30000;
            r.UserAgent = "GOLauncher/1";
            r.KeepAlive = true;
            // (2026-11-01) the update server gzips what it sends when asked (server/ota.py): ~35 % less to download.
            // The data is checked by sha256 after decompression, exactly as before.
            r.AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate;
            if (from >= 0) r.AddRange(from, to);
            using (HttpWebResponse resp = (HttpWebResponse)r.GetResponse())
            using (Stream s = resp.GetResponseStream())
            using (MemoryStream m = new MemoryStream())
            {
                if (from >= 0 && resp.StatusCode != HttpStatusCode.PartialContent && from > 0)
                    throw new IOException("server ignored the range request");
                s.CopyTo(m);
                byte[] b = m.ToArray();
                if (from >= 0 && resp.StatusCode != HttpStatusCode.PartialContent)
                {   // a full answer (range from 0): cut it
                    long n = Math.Min(b.Length, to - from + 1);
                    byte[] c = new byte[n];
                    Buffer.BlockCopy(b, (int)from, c, 0, (int)n);
                    return c;
                }
                return b;
            }
        }

        byte[] GetAny(string rel, long from, long to, int tries)
        {
            Exception last = null, notFound = null;
            for (int t = 0; t < tries && notFound == null; t++)
                foreach (string u in Urls)
                {
                    try { return Get(u + "/" + rel, from, to); }
                    catch (Exception e)
                    {
                        last = e; OnLog(u + "/" + rel + ": " + e.Message);
                        WebException we = e as WebException;
                        if (we != null && we.Response is HttpWebResponse && ((HttpWebResponse)we.Response).StatusCode == HttpStatusCode.NotFound)
                            notFound = e;                      // a working server says it does not exist
                    }
                    if (t > 0) Thread.Sleep(1000 * t);
                }
            throw notFound ?? last ?? new IOException("no download URL");
        }

        // ---- manifest ---------------------------------------------------------------------------------------------
        public void LoadManifest()
        {
            OnStatus(Txt.Get("check"));
            byte[] mb = null, sig = null;
            List<string> chans = new List<string> { Channel };
            if (!ChannelFixed) foreach (string c in new[] { "cn", "tw", "en" }) if (!chans.Contains(c)) chans.Add(c);
            Exception last = null;
            foreach (string c in chans)
            {
                try
                {
                    mb = GetAny("manifest-" + c + ".json", -1, -1, 2);
                    sig = GetAny("manifest-" + c + ".json.sig", -1, -1, 2);
                    Channel = c;
                    break;
                }
                catch (WebException e)
                {
                    last = e; mb = null;
                    HttpWebResponse r = e.Response as HttpWebResponse;
                    if (r == null || r.StatusCode != HttpStatusCode.NotFound) break;   // offline: do not try the others
                }
                catch (Exception e) { last = e; mb = null; break; }
            }
            if (mb == null)
            {
                Offline = true;
                throw new UpdateException("offline", last != null ? last.Message : "?");
            }
            Txt.Lang = Channel == "cn" ? "zh-cn" : Channel == "tw" ? "zh-tw" : "en";
            if (!Ota.Verify(mb, Convert.FromBase64String(Encoding.ASCII.GetString(sig).Trim()), keyN, keyE))
                throw new UpdateException("badsig", "signature");
            Manifest = Ota.ParseObj(Encoding.UTF8.GetString(mb));
            if (Ota.Str(Manifest, "channel", "") != Channel) throw new UpdateException("badsig", "channel mismatch");
        }

        public string Version { get { return Ota.Str(Manifest, "version", "?"); } }

        // ---- plan / download ------------------------------------------------------------------------------------------
        class Item { public string Path, Sha, Target, Cdc; public long Size; public List<string> Chunks; public bool IsLauncher; }

        // ---- content-defined delta (2026-10-27): rebuild a file from chunks the player already has ----------------------
        class Piece { public long NewOff; public int Len; public string Key; public int Src = -1; public long SrcOff; }
        class CdcPlan { public List<Piece> P = new List<Piece>(); public List<string> Src = new List<string>(); public long Missing; }

        CdcPlan PlanCdc(Item it)
        {
            if (string.IsNullOrEmpty(it.Cdc)) return null;
            try
            {
                byte[] b = GetAny("objects/" + it.Cdc, -1, -1, 3);
                if (Ota.Sha256(b, 0, b.Length) != it.Cdc) { OnLog(it.Path + ": cdc object check failed"); return null; }
                List<Ota.CdcChunk> want = Ota.ParseCdc(b);
                long tot = 0;
                foreach (Ota.CdcChunk c in want) tot += c.Len;
                if (tot != it.Size) { OnLog(it.Path + ": cdc size mismatch"); return null; }
                CdcPlan pl = new CdcPlan();
                Dictionary<string, KeyValuePair<int, long>> idx = new Dictionary<string, KeyValuePair<int, long>>();
                foreach (string cand in new string[] { it.Target, it.Target + ".orig" })
                {
                    if (!File.Exists(cand)) continue;
                    int si = pl.Src.Count; pl.Src.Add(cand);
                    foreach (Ota.CdcChunk c in Ota.Cdc(cand))
                        if (!idx.ContainsKey(c.Key)) idx[c.Key] = new KeyValuePair<int, long>(si, c.Off);
                }
                foreach (Ota.CdcChunk c in want)
                {
                    Piece p = new Piece(); p.NewOff = c.Off; p.Len = c.Len; p.Key = c.Key;
                    KeyValuePair<int, long> h;
                    if (idx.TryGetValue(c.Key, out h)) { p.Src = h.Key; p.SrcOff = h.Value; } else pl.Missing += c.Len;
                    pl.P.Add(p);
                }
                OnLog(it.Path + ": " + (pl.Missing / 1048576.0).ToString("0.0") + " of " + (it.Size / 1048576.0).ToString("0.0") + " MB to download");
                return pl;
            }
            catch (Exception e) { OnLog(it.Path + ": cdc " + e.Message); return null; }
        }

        byte[] GetPieces(Item it, List<Piece> P, int i, int j)
        {
            long a = P[i].NewOff, n = P[j - 1].NewOff + P[j - 1].Len - a;
            for (int t = 0; t < 4; t++)
            {
                byte[] d = GetAny("objects/" + it.Sha, a, a + n - 1, 3);
                bool ok = d.Length == n;
                for (int k = i; k < j && ok; k++) ok = Ota.CdcKey(d, (int)(P[k].NewOff - a), P[k].Len) == P[k].Key;
                if (ok) return d;
                OnLog(it.Path + " @" + a + ": bad data, retry");
            }
            throw new UpdateException("fail", it.Path + ": download check failed");
        }

        void WriteCdc(Item it, CdcPlan pl, FileStream outf, ref long done, long total)
        {
            FileStream[] src = new FileStream[pl.Src.Count];
            try
            {
                for (int s = 0; s < src.Length; s++) src[s] = File.OpenRead(pl.Src[s]);
                byte[] buf = new byte[Ota.CdcMax];
                int i = 0;
                while (i < pl.P.Count)
                {
                    Piece p = pl.P[i];
                    if (p.Src >= 0)
                    {
                        src[p.Src].Seek(p.SrcOff, SeekOrigin.Begin);
                        if (Ota.ReadFull(src[p.Src], buf, p.Len) == p.Len && Ota.CdcKey(buf, 0, p.Len) == p.Key)
                        {
                            outf.Write(buf, 0, p.Len); i++; continue;
                        }
                        p.Src = -1;                                        // local file changed meanwhile: download it
                        total += p.Len;
                    }
                    int j = i; long n = 0;
                    while (j < pl.P.Count && pl.P[j].Src < 0 && (j == i || n + pl.P[j].Len <= (4 << 20))) { n += pl.P[j].Len; j++; }
                    byte[] d = GetPieces(it, pl.P, i, j);
                    outf.Write(d, 0, d.Length);
                    done += d.Length;
                    OnProgress(done, total);
                    i = j;
                }
            }
            finally { foreach (FileStream f in src) if (f != null) f.Dispose(); }
        }

        Dictionary<string, object> HashCache()
        {
            Dictionary<string, object> c = Ota.Obj(State, "hashes");
            if (c == null) { c = new Dictionary<string, object>(); State["hashes"] = c; }
            return c;
        }

        bool UpToDate(string file, string sha, long size)
        {
            FileInfo fi = new FileInfo(file);
            if (!fi.Exists || fi.Length != size) return false;
            string key = file.ToLowerInvariant();
            string stamp = fi.Length + ":" + fi.LastWriteTimeUtc.Ticks;
            Dictionary<string, object> c = HashCache();
            Dictionary<string, object> e = Ota.Obj(c, key);
            if (e != null && Ota.Str(e, "stamp", "") == stamp) return Ota.Str(e, "sha", "") == sha;
            string got = Ota.Sha256File(file);
            Dictionary<string, object> ne = new Dictionary<string, object>();
            ne["stamp"] = stamp; ne["sha"] = got;
            c[key] = ne;
            return got == sha;
        }

        List<Item> Plan()
        {
            OnStatus(Txt.Get("scan"));
            List<Item> need = new List<Item>();
            foreach (object o in Ota.Arr(Manifest, "files"))
            {
                Dictionary<string, object> f = (Dictionary<string, object>)o;
                Item it = new Item();
                it.Path = Ota.Str(f, "path", "");
                if (it.Path == "" || it.Path.Contains("..") || Path.IsPathRooted(it.Path)) throw new UpdateException("badsig", "bad path " + it.Path);
                it.Sha = Ota.Str(f, "sha256", ""); it.Size = Ota.Long(f, "size", 0);
                it.Chunks = new List<string>();
                foreach (object c in Ota.Arr(f, "chunks")) it.Chunks.Add((string)c);
                it.Cdc = Ota.Str(f, "cdc", "");
                it.Target = System.IO.Path.Combine(GameDir, it.Path.Replace('/', System.IO.Path.DirectorySeparatorChar));
                if (!UpToDate(it.Target, it.Sha, it.Size)) need.Add(it);
            }
            Dictionary<string, object> l = Ota.Obj(Manifest, "launcher");
            if (l != null && SelfExe != null && Ota.Sha256File(SelfExe) != Ota.Str(l, "sha256", ""))
            {
                Item it = new Item();
                it.Path = System.IO.Path.GetFileName(SelfExe); it.Target = SelfExe; it.IsLauncher = true;
                it.Sha = Ota.Str(l, "sha256", ""); it.Size = Ota.Long(l, "size", 0); it.Chunks = new List<string>();
                need.Add(it);
            }
            return need;
        }

        string StageDir { get { return Path.Combine(StateDir, "stage"); } }

        /// (2026-11-01) the release's "remove" list (signed with the manifest): files of older releases to delete.
        /// Only plain relative paths; never a file the release itself installs, the game exe or this launcher.
        public List<string> RemovePaths()
        {
            List<string> r = new List<string>();
            HashSet<string> keep = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (string p in ManifestPaths()) keep.Add(p.Replace('\\', '/'));
            keep.Add(Ota.Str(Manifest, "start", "GO.exe"));
            if (SelfExe != null) keep.Add(Path.GetFileName(SelfExe));
            foreach (object o in Ota.Arr(Manifest, "remove"))
            {
                string p = (o as string ?? "").Replace('\\', '/').Trim();
                if (p == "" || p.Contains("..") || Path.IsPathRooted(p) || p.IndexOfAny(new char[] { '*', '?', ':' }) >= 0 || keep.Contains(p)) continue;
                r.Add(p);
            }
            return r;
        }

        /// the ones of them that are still in the game folder
        List<string> RemovePending()
        {
            List<string> r = new List<string>();
            foreach (string p in RemovePaths())
                if (File.Exists(Path.Combine(GameDir, p.Replace('/', Path.DirectorySeparatorChar)))) r.Add(p);
            return r;
        }

        /// delete them (also run elevated with --apply; a file that cannot be deleted stays, the next start tries again)
        public static void RemoveFiles(string gameDir, IEnumerable<string> paths)
        {
            foreach (string l in paths)
            {
                string rel = l.Trim();
                if (rel == "" || rel.Contains("..") || Path.IsPathRooted(rel) || rel.IndexOfAny(new char[] { '*', '?', ':' }) >= 0) continue;
                string f = Path.Combine(gameDir, rel.Replace('/', Path.DirectorySeparatorChar));
                if (File.Exists(f)) try { File.SetAttributes(f, FileAttributes.Normal); File.Delete(f); } catch { }
            }
        }

        List<string> ManifestPaths()
        {
            List<string> r = new List<string>();
            foreach (object o in Ota.Arr(Manifest, "files")) r.Add(Ota.Str((Dictionary<string, object>)o, "path", ""));
            return r;
        }

        void Stage(List<Item> need)
        {
            int chunk = (int)Ota.Long(Manifest, "chunk", Ota.Chunk);
            Directory.CreateDirectory(StageDir);
            // bytes to download: chunks that differ from the local file
            long total = 0, done = 0;
            Dictionary<Item, List<bool>> have = new Dictionary<Item, List<bool>>();
            Dictionary<Item, CdcPlan> cdc = new Dictionary<Item, CdcPlan>();
            foreach (Item it in need)
            {
                List<bool> h = new List<bool>();
                List<string> local = new List<string>();
                string staged = Path.Combine(StageDir, it.Path);
                if (File.Exists(staged) && new FileInfo(staged).Length == it.Size && Ota.Sha256File(staged) == it.Sha) { have[it] = null; continue; }
                CdcPlan pl = it.IsLauncher ? null : PlanCdc(it);
                if (pl != null) { cdc[it] = pl; have[it] = h; total += pl.Missing; continue; }
                if (it.Chunks.Count > 0 && File.Exists(it.Target)) try { Ota.HashFile(it.Target, local); } catch { }
                int nch = it.Chunks.Count > 0 ? it.Chunks.Count : (int)((it.Size + chunk - 1) / chunk);
                for (int i = 0; i < nch; i++)
                {
                    bool same = it.Chunks.Count > 0 && i < local.Count && local[i] == it.Chunks[i];
                    h.Add(same);
                    if (!same) total += Math.Min(chunk, it.Size - (long)i * chunk);
                }
                have[it] = h;
            }
            OnProgress(0, total);
            foreach (Item it in need)
            {
                if (have[it] == null) continue;                       // already staged by an earlier run
                string staged = Path.Combine(StageDir, it.Path);
                Directory.CreateDirectory(Path.GetDirectoryName(staged));
                OnStatus(Txt.Get("dl", it.Path));
                if (cdc.ContainsKey(it))
                    using (FileStream outf = new FileStream(staged + ".part", FileMode.Create, FileAccess.Write))
                        WriteCdc(it, cdc[it], outf, ref done, total);
                else
                using (FileStream outf = new FileStream(staged + ".part", FileMode.Create, FileAccess.Write))
                using (FileStream inf = have[it].Contains(true) ? File.OpenRead(it.Target) : null)
                {
                    byte[] buf = new byte[chunk];
                    for (int i = 0; i < have[it].Count; i++)
                    {
                        long a = (long)i * chunk;
                        int n = (int)Math.Min(chunk, it.Size - a);
                        byte[] data;
                        if (have[it][i])
                        {
                            inf.Seek(a, SeekOrigin.Begin);
                            Ota.ReadFull(inf, buf, n);
                            data = buf;
                        }
                        else
                        {
                            data = null;
                            for (int t = 0; t < 4 && data == null; t++)
                            {
                                byte[] d = GetAny("objects/" + it.Sha, a, a + n - 1, 3);
                                if (d.Length == n && (it.Chunks.Count == 0 || Ota.Sha256(d, 0, n) == it.Chunks[i])) data = d;
                                else OnLog(it.Path + " chunk " + i + ": bad data, retry");
                            }
                            if (data == null) throw new UpdateException("fail", it.Path + ": download check failed");
                            done += n;
                            OnProgress(done, total);
                        }
                        outf.Write(data, 0, n);
                    }
                }
                if (Ota.Sha256File(staged + ".part") != it.Sha) { File.Delete(staged + ".part"); throw new UpdateException("fail", it.Path + ": file check failed"); }
                if (File.Exists(staged)) File.Delete(staged);
                File.Move(staged + ".part", staged);
            }
            List<string> lines = new List<string>();
            foreach (Item it in need) lines.Add((it.IsLauncher ? "*" : "") + it.Path);
            File.WriteAllLines(Path.Combine(StageDir, "apply.txt"), lines.ToArray());
            File.WriteAllLines(Path.Combine(StageDir, "clean.txt"), ManifestPaths().ToArray());
            File.WriteAllLines(Path.Combine(StageDir, "remove.txt"), RemovePaths().ToArray());
        }

        // ---- install --------------------------------------------------------------------------------------------------
        public static bool Writable(string dir)
        {
            try
            {
                string p = Path.Combine(dir, ".sglauncher_write_test");
                File.WriteAllText(p, "x");
                File.Delete(p);
                return true;
            }
            catch { return false; }
        }

        /// copy the staged files into the game folder (also run elevated with --apply)
        public static void Apply(string stage, string gameDir, string selfExe, string oldVersion)
        {
            string[] lines = File.ReadAllLines(Path.Combine(stage, "apply.txt"));
            // (2026-11-01) no SGLauncher.backup copies any more (every start checks every file by sha256 and repairs it,
            // so the copies were never used - 78 MB on the user's PC); an old folder is removed
            string bdir = Path.Combine(gameDir, "SGLauncher.backup");
            if (Directory.Exists(bdir)) try { Directory.Delete(bdir, true); } catch { }
            // (2026-11-02 GO names) also here, where an elevated --apply can write a protected folder: GOLauncher.exe
            if (selfExe != null && string.Equals(Path.GetFileName(selfExe), "SGLauncher.exe", StringComparison.OrdinalIgnoreCase)
                && !File.Exists(Path.Combine(gameDir, "GOLauncher.exe")))
                try { File.Copy(selfExe, Path.Combine(gameDir, "GOLauncher.exe"), false); } catch { }
            foreach (string l0 in lines)
            {
                if (l0.Trim() == "") continue;
                bool launcher = l0.StartsWith("*");
                string rel = launcher ? l0.Substring(1) : l0;
                string src = Path.Combine(stage, rel);
                string dst = launcher && selfExe != null ? selfExe : Path.Combine(gameDir, rel.Replace('/', Path.DirectorySeparatorChar));
                Directory.CreateDirectory(Path.GetDirectoryName(dst));
                if (File.Exists(dst))
                {
                    if (launcher)
                    {   // a running exe cannot be overwritten, but it can be renamed
                        string old = dst + ".old";
                        if (File.Exists(old)) try { File.Delete(old); } catch { }
                        File.Move(dst, old);
                    }
                }
                File.Copy(src, dst, true);
            }
            string cl = Path.Combine(stage, "clean.txt");
            if (File.Exists(cl)) Cleanup(gameDir, File.ReadAllLines(cl));
            string rm = Path.Combine(stage, "remove.txt");
            if (File.Exists(rm)) RemoveFiles(gameDir, File.ReadAllLines(rm));
            Directory.Delete(stage, true);
        }

        /// (2026-11-01) remove "<file>.orig" (copies of the original 1.8.5 files made by the old install_pam_fix.bat -
        /// about 280 MB) for every file of the release that is installed and correct.  Their content is no longer needed:
        /// the next update rebuilds from the installed file, whose chunks are what the next release mostly shares.
        public static void Cleanup(string gameDir, IEnumerable<string> paths)
        {
            foreach (string l in paths)
            {
                string rel = l.Trim();
                if (rel == "" || rel.Contains("..") || Path.IsPathRooted(rel)) continue;
                string f = Path.Combine(gameDir, rel.Replace('/', Path.DirectorySeparatorChar));
                if (File.Exists(f) && File.Exists(f + ".orig")) try { File.Delete(f + ".orig"); } catch { }
            }
        }

        public void Install()
        {
            OnStatus(Txt.Get("apply"));
            foreach (string name in new[] { "GO", "GO_debug", "SG", "SG_debug" })
                if (Process.GetProcessesByName(name).Length > 0) throw new UpdateException("running", "game running");
            string oldV = Ota.Str(State, "version", "?");
            if (Writable(GameDir))
            {
                Apply(StageDir, GameDir, SelfExe, oldV);
                return;
            }
            ProcessStartInfo p = new ProcessStartInfo(SelfExe, "--apply \"" + StageDir + "\" --dir \"" + GameDir + "\" --from \"" + oldV + "\"");
            p.Verb = "runas"; p.UseShellExecute = true;
            Process pr;
            try { pr = Process.Start(p); }
            catch (Exception) { throw new UpdateException("admin", "UAC declined"); }
            pr.WaitForExit();
            if (pr.ExitCode != 0) throw new UpdateException("fail", "install (exit " + pr.ExitCode + ")");
        }

        public void WriteServer()
        {
            Dictionary<string, object> s = Ota.Obj(Manifest, "server");
            string ip = Ota.Str(s, "ip", "");
            if (ip == "") return;
            try
            {
                using (RegistryKey k = Registry.CurrentUser.CreateSubKey(@"SOFTWARE\Galactic Overlord"))
                    k.SetValue("REG_SG_IP", ip, RegistryValueKind.String);
            }
            catch (Exception e) { OnLog("registry: " + e.Message); }
            State["server"] = ip;
        }

        /// the copy a self-update renamed away (a running exe cannot be overwritten).  (user 11-02 17:38) also the old
        /// SGLauncher.exe.old: after the move to GOLauncher.exe this exe is no longer the one that left it
        void DeleteOld()
        {
            foreach (string o in new[] { SelfExe != null ? SelfExe + ".old" : null, Path.Combine(GameDir, "SGLauncher.exe.old"), Path.Combine(GameDir, "GOLauncher.exe.old") })
                try { if (o != null && File.Exists(o)) { File.SetAttributes(o, FileAttributes.Normal); File.Delete(o); } } catch { }
        }

        /// whole update; returns the status line to show
        public string Run()
        {
            DeleteOld();
            LoadManifest();
            WriteServer();
            List<Item> need = Plan();
            SaveState();
            if (need.Count == 0)
            {
                // everything is correct: the old copies can go now (only when no administrator rights are needed;
                // otherwise at the next update, which asks for them anyway)
                if (Writable(GameDir))
                {
                    Cleanup(GameDir, ManifestPaths());
                    RemoveFiles(GameDir, RemovePaths());
                    string bdir = Path.Combine(GameDir, "SGLauncher.backup");
                    if (Directory.Exists(bdir)) try { Directory.Delete(bdir, true); } catch { }
                }
                else RemoveElevated();
                State["version"] = Version; SaveState();
                return Txt.Get("ready", Version);
            }
            Stage(need);
            Install();
            State["version"] = Version;
            SaveState();
            foreach (Item it in need) if (it.IsLauncher) SelfUpdated = true;
            return Txt.Get("updated", Version);
        }

        /// files to remove in a folder that needs administrator rights (Program Files) and nothing to install: one
        /// elevated --apply with an empty file list, once per release (a declined prompt is not asked again until the
        /// next release; the game still starts)
        void RemoveElevated()
        {
            List<string> pending = RemovePending();
            if (pending.Count == 0 || Ota.Str(State, "removed_for", "") == Version) return;
            State["removed_for"] = Version; SaveState();
            try
            {
                if (Directory.Exists(StageDir)) Directory.Delete(StageDir, true);
                Directory.CreateDirectory(StageDir);
                File.WriteAllLines(Path.Combine(StageDir, "apply.txt"), new string[0]);
                File.WriteAllLines(Path.Combine(StageDir, "remove.txt"), pending.ToArray());
                Install();
            }
            catch (Exception e) { OnLog("remove: " + e.Message); }
        }

        public string Notes()
        {
            Dictionary<string, object> n = Ota.Obj(Manifest, "notes");
            return Ota.Str(n, Txt.Lang, Ota.Str(n, "zh-cn", ""));
        }

        public string StartExe()
        {
            string s = Manifest != null ? Ota.Str(Manifest, "start", "GO.exe") : "GO.exe";
            return Path.Combine(GameDir, s);
        }
    }

    class LauncherForm : Form
    {
        Updater up;
        Label status = new Label();
        ProgressBar bar = new ProgressBar();
        TextBox notes = new TextBox();
        Button play = new Button(), retry = new Button(), quit = new Button();
        string gameDir, urlOverride, channel;

        public LauncherForm(string gameDir, string urlOverride, string channel)
        {
            this.gameDir = gameDir; this.urlOverride = urlOverride; this.channel = channel;
            Font = new Font("Microsoft YaHei", 9f);
            ClientSize = new Size(520, 330);
            FormBorderStyle = FormBorderStyle.FixedSingle; MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }   /* (11-02 17:47) the horizon icon (launcher.res) */
            status.SetBounds(16, 14, 488, 40); status.AutoSize = false;
            bar.SetBounds(16, 58, 488, 18);
            notes.SetBounds(16, 88, 488, 186); notes.Multiline = true; notes.ReadOnly = true; notes.ScrollBars = ScrollBars.Vertical;
            play.SetBounds(298, 286, 100, 30); retry.SetBounds(192, 286, 100, 30); quit.SetBounds(404, 286, 100, 30);
            play.Enabled = false; retry.Visible = false;
            play.Click += delegate { StartGame(); };
            retry.Click += delegate { Begin(); };
            quit.Click += delegate { Close(); };
            Controls.AddRange(new Control[] { status, bar, notes, play, retry, quit });
            Shown += delegate { Begin(); };
        }

        void Ui(Action a) { if (IsHandleCreated) BeginInvoke(a); }

        void Begin()
        {
            retry.Visible = false; play.Enabled = false;
            try
            {
                up = new Updater(gameDir, Application.ExecutablePath, urlOverride, channel);
            }
            catch (Exception e) { status.Text = Txt.Get("fail", e.Message); retry.Visible = true; return; }
            Text = Txt.Get("title"); play.Text = Txt.Get("play"); retry.Text = Txt.Get("retry"); quit.Text = Txt.Get("exit");
            if (!Updater.LooksLikeGameDir(gameDir)) { status.Text = Txt.Get("nogame"); return; }
            up.OnStatus = s => Ui(() => status.Text = s);
            up.OnProgress = (d, t) => Ui(() => { bar.Maximum = 1000; bar.Value = t > 0 ? (int)Math.Min(1000, d * 1000 / t) : 0; status.Text = status.Text.Split(new char[] { '(' })[0].TrimEnd(new char[] { ' ' }) + (t > 0 ? string.Format("  ({0:0.0} / {1:0.0} MB)", d / 1048576.0, t / 1048576.0) : ""); });
            Thread th = new Thread(() =>
            {
                string msg; bool canPlay = true, again = false;
                try { msg = up.Run(); }
                catch (UpdateException e) { msg = e.Key == "fail" ? Txt.Get("fail", e.Message) : Txt.Get(e.Key); canPlay = e.Key == "offline" || e.Key == "admin"; again = true; }
                catch (Exception e) { msg = Txt.Get("fail", e.Message); again = true; }
                Ui(() =>
                {
                    status.Text = msg;
                    if (up.Manifest != null) notes.Text = Txt.Get("notes") + " " + up.Version + "\r\n\r\n" + up.Notes();
                    bar.Value = canPlay && !again ? bar.Maximum : bar.Value;
                    play.Enabled = canPlay; retry.Visible = again;
                    if (up.SelfUpdated)
                    {
                        status.Text = Txt.Get("self");
                        Process.Start(Application.ExecutablePath);
                        Close();
                    }
                });
            });
            th.IsBackground = true;
            th.Start();
        }

        /// UDP relay (claude/UDP_RELAY.md): GORelay.exe (was SGRelay.exe) in the game folder carries the game connection over UDP.
        /// It answers READY (and points REG_SG_IP at 127.0.0.1 itself) or FAIL - then the game connects directly.
        void StartRelay()
        {
            try
            {
                Dictionary<string, object> srv = up.Manifest != null ? Ota.Obj(up.Manifest, "server") : null;
                string ip = srv != null ? Ota.Str(srv, "ip", "") : "";
                long port = srv != null ? Ota.Long(srv, "relay_port", 0) : 0;
                string exe = Path.Combine(gameDir, "GORelay.exe");
                if (!File.Exists(exe)) exe = Path.Combine(gameDir, "SGRelay.exe");                    // (a folder not updated yet)
                if (ip == "" || port <= 0 || !File.Exists(exe) || File.Exists(Path.Combine(gameDir, "norelay.txt"))) return;
                if (Process.GetProcessesByName("GORelay").Length > 0 || Process.GetProcessesByName("SGRelay").Length > 0) return;          // already running (second game window)
                ProcessStartInfo r = new ProcessStartInfo(exe, "--server " + ip + " --port " + port);
                r.UseShellExecute = false; r.CreateNoWindow = true; r.RedirectStandardOutput = true;
                r.WorkingDirectory = gameDir;
                Process pr = Process.Start(r);
                string line = null;
                Thread t = new Thread(() => { try { line = pr.StandardOutput.ReadLine(); } catch { } });
                t.IsBackground = true; t.Start();
                if (!t.Join(4000) || line == null || !line.StartsWith("READY"))
                {
                    try { if (!pr.HasExited) pr.Kill(); } catch { }
                    up.WriteServer();                                                  // direct connection
                }
            }
            catch (Exception) { try { up.WriteServer(); } catch { } }
        }

        void StartGame()
        {
            try
            {
                StartRelay();
                ProcessStartInfo p = new ProcessStartInfo(up.StartExe());
                p.WorkingDirectory = gameDir;
                Process.Start(p);
                Close();
            }
            catch (Exception e) { status.Text = Txt.Get("fail", e.Message); }
        }
    }

    static class Program
    {
        [System.Runtime.InteropServices.DllImport("kernel32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
        static extern uint GetLongPathName(string s, StringBuilder l, uint n);

        static string LongPath(string p)
        {
            try { StringBuilder b = new StringBuilder(1024); uint n = GetLongPathName(p, b, 1024); return Path.GetFullPath(n > 0 && n < 1024 ? b.ToString() : p); }
            catch { return p; }
        }

        /// (2026-11-02, user "SG 改成 GO"): run as SGLauncher.exe -> copy this (stamped) exe to GOLauncher.exe, point the
        /// shortcuts that open SG.exe / SG_debug.exe / SGLauncher.exe of this folder at GOLauncher.exe, start GOLauncher.exe
        /// and end; the release's "remove" list deletes SGLauncher.exe at a later start.  false = go on as we are.
        static bool MoveToGoName(string self, string dir, string[] args)
        {
            if (!string.Equals(Path.GetFileName(self), "SGLauncher.exe", StringComparison.OrdinalIgnoreCase)) return false;
            string go = Path.Combine(dir, "GOLauncher.exe");
            if (!File.Exists(go))                                             // (an existing one may be newer: kept)
                try { File.Copy(self, go, false); } catch { return false; }   // (Program Files without rights: stay SGLauncher)
            try { MoveShortcuts(dir, go); } catch { }
            try
            {
                StringBuilder a = new StringBuilder();
                foreach (string s in args) a.Append(" \"").Append(s).Append("\"");
                ProcessStartInfo p = new ProcessStartInfo(go, a.ToString().Trim()); p.WorkingDirectory = dir;
                Process.Start(p);
                return true;
            }
            catch { return false; }
        }

        static void MoveShortcuts(string dir, string go)
        {
            string gdir = LongPath(dir).TrimEnd('\\');
            string[] old = { "SG.exe", "SG_debug.exe", "SGLauncher.exe" };
            Type ws = Type.GetTypeFromProgID("WScript.Shell");
            if (ws == null) return;
            object sh = Activator.CreateInstance(ws);
            List<string> roots = new List<string>();
            foreach (Environment.SpecialFolder f in new[] { Environment.SpecialFolder.DesktopDirectory, Environment.SpecialFolder.CommonDesktopDirectory,
                                                            Environment.SpecialFolder.Programs, Environment.SpecialFolder.CommonPrograms })
                try { string r = Environment.GetFolderPath(f); if (r != "" && Directory.Exists(r)) roots.Add(r); } catch { }
            foreach (string r in roots)
            {
                string[] lnks;
                try { lnks = Directory.GetFiles(r, "*.lnk", SearchOption.AllDirectories); } catch { continue; }
                foreach (string l in lnks)
                {
                    try
                    {
                        object k = ws.InvokeMember("CreateShortcut", System.Reflection.BindingFlags.InvokeMethod, null, sh, new object[] { l });
                        Type kt = k.GetType();
                        string target = (string)kt.InvokeMember("TargetPath", System.Reflection.BindingFlags.GetProperty, null, k, null);
                        if (string.IsNullOrEmpty(target)) continue;
                        string tname = Path.GetFileName(target);
                        bool ours = false;
                        foreach (string o in old) if (string.Equals(tname, o, StringComparison.OrdinalIgnoreCase)) ours = true;
                        if (!ours || !string.Equals(LongPath(Path.GetDirectoryName(target)).TrimEnd('\\'), gdir, StringComparison.OrdinalIgnoreCase)) continue;
                        kt.InvokeMember("TargetPath", System.Reflection.BindingFlags.SetProperty, null, k, new object[] { go });
                        kt.InvokeMember("WorkingDirectory", System.Reflection.BindingFlags.SetProperty, null, k, new object[] { dir });
                        kt.InvokeMember("Arguments", System.Reflection.BindingFlags.SetProperty, null, k, new object[] { "" });
                        kt.InvokeMember("IconLocation", System.Reflection.BindingFlags.SetProperty, null, k, new object[] { go + ",0" });
                        kt.InvokeMember("Save", System.Reflection.BindingFlags.InvokeMethod, null, k, null);
                    }
                    catch { }
                }
            }
        }

        [STAThread]
        static int Main(string[] args)
        {
            ServicePointManager.DefaultConnectionLimit = 8;
            string dir = null, url = null, ch = null, apply = null, from = null;
            bool check = false;
            for (int i = 0; i < args.Length; i++)
            {
                string a = args[i];
                string v = i + 1 < args.Length ? args[i + 1] : null;
                if (a == "--dir") { dir = v; i++; }
                else if (a == "--url") { url = v; i++; }
                else if (a == "--channel") { ch = v; i++; }
                else if (a == "--apply") { apply = v; i++; }
                else if (a == "--from") { from = v; i++; }
                else if (a == "--check") check = true;
            }
            string self = Path.GetFullPath(System.Reflection.Assembly.GetExecutingAssembly().Location);
            if (dir == null) dir = Path.GetDirectoryName(self);
            if (apply == null && !check && MoveToGoName(self, dir, args)) return 0;
            if (apply != null)
            {
                try { Updater.Apply(apply, dir, self, from); return 0; }
                catch (Exception e) { try { File.WriteAllText(Path.Combine(apply, "apply_error.txt"), e.ToString()); } catch { } return 3; }
            }
            if (check)
            {
                try
                {
                    Updater u = new Updater(dir, self, url, ch);
                    u.OnStatus = s => Console.WriteLine("status: " + s);
                    u.OnLog = s => Console.WriteLine("log: " + s);
                    long lastp = -1;
                    u.OnProgress = (d, t) => { long p = t > 0 ? d * 10 / t : 10; if (p != lastp) { lastp = p; Console.WriteLine("progress: " + d + "/" + t); } };
                    Console.WriteLine(u.Run());
                    Console.WriteLine("version=" + u.Version + " channel=" + u.Channel + " selfupdated=" + u.SelfUpdated);
                    return 0;
                }
                catch (UpdateException e) { Console.WriteLine("ERROR " + e.Key + ": " + e.Message); return 1; }
                catch (Exception e) { Console.WriteLine("ERROR: " + e); return 1; }
            }
            Application.EnableVisualStyles();
            Application.Run(new LauncherForm(dir, url, ch));
            return 0;
        }
    }
}
