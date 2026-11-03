// SGPublish: builds a signed OTA release (2026-10-22, claude/OTA_PLAN.md).  Run by deploy\publish.ps1.
//   SGPublish keygen  [--key FILE]                         RSA-2048 signing key (default %USERPROFILE%\.sgota\ota_key.json)
//   SGPublish build   --version V --url URL[,URL2] --server-ip IP [--port 3000] [--min V] [--deadline-hours H]
//                     [--notes TEXT] [--notes-tw TEXT] [--notes-en TEXT] [--files deploy\ota_files.json]
//                     [--launcher launcher\SGLauncher.exe] (published as GOLauncher.exe since 2026-11-02) [--out out\ota] [--key FILE] [--force] [--all]
//                     -> out\ota\stage\  (only objects the server does not have yet + manifests + release.json)
//   SGPublish commit  [--out out\ota]                      after a successful upload: remember the uploaded objects
//   SGPublish verify  DIR [--key FILE]                     check every manifest signature / object hash in DIR
//   SGPublish stamp   --launcher IN --url URL --out FILE   stamped launcher only (for a first install package)
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace SGOta
{
    static class Publish
    {
        static Dictionary<string, string> opt = new Dictionary<string, string>();
        static List<string> pos = new List<string>();

        static string O(string k, string def) { string v; return opt.TryGetValue(k, out v) ? v : def; }

        static int Main(string[] args)
        {
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i].StartsWith("--"))
                {
                    string k = args[i].Substring(2);
                    if (k == "force" || k == "all") opt[k] = "1";
                    else if (i + 1 < args.Length) opt[k] = args[++i];
                }
                else pos.Add(args[i]);
            }
            if (pos.Count == 0) { Console.WriteLine("usage: SGPublish keygen|build|commit|verify|stamp (see the source header)"); return 2; }
            try
            {
                switch (pos[0])
                {
                    case "keygen": return Keygen();
                    case "build": return Build();
                    case "commit": return Commit();
                    case "verify": return VerifyDir(pos.Count > 1 ? pos[1] : Path.Combine(O("out", Path.Combine("out", "ota")), "stage"));
                    case "stamp": return StampOnly();
                }
                Console.WriteLine("unknown command " + pos[0]);
                return 2;
            }
            catch (Exception e)
            {
                Console.Error.WriteLine("ERROR: " + e.Message);
                return 1;
            }
        }

        static string KeyPath()
        {
            string home = Environment.GetEnvironmentVariable("USERPROFILE") ?? Environment.GetEnvironmentVariable("HOME") ?? ".";
            return O("key", Path.Combine(Path.Combine(home, ".sgota"), "ota_key.json"));
        }

        static int Keygen()
        {
            string p = KeyPath();
            if (File.Exists(p)) { Console.WriteLine("key already exists: " + p + "  (keep it: the launchers trust only this key)"); return 0; }
            RSAParameters k;
            using (RSACryptoServiceProvider r = new RSACryptoServiceProvider(2048)) { r.PersistKeyInCsp = false; k = r.ExportParameters(true); }
            Dictionary<string, object> d = new Dictionary<string, object>();
            d["n"] = Convert.ToBase64String(k.Modulus);
            d["e"] = Convert.ToBase64String(k.Exponent);
            d["d"] = Convert.ToBase64String(k.D);
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(p)));
            File.WriteAllText(p, Ota.Json().Serialize(d));
            // self test
            byte[] msg = Encoding.UTF8.GetBytes("selftest");
            if (!Ota.Verify(msg, Ota.Sign(msg, k.Modulus, k.D), k.Modulus, k.Exponent)) throw new Exception("key self test failed");
            Console.WriteLine("signing key written: " + p);
            Console.WriteLine("BACK IT UP (and never put it in the repo): without it no launcher accepts a new release.");
            return 0;
        }

        static Dictionary<string, object> LoadKey()
        {
            string p = KeyPath();
            if (!File.Exists(p)) throw new Exception("no signing key " + p + " - run: SGPublish keygen");
            return Ota.ParseObj(File.ReadAllText(p));
        }

        static byte[] K(Dictionary<string, object> key, string f) { return Convert.FromBase64String(Ota.Str(key, f, "")); }

        static byte[] StampLauncher(string launcher, Dictionary<string, object> key, string[] urls)
        {
            byte[] exe = Ota.Unstamped(File.ReadAllBytes(launcher));
            Dictionary<string, object> st = new Dictionary<string, object>();
            st["n"] = Ota.Str(key, "n", "");
            st["e"] = Ota.Str(key, "e", "");
            st["urls"] = urls;
            byte[] tail = Encoding.UTF8.GetBytes(Ota.StampMark + Ota.Json().Serialize(st));
            byte[] r = new byte[exe.Length + tail.Length];
            Buffer.BlockCopy(exe, 0, r, 0, exe.Length);
            Buffer.BlockCopy(tail, 0, r, exe.Length, tail.Length);
            return r;
        }

        static string[] Urls()
        {
            string u = O("url", "");
            if (u == "") throw new Exception("--url missing (e.g. http://43.135.15.91:3001)");
            string[] a = u.Split(new char[] { ',' });
            for (int i = 0; i < a.Length; i++) a[i] = a[i].Trim().TrimEnd(new char[] { '/' });
            return a;
        }

        static int StampOnly()
        {
            byte[] b = StampLauncher(O("launcher", Path.Combine("launcher", "SGLauncher.exe")), LoadKey(), Urls());
            File.WriteAllBytes(O("out", "GOLauncher.exe"), b);
            Console.WriteLine("stamped launcher -> " + O("out", "GOLauncher.exe"));
            return 0;
        }

        static HashSet<string> Published(string outDir, out Dictionary<string, object> state)
        {
            string p = Path.Combine(outDir, "published.json");
            state = File.Exists(p) ? Ota.ParseObj(File.ReadAllText(p)) : new Dictionary<string, object>();
            HashSet<string> s = new HashSet<string>();
            foreach (object o in Ota.Arr(state, "objects")) s.Add((string)o);
            return s;
        }

        static void AddObject(string stage, HashSet<string> have, HashSet<string> added, string sha, string src, byte[] data)
        {
            if (have.Contains(sha) || added.Contains(sha)) return;
            string dst = Path.Combine(Path.Combine(stage, "objects"), sha);
            if (data != null) File.WriteAllBytes(dst, data); else File.Copy(src, dst, true);
            added.Add(sha);
        }

        static int Build()
        {
            string ver = O("version", "");
            if (ver == "" || ver.Split(new char[] { '.' }).Length < 2) throw new Exception("--version like 1.0.3 required");
            string outDir = O("out", Path.Combine("out", "ota"));
            string stage = Path.Combine(outDir, "stage");
            Dictionary<string, object> key = LoadKey();
            byte[] n = K(key, "n"), d = K(key, "d"), e = K(key, "e");
            Dictionary<string, object> state;
            HashSet<string> have = Published(outDir, out state);
            string last = Ota.Str(state, "version", "0");
            if (O("all", "") != "") have.Clear();               // --all: upload every object again (new / wiped server)
            if (Ota.Cmp(ver, last) <= 0 && O("force", "") == "")
                throw new Exception("version " + ver + " is not newer than the last published " + last + " (use --force to republish)");
            if (Directory.Exists(stage)) Directory.Delete(stage, true);
            Directory.CreateDirectory(Path.Combine(stage, "objects"));
            Directory.CreateDirectory(Path.Combine(Path.Combine(stage, "versions"), ver));
            Directory.CreateDirectory(Path.Combine(stage, "launcher"));
            HashSet<string> added = new HashSet<string>();

            // launcher (stamped with the public key + download URLs)
            byte[] lb = StampLauncher(O("launcher", Path.Combine("launcher", "SGLauncher.exe")), key, Urls());
            string lsha = Ota.Sha256(lb, 0, lb.Length);
            AddObject(stage, have, added, lsha, null, lb);
            File.WriteAllBytes(Path.Combine(Path.Combine(stage, "launcher"), "GOLauncher.exe"), lb);

            Dictionary<string, object> cfg = Ota.ParseObj(File.ReadAllText(O("files", Path.Combine("deploy", "ota_files.json"))));
            string root = Path.GetDirectoryName(Path.GetFullPath(O("files", Path.Combine("deploy", "ota_files.json"))));
            root = Path.GetFullPath(Path.Combine(root, Ota.Str(cfg, "root", "..")));
            Dictionary<string, object> common = Ota.Obj(cfg, "common") ?? new Dictionary<string, object>();
            Dictionary<string, object> chans = Ota.Obj(cfg, "channels");
            if (chans == null || chans.Count == 0) throw new Exception("ota_files.json: no channels");

            double deadline = 0;
            if (O("deadline-hours", "") != "")
                deadline = (DateTime.UtcNow - new DateTime(1970, 1, 1)).TotalSeconds + double.Parse(O("deadline-hours", "0"), System.Globalization.CultureInfo.InvariantCulture) * 3600;
            Dictionary<string, object> notes = new Dictionary<string, object>();
            notes["zh-cn"] = O("notes", "");
            notes["zh-tw"] = O("notes-tw", O("notes", ""));
            notes["en"] = O("notes-en", O("notes", ""));
            Dictionary<string, object> server = new Dictionary<string, object>();
            server["ip"] = O("server-ip", "");
            server["port"] = int.Parse(O("port", "3000"));
            server["relay_port"] = int.Parse(O("relay-port", "3002"));     // UDP relay (SGRelay.exe), 0 = off
            if (Ota.Str(server, "ip", "") == "") throw new Exception("--server-ip missing");

            Dictionary<string, string[]> hcache = new Dictionary<string, string[]>();   // src -> {sha, size, chunks...}
            Dictionary<string, string> ccache = new Dictionary<string, string>();       // src -> sha of its cdc object
            foreach (KeyValuePair<string, object> ch in chans)
            {
                List<object> files = new List<object>();
                Dictionary<string, object> all = new Dictionary<string, object>();
                foreach (KeyValuePair<string, object> kv in common) all[kv.Key] = kv.Value;
                foreach (KeyValuePair<string, object> kv in (Dictionary<string, object>)ch.Value) all[kv.Key] = kv.Value;
                foreach (KeyValuePair<string, object> kv in all)
                {
                    string src; bool client = false;
                    Dictionary<string, object> eo = kv.Value as Dictionary<string, object>;
                    if (eo != null) { src = Ota.Str(eo, "src", ""); client = Ota.Str(eo, "client", "") == "True"; }
                    else src = (string)kv.Value;
                    string full = Path.GetFullPath(Path.Combine(root, src));
                    if (!File.Exists(full)) throw new Exception("missing file " + full + " (" + ch.Key + ":" + kv.Key + ")");
                    string[] h;
                    if (!hcache.TryGetValue(full, out h))
                    {
                        List<string> chunks = new List<string>();
                        string sha = Ota.HashFile(full, chunks);
                        List<string> l = new List<string>();
                        l.Add(sha); l.Add(new FileInfo(full).Length.ToString()); l.AddRange(chunks);
                        h = l.ToArray(); hcache[full] = h;
                    }
                    AddObject(stage, have, added, h[0], full, null);
                    string cdcSha;
                    if (!ccache.TryGetValue(full, out cdcSha))
                    {   // content-defined chunk list: lets the launcher reuse the player's own (original / older) files
                        byte[] cb = Ota.CdcBlob(Ota.Cdc(full));
                        cdcSha = Ota.Sha256(cb, 0, cb.Length);
                        AddObject(stage, have, added, cdcSha, null, cb);
                        ccache[full] = cdcSha;
                    }
                    Dictionary<string, object> fe = new Dictionary<string, object>();
                    fe["path"] = kv.Key.Replace('\\', '/');
                    fe["size"] = long.Parse(h[1]);
                    fe["sha256"] = h[0];
                    string[] cs = new string[h.Length - 2];
                    Array.Copy(h, 2, cs, 0, cs.Length);
                    fe["chunks"] = cs;
                    fe["cdc"] = cdcSha;
                    if (client) fe["client"] = true;
                    files.Add(fe);
                }
                Dictionary<string, object> m = new Dictionary<string, object>();
                m["version"] = ver;
                m["min_version"] = O("min", "");
                m["channel"] = ch.Key;
                m["created"] = (long)(DateTime.UtcNow - new DateTime(1970, 1, 1)).TotalSeconds;
                m["chunk"] = Ota.Chunk;
                m["start"] = Ota.Str(cfg, "start", "GO.exe");
                m["server"] = server;
                m["notes"] = notes;
                Dictionary<string, object> lm = new Dictionary<string, object>();
                lm["sha256"] = lsha; lm["size"] = lb.Length;
                m["launcher"] = lm;
                m["files"] = files;
                // (2026-11-01) files of older releases the launcher deletes from the game folder: ota_files.json "remove"
                // (exact relative paths; a file still in this channel's list is never removed)
                List<object> rm = new List<object>();
                foreach (object ro in Ota.Arr(cfg, "remove"))
                {
                    string rp = ((string)ro).Replace('\\', '/').Trim();
                    if (rp == "" || rp.Contains("..") || Path.IsPathRooted(rp) || rp.IndexOfAny(new char[] { '*', '?' }) >= 0)
                        throw new Exception("ota_files.json remove: bad path " + rp);
                    bool listed = false;
                    foreach (KeyValuePair<string, object> kv in all) if (string.Equals(kv.Key.Replace('\\', '/'), rp, StringComparison.OrdinalIgnoreCase)) listed = true;
                    if (!listed) rm.Add(rp);
                }
                m["remove"] = rm;
                byte[] mb = Encoding.UTF8.GetBytes(Ota.Json().Serialize(m));
                byte[] sig = Encoding.ASCII.GetBytes(Convert.ToBase64String(Ota.Sign(mb, n, d)));
                if (!Ota.Verify(mb, Convert.FromBase64String(Encoding.ASCII.GetString(sig)), n, e)) throw new Exception("signature self test failed");
                foreach (string dir in new string[] { stage, Path.Combine(Path.Combine(stage, "versions"), ver) })
                {
                    File.WriteAllBytes(Path.Combine(dir, "manifest-" + ch.Key + ".json"), mb);
                    File.WriteAllBytes(Path.Combine(dir, "manifest-" + ch.Key + ".json.sig"), sig);
                }
                Console.WriteLine("  " + ch.Key + ": " + files.Count + " files");
            }
            Dictionary<string, object> rel = new Dictionary<string, object>();
            rel["version"] = ver;
            rel["min_version"] = O("min", "");
            rel["deadline"] = deadline > 0 ? (object)(long)deadline : null;
            rel["notes"] = notes;
            File.WriteAllText(Path.Combine(stage, "release.json"), Ota.Json().Serialize(rel));
            File.WriteAllText(Path.Combine(Path.Combine(Path.Combine(stage, "versions"), ver), "release.json"), Ota.Json().Serialize(rel));
            long bytes = 0;
            foreach (string f in Directory.GetFiles(Path.Combine(stage, "objects"))) bytes += new FileInfo(f).Length;
            File.WriteAllText(Path.Combine(stage, "objects.txt"), string.Join("\n", new List<string>(added).ToArray()));
            Console.WriteLine("release " + ver + " staged in " + stage + ": " + added.Count + " new object(s), " + (bytes / 1048576.0).ToString("0.0") + " MB to upload");
            return 0;
        }

        static int Commit()
        {
            string outDir = O("out", Path.Combine("out", "ota"));
            string stage = Path.Combine(outDir, "stage");
            Dictionary<string, object> state;
            HashSet<string> have = Published(outDir, out state);
            Dictionary<string, object> rel = Ota.ParseObj(File.ReadAllText(Path.Combine(stage, "release.json")));
            foreach (string f in Directory.GetFiles(Path.Combine(stage, "objects"))) have.Add(Path.GetFileName(f));
            List<string> l = new List<string>(have);
            l.Sort();
            state["objects"] = l.ToArray();
            state["version"] = Ota.Str(rel, "version", "");
            List<object> hist = Ota.Arr(state, "history");
            hist.Add(Ota.Str(rel, "version", "") + " " + DateTime.Now.ToString("yyyy-MM-dd HH:mm"));
            state["history"] = hist.ToArray();
            File.WriteAllText(Path.Combine(outDir, "published.json"), Ota.Json().Serialize(state));
            Directory.Delete(stage, true);
            Console.WriteLine("published " + Ota.Str(rel, "version", ""));
            return 0;
        }

        static int VerifyDir(string dir)
        {
            Dictionary<string, object> key = LoadKey();
            byte[] n = K(key, "n"), e = K(key, "e");
            int bad = 0;
            foreach (string mf in Directory.GetFiles(dir, "manifest-*.json"))
            {
                byte[] mb = File.ReadAllBytes(mf);
                bool ok = Ota.Verify(mb, Convert.FromBase64String(File.ReadAllText(mf + ".sig").Trim()), n, e);
                Console.WriteLine(Path.GetFileName(mf) + ": signature " + (ok ? "OK" : "BAD"));
                if (!ok) bad++;
                foreach (object fo in Ota.Arr(Ota.ParseObj(Encoding.UTF8.GetString(mb)), "files"))
                {
                    Dictionary<string, object> f = (Dictionary<string, object>)fo;
                    string obj = Path.Combine(Path.Combine(dir, "objects"), Ota.Str(f, "sha256", ""));
                    if (File.Exists(obj) && Ota.Sha256File(obj) != Ota.Str(f, "sha256", "")) { Console.WriteLine("  BAD object " + obj); bad++; }
                }
            }
            return bad == 0 ? 0 : 1;
        }
    }
}
