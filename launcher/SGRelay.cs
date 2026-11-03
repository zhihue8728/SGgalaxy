// GORelay.exe (source SGRelay.cs; was SGRelay.exe until 2026-11-02) (2026-10-26, claude/UDP_RELAY.md): the player's side of the UDP relay.
// The game connects to 127.0.0.1:3000 (REG_SG_IP = 127.0.0.1); every TCP connection is carried to the server over UDP
// (protocol = server/udp_relay.py: every datagram with new bytes is sent twice, holes are re-sent at once, RTO last).
// usage: GORelay.exe --server 43.135.15.91 --port 3002 [--listen 3000] [--no-registry]
//   prints READY (stdout) when the server answered and 127.0.0.1:<listen> is open, then sets REG_SG_IP = 127.0.0.1;
//   prints FAIL <reason> and exits 2/3 when UDP does not get through / the port is taken (launcher: connect directly).
//   Exits when no GO.exe / GO_debug.exe (or an older SG.exe) has run for 20 s, and then sets REG_SG_IP back to the server address.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using Microsoft.Win32;

namespace SGRelay
{
    static class P
    {
        public const byte T_HELLO = 1, T_HELLO_OK = 2, T_DATA = 3, T_ACK = 4, T_FIN = 5, T_PING = 6, T_PONG = 7, T_RST = 8;
        public const int HDR = 12, MAX_CHUNK = 1150, RESEND_BURST = 16;
        public static byte[] Pack(byte t, ulong sid, byte[] body, int off, int n)
        {
            byte[] d = new byte[HDR + n];
            d[0] = (byte)'S'; d[1] = (byte)'R'; d[2] = 1; d[3] = t;
            for (int i = 0; i < 8; i++) d[4 + i] = (byte)(sid >> (56 - 8 * i));
            if (n > 0) Buffer.BlockCopy(body, off, d, HDR, n);
            return d;
        }
        public static void PutU32(byte[] b, int o, long v) { uint u = (uint)v; b[o] = (byte)(u >> 24); b[o + 1] = (byte)(u >> 16); b[o + 2] = (byte)(u >> 8); b[o + 3] = (byte)u; }
        public static uint U32(byte[] b, int o) { return ((uint)b[o] << 24) | ((uint)b[o + 1] << 16) | ((uint)b[o + 2] << 8) | b[o + 3]; }
        public static ulong Sid(byte[] d) { ulong s = 0; for (int i = 0; i < 8; i++) s = (s << 8) | d[4 + i]; return s; }
        static readonly Stopwatch sw = Stopwatch.StartNew();
        public static double Now { get { return sw.Elapsed.TotalSeconds; } }
        public static long Unwrap(uint v, long reference)
        {
            const long MOD = 1L << 32;
            long c = reference - (reference % MOD) + v;
            if (c - reference > MOD / 2) c -= MOD; else if (reference - c > MOD / 2) c += MOD;
            return c;
        }
    }

    /// reliable ordered bytes over datagrams - the same algorithm as Stream in server/udp_relay.py
    class Stream
    {
        public delegate void Out(byte t, byte[] body, int n);
        readonly Out output; readonly Action<byte[], int, int> deliver;
        byte[] tx = new byte[65536]; int txLen;           // bytes from una
        public long una, nxt, rcv;
        readonly SortedDictionary<long, byte[]> ooo = new SortedDictionary<long, byte[]>();
        double srtt = -1, rttvar, rto = 0.25, rtoAt = -1, fastAt, dupAt = -1;
        readonly List<double[]> dup3 = new List<double[]>();   // third copies of small writes {from, to, when}
        long dupA, dupB;
        readonly List<double[]> sent = new List<double[]>();   // {end offset, time, retransmitted 0/1}
        public double LastTx;
        public long PeerFin = -1;
        public int Tx, Rx, Re, DupRx, Gaps;
        public Stream(Out o, Action<byte[], int, int> d) { output = o; deliver = d; }

        public void Write(byte[] b, int n)
        {
            if (n <= 0) return;
            double now = P.Now;
            if (txLen + n > tx.Length) { byte[] t2 = new byte[Math.Max(tx.Length * 2, txLen + n)]; Buffer.BlockCopy(tx, 0, t2, 0, txLen); tx = t2; }
            Buffer.BlockCopy(b, 0, tx, txLen, n); txLen += n;
            long a = nxt; nxt += n;
            sent.Add(new double[] { nxt, now, 0 });
            Send(a, nxt, int.MaxValue);
            if (dupAt >= 0 && dupB == a) dupB = nxt; else { dupA = a; dupB = nxt; dupAt = now + 0.020; }
            if (n <= 300) dup3.Add(new double[] { a, nxt, now + 0.060 });
            if (rtoAt < 0) rtoAt = now + rto;
        }
        void Send(long a, long b, int limit)
        {
            if (a < una) a = una;
            int k = 0;
            while (a < b && k < limit)
            {
                long e = Math.Min(b, a + P.MAX_CHUNK);
                int n = (int)(e - a);
                byte[] body = new byte[10 + n];
                P.PutU32(body, 0, rcv); P.PutU32(body, 4, a); body[8] = (byte)(n >> 8); body[9] = (byte)n;
                Buffer.BlockCopy(tx, (int)(a - una), body, 10, n);
                output(P.T_DATA, body, body.Length);
                Tx++; a = e; k++;
            }
            LastTx = P.Now;
        }
        void ResendFromUna() { foreach (double[] s in sent) s[2] = 1; Re++; Send(una, nxt, P.RESEND_BURST); }

        public void OnAck(uint wire, bool gap)
        {
            long ack = P.Unwrap(wire, una); double now = P.Now;
            if (ack > nxt) return;
            if (ack > una)
            {
                double sample = -1;
                while (sent.Count > 0 && sent[0][0] <= ack) { if (sent[0][2] == 0) sample = now - sent[0][1]; sent.RemoveAt(0); }
                if (sample >= 0)
                {
                    if (srtt < 0) { srtt = sample; rttvar = sample / 2; }
                    else { rttvar = 0.75 * rttvar + 0.25 * Math.Abs(srtt - sample); srtt = 0.875 * srtt + 0.125 * sample; }
                    rto = Math.Min(1.5, Math.Max(0.08, srtt * 1.2 + 2 * rttvar + 0.02));
                }
                int d = (int)(ack - una);
                Buffer.BlockCopy(tx, d, tx, 0, txLen - d); txLen -= d; una = ack;
                rtoAt = una < nxt ? now + rto : -1;
            }
            else if (gap && ack == una && una < nxt && now >= fastAt)
            {
                ResendFromUna(); fastAt = now + (srtt > 0 ? srtt : 0.2) * 0.8;
            }
        }
        public void Tick()
        {
            double now = P.Now;
            if (dupAt >= 0 && now >= dupAt) { dupAt = -1; if (dupB > una) Send(dupA, dupB, int.MaxValue); }
            while (dup3.Count > 0 && now >= dup3[0][2]) { double[] c = dup3[0]; dup3.RemoveAt(0); if ((long)c[1] > una) Send((long)c[0], (long)c[1], int.MaxValue); }
            if (rtoAt >= 0 && now >= rtoAt)
            {
                if (una < nxt) { ResendFromUna(); rto = Math.Min(1.5, rto * 1.5); rtoAt = now + rto; } else rtoAt = -1;
            }
        }
        public void OnData(byte[] d, int off, int len)
        {
            if (len < 10) return;
            uint ack = P.U32(d, off); long seq = P.Unwrap(P.U32(d, off + 4), rcv);
            int n = (d[off + 8] << 8) | d[off + 9];
            if (n > len - 10) return;
            Rx++;
            OnAck(ack, false);
            long end = seq + n;
            if (end <= rcv) DupRx++;
            else if (seq <= rcv) Take(d, off + 10 + (int)(rcv - seq), (int)(end - rcv));
            else { Gaps++; if (ooo.Count < 4096 && !ooo.ContainsKey(seq)) { byte[] c = new byte[n]; Buffer.BlockCopy(d, off + 10, c, 0, n); ooo[seq] = c; } }
            byte[] a = new byte[5]; P.PutU32(a, 0, rcv); a[4] = (byte)(ooo.Count > 0 ? 1 : 0);
            output(P.T_ACK, a, 5);
        }
        void Take(byte[] d, int off, int n)
        {
            rcv += n; deliver(d, off, n);
            while (ooo.Count > 0)
            {
                long k = -1; foreach (long x in ooo.Keys) { k = x; break; }
                if (k > rcv) break;
                byte[] c = ooo[k]; ooo.Remove(k);
                if (k + c.Length > rcv) { int skip = (int)(rcv - k); deliver(c, skip, c.Length - skip); rcv = k + c.Length; }
            }
        }
        public bool Idle { get { return una == nxt; } }
        public double Srtt { get { return srtt; } }
    }

    class Session
    {
        public ulong Sid; public TcpClient Tcp; public NetworkStream Net; public Stream S;
        public ManualResetEvent Ok = new ManualResetEvent(false);
        public volatile bool Closed; public double Start = P.Now;
    }

    static class Program
    {
        static UdpClient udp; static IPEndPoint server; static readonly object L = new object();
        static readonly Dictionary<ulong, Session> sessions = new Dictionary<ulong, Session>();
        static volatile bool pong; static string serverHost; static StreamWriter log;
        static readonly Random rnd = new Random();

        static void Log(string m)
        {
            try { lock (L) { if (log != null) { log.WriteLine(DateTime.Now.ToString("HH:mm:ss.fff") + " " + m); log.Flush(); } } } catch { }
        }

        static void SetRegistry(string ip)
        {
            try { using (RegistryKey k = Registry.CurrentUser.CreateSubKey(@"SOFTWARE\Galactic Overlord")) k.SetValue("REG_SG_IP", ip, RegistryValueKind.String); }
            catch (Exception e) { Log("registry: " + e.Message); }
        }

        static int Main(string[] args)
        {
            serverHost = null; int port = 3002, listen = 3000; bool reg = true;
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == "--server" && i + 1 < args.Length) serverHost = args[++i];
                else if (args[i] == "--port" && i + 1 < args.Length) port = int.Parse(args[++i]);
                else if (args[i] == "--listen" && i + 1 < args.Length) listen = int.Parse(args[++i]);
                else if (args[i] == "--no-registry") reg = false;
            }
            if (serverHost == null) { Console.WriteLine("FAIL usage: --server HOST [--port 3002]"); return 1; }
            try
            {
                string dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "GOLauncher");
                Directory.CreateDirectory(dir);
                log = new StreamWriter(Path.Combine(dir, "relay.log"), true);
            }
            catch { }
            try
            {
                IPAddress ip;
                if (!IPAddress.TryParse(serverHost, out ip)) ip = Dns.GetHostAddresses(serverHost)[0];
                server = new IPEndPoint(ip, port);
                udp = new UdpClient(0);
                try { udp.Client.IOControl(-1744830452, new byte[] { 0 }, null); } catch { }   // SIO_UDP_CONNRESET off
            }
            catch (Exception e) { Console.WriteLine("FAIL udp " + e.Message); return 2; }
            Thread rx = new Thread(RecvLoop); rx.IsBackground = true; rx.Start();
            // 1. probe: does UDP get through?
            for (int i = 0; i < 6 && !pong; i++)
            {
                Send(P.Pack(P.T_PING, 0, new byte[4], 0, 4));
                for (int k = 0; k < 25 && !pong; k++) Thread.Sleep(10);
            }
            if (!pong) { Console.WriteLine("FAIL no answer from " + server); Console.Out.Flush(); Log("no UDP answer from " + server); return 2; }
            TcpListener lst;
            try { lst = new TcpListener(IPAddress.Loopback, listen); lst.Start(); }
            catch (Exception e) { Console.WriteLine("FAIL listen " + e.Message); Console.Out.Flush(); return 3; }
            if (reg) SetRegistry("127.0.0.1");
            Log("relay ready: 127.0.0.1:" + listen + " -> udp " + server);
            Console.WriteLine("READY"); Console.Out.Flush();
            Thread tk = new Thread(TickLoop); tk.IsBackground = true; tk.Start();
            Thread ac = new Thread(() => { while (true) { try { TcpClient c = lst.AcceptTcpClient(); Thread t = new Thread(() => Serve(c)); t.IsBackground = true; t.Start(); } catch { return; } } });
            ac.IsBackground = true; ac.Start();
            // 2. live while the game runs
            double lastGame = P.Now;
            while (true)
            {
                Thread.Sleep(2000);
                if (Process.GetProcessesByName("GO").Length > 0 || Process.GetProcessesByName("GO_debug").Length > 0 ||
                    Process.GetProcessesByName("SG").Length > 0 || Process.GetProcessesByName("SG_debug").Length > 0) lastGame = P.Now;
                int n; lock (L) n = sessions.Count;
                if (n == 0 && P.Now - lastGame > 20) break;
            }
            if (reg) SetRegistry(serverHost);
            Log("relay exit (game closed)");
            return 0;
        }

        static void Send(byte[] d) { try { udp.Send(d, d.Length, server); } catch { } }

        static void Serve(TcpClient c)
        {
            c.NoDelay = true;
            Session s = new Session();
            byte[] r8 = new byte[8]; lock (rnd) rnd.NextBytes(r8);
            s.Sid = BitConverter.ToUInt64(r8, 0); s.Tcp = c; s.Net = c.GetStream();
            Session self = s;
            s.S = new Stream((t, b, n) => Send(P.Pack(t, self.Sid, b, 0, n)), (d, o, n) => { try { self.Net.Write(d, o, n); } catch { self.Closed = true; } });
            lock (L) sessions[s.Sid] = s;
            for (int i = 0; i < 20 && !s.Ok.WaitOne(0); i++) { Send(P.Pack(P.T_HELLO, s.Sid, null, 0, 0)); s.Ok.WaitOne(250); }
            if (!s.Ok.WaitOne(0)) { Log("no HELLO_OK"); Close(s); return; }
            Log("session " + s.Sid.ToString("x") + " open");
            byte[] buf = new byte[65536];
            try
            {
                while (!s.Closed)
                {
                    int n = s.Net.Read(buf, 0, buf.Length);
                    if (n <= 0) break;
                    lock (L) s.S.Write(buf, n);
                }
            }
            catch { }
            byte[] f = new byte[4]; lock (L) P.PutU32(f, 0, s.S.nxt);
            for (int i = 0; i < 3; i++) Send(P.Pack(P.T_FIN, s.Sid, f, 0, 4));
            Close(s);
        }

        static void Close(Session s)
        {
            lock (L)
            {
                if (!sessions.Remove(s.Sid)) return;
                Log(string.Format("session {0:x} closed after {1:0} s: rtt {2:0} ms, sent {3} ({4} resend rounds), received {5} ({6} duplicates, {7} after a gap)",
                    s.Sid, P.Now - s.Start, s.S.Srtt * 1000, s.S.Tx, s.S.Re, s.S.Rx, s.S.DupRx, s.S.Gaps));
            }
            s.Closed = true;
            try { s.Tcp.Close(); } catch { }
        }

        static void RecvLoop()
        {
            IPEndPoint from = new IPEndPoint(IPAddress.Any, 0);
            while (true)
            {
                byte[] d;
                try { d = udp.Receive(ref from); } catch (SocketException) { continue; } catch { return; }
                if (d.Length < P.HDR || d[0] != 'S' || d[1] != 'R' || d[2] != 1) continue;
                byte t = d[3]; ulong sid = P.Sid(d);
                if (t == P.T_PONG) { pong = true; continue; }
                Session s; lock (L) sessions.TryGetValue(sid, out s);
                if (s == null) continue;
                lock (L)
                {
                    if (t == P.T_HELLO_OK) s.Ok.Set();
                    else if (t == P.T_DATA) s.S.OnData(d, P.HDR, d.Length - P.HDR);
                    else if (t == P.T_ACK && d.Length >= P.HDR + 4) s.S.OnAck(P.U32(d, P.HDR), d.Length > P.HDR + 4 && d[P.HDR + 4] == 1);
                    else if (t == P.T_FIN && d.Length >= P.HDR + 4) s.S.PeerFin = P.Unwrap(P.U32(d, P.HDR), s.S.rcv);
                }
                if (t == P.T_RST) Close(s);
            }
        }

        static void TickLoop()
        {
            while (true)
            {
                Thread.Sleep(10);
                List<Session> done = new List<Session>();
                lock (L)
                {
                    double now = P.Now;
                    foreach (Session s in sessions.Values)
                    {
                        if (!s.Ok.WaitOne(0)) continue;
                        s.S.Tick();
                        if (s.S.PeerFin >= 0 && s.S.rcv >= s.S.PeerFin) done.Add(s);
                        else if (s.Closed) done.Add(s);
                        else if (now - s.S.LastTx > 1.0) { Send(P.Pack(P.T_PING, s.Sid, new byte[4], 0, 4)); s.S.LastTx = now; }
                    }
                }
                foreach (Session s in done) Close(s);
            }
        }
    }
}
