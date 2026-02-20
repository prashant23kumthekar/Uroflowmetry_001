import socket
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
# Data storage: use in-memory structures only (no persistent DB)
# Data storage: use in-memory structures only (no persistent DB)
import time
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import numpy as np
import tempfile
import os
from matplotlib.backends.backend_agg import FigureCanvasAgg

class UroflowmetryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Uroflowmetry System")
        self.root.geometry("480x320")
        # self.root.attributes('-fullscreen', True)
        # Apply styles before creating widgets so themed widgets use them
        # Initialize session state (no persistent DB)
        # keep only live-sample and UI-related state here
        self.server_port = 0
        self.device_connected = False
        self.live_samples = []
        self.sample_interval = 0.3
        self._last_live_len = 0
        # Note: connector thread removed — connect_device will read one batch
        # of samples and populate `self.live_samples` for a single-shot plot.
        # Sampling: 400 samples at 300ms interval = 120 seconds total test time
        self.sample_interval = 0.3  # 300ms per sample
        self.graph_total_duration = 120.0  # 400 samples × 0.3s = 120s
        # Flowrate limits (units: mL/s). Y-axis range for flow rate graph
        # Device mapping: raw 0 -> 0 mL, raw 1200 -> 1000 mL (linear)
        self.flowrate_min = 0.0
        self.flowrate_max = 50.0  # mL/s max on y-axis
        self.setup_styles()
        self.create_widgets()

    # init_db removed — session state initialized in __init__ (no DB persistence)

    def setup_styles(self):
        """Configure a simple, colorful ttk style for the UI."""
        style = ttk.Style(self.root)
        try:
            # Try a modern theme if available
            style.theme_use('clam')
        except Exception:
            pass

        # Color palette
        bg = '#f4f7fb'          # window background
        frame_bg = '#ffffff'    # frame background
        label_fg = '#102a43'
        accent = '#2a9df4'      # blue accent for buttons/tabs
        accent_dark = '#1070c6'
        btn_fg = '#ffffff'

        # Root background
        try:
            self.root.configure(background=bg)
        except Exception:
            pass

        # General widget styles
        style.configure('TFrame', background=frame_bg)
        style.configure('TLabelframe', background=frame_bg)
        style.configure('TLabelframe.Label', background=frame_bg, foreground=label_fg, font=('Segoe UI', 11, 'bold'))
        style.configure('TLabel', background=frame_bg, foreground=label_fg, font=('Segoe UI', 10))
        style.configure('TButton', background=accent, foreground=btn_fg, font=('Segoe UI', 10, 'bold'))
        style.map('TButton', background=[('active', accent_dark)])
        style.configure('TCombobox', foreground=label_fg)

        # Notebook/tab styling
        style.configure('TNotebook', background=bg)
        style.configure('TNotebook.Tab', background=accent, foreground=btn_fg, padding=(10, 6))

    def create_widgets(self):
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Tab 1: Patient / Device Info (minimal)
        self.patient_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.patient_tab, text='Patient Info')
        self.create_patient_tab()

        # Tab 2: Test & Graph
        self.test_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.test_tab, text='Test & Graph')
        self.create_test_tab()

    def create_patient_tab(self):
        """Minimal Patient/Device tab. Patient registration and DB are removed;
        this tab provides a simple device connection toggle and status.
        """
        for w in self.patient_tab.winfo_children():
            w.destroy()

        frame = ttk.LabelFrame(self.patient_tab, text="Device", padding=10)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Connect device button (UI-only toggle)
        self.connect_btn = ttk.Button(frame, text='Connect Device', command=self.connect_device)
        self.connect_btn.pack(pady=6)

        # Simple status label
        self.device_status = ttk.Label(frame, text='Device: Disconnected')
        self.device_status.pack(pady=6)

    def create_test_tab(self):
        frame = ttk.LabelFrame(self.test_tab, text="Uroflowmetry Test", padding=10)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        # Note: patient selection and manual input fields removed
        # Graph canvas (show above the Generate button)
        self.canvas_frame = ttk.Frame(frame)
        self.canvas_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Generate report button (uses most recent patient if none selected elsewhere)
        ttk.Button(frame, text="Generate PDF Report", command=self.generate_pdf).pack(pady=5)

        # Show live flow-vs-time plot on this tab. The live plot is updated when
        # samples arrive, and a periodic refresh will redraw only when the
        # sample buffer length changes to reduce CPU load.
        try:
            self.plot_live_samples()
        except Exception:
            pass

        # periodic refresh (redraw only when samples changed)
        try:
            self.root.after(500, self._refresh_live_plot)
        except Exception:
            pass

    def _refresh_live_plot(self):
        try:
            if len(self.live_samples) != getattr(self, '_last_live_len', 0):
                self._last_live_len = len(self.live_samples)
                try:
                    self.plot_live_samples()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.root.after(500, self._refresh_live_plot)
        except Exception:
            pass

    def create_report_tab(self):
        # Deprecated: report controls moved to Test & Graph tab.
        pass

    def _debug_log_tcp(self, data: bytes):
        """Append a small debug record for raw TCP payloads.

        Writes a timestamped entry to ~/uro_tcp_debug.log and prints a
        concise summary (hex prefix + safe-decoded text) to stdout.
        """
        try:
            if not data:
                return
            # safe text representation
            text = data.decode(errors='replace')
            hexdump = data.hex()
            # keep hex summary reasonably small
            hex_summary = hexdump[:200]
            log_path = os.path.expanduser('~/uro_tcp_debug.log')
            timestamp = datetime.now().isoformat()
            with open(log_path, 'ab') as f:
                f.write(f"--- {timestamp} ---\n".encode('utf-8'))
                f.write(data + b"\n")
            # Prefer decimal output: if data looks like 16-bit samples, print
            # them as unsigned decimals separated by a single space. Otherwise
            # fall back to printing each byte as decimal separated by spaces.
            try:
                dec_str = None
                # limit detailed decimal output length to avoid huge prints
                max_dec_chars = 1000
                if len(data) >= 2 and len(data) % 2 == 0 and len(data) <= 1600:
                    import struct
                    num = len(data) // 2
                    vals = struct.unpack(f'<{num}H', data)
                    dec_str = ' '.join(str(v) for v in vals)
                else:
                    dec_str = ' '.join(str(b) for b in data)
                if len(dec_str) > max_dec_chars:
                    print(f"[TCP DEBUG] {len(data)} bytes, decimal={dec_str[:max_dec_chars]}...")
                else:
                    print(f"[TCP DEBUG] {len(data)} bytes, decimal={dec_str}")
            except Exception:
                # fallback to hex/text if decimal formatting fails
                print(f"[TCP DEBUG] {len(data)} bytes, hex={hex_summary}{'...' if len(hexdump)>200 else ''}")
            print(f"[TCP TEXT] {text}")
        except Exception as e:
            print(f"[TCP DEBUG] logging failed: {e}")


    # server queue and polling removed — live samples should be pushed directly
    # into `self.live_samples` by external code or device handlers.

    def plot_live_samples(self):
        """Plot the current `self.live_samples` (time, flow) into `self.canvas_frame`.

        This renders a scrolling-style live plot of the most recent samples.
        """
        # Ensure canvas_frame exists
        if not hasattr(self, 'canvas_frame'):
            return

        for w in self.canvas_frame.winfo_children():
            w.destroy()

        if not self.live_samples:
            # Render an empty axes so the tab always shows a plot area
            fig = Figure(figsize=(6, 3), dpi=100)
            ax = fig.add_subplot(111)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Flow Rate (mL/s)')
            ax.set_title('Live Flow (stream) — no data')
            ax.grid(True, alpha=0.3)
            try:
                ax.set_xlim(0.0, float(self.graph_total_duration))
            except Exception:
                pass
            try:
                ax.set_ylim(float(self.flowrate_min), float(self.flowrate_max))
            except Exception:
                pass

            canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            return

        xs = [s[0] for s in self.live_samples]
        ys = [s[1] for s in self.live_samples]

        fig = Figure(figsize=(6, 3), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(xs, ys, color='#2a9df4', linewidth=1.5)
        ax.fill_between(xs, ys, alpha=0.15, color='#2a9df4')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Flow Rate (mL/s)')
        ax.set_title('Live Flow (stream)')
        ax.grid(True, alpha=0.3)
        try:
            ax.set_xlim(0.0, float(self.graph_total_duration))
        except Exception:
            pass
        try:
            ax.set_ylim(float(self.flowrate_min), float(self.flowrate_max))
        except Exception:
            pass

        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def get_patient_names(self):
        # patient list removed; provide empty list for compatibility
        return []


    # start_server/stop_server removed — server control handled externally if needed

    def connect_device(self):
        """Simple toggle for device connection state. This is a lightweight UI affordance
        that can later be extended to perform device-specific handshake/initialisation.
        """
        host = '192.168.1.3'  # Server IP address
        port = 4244        # Server port

        # For this build we perform a single-shot fetch of data from the device
        # and render the plot for that batch only. Toggling the button will
        # attempt to connect and read one block of samples.
        self.device_connected = not getattr(self, 'device_connected', False)
        if self.device_connected:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((host, port))
                    s.settimeout(300)  # 5 minutes timeout
                    # Send command: 2 bytes 0x30 0x30
                    try:
                        s.send(b'\x30\x30')
                        print("[TCP CMD] Sent command: 0x30 0x30")
                    except Exception as e:
                        print(f"[TCP CMD] Failed to send command: {e}")
                    try:
                        data = s.recv(65536)
                        # Log raw TCP payload for debugging (hex + safe text)
                        try:
                            self._debug_log_tcp(data)
                        except Exception:
                            # fallback to simple print if helper fails
                            print(f"Received data (raw): {data}")
                    except socket.timeout:
                        data = b''

                if data:
                    flows = []
                    # Try to parse 16-bit samples (800 bytes = 400 samples)
                    if len(data) >= 2:
                        try:
                            # Parse as 16-bit unsigned integers (little-endian)
                            import struct
                            num_samples = len(data) // 2
                            raw_vals = list(struct.unpack(f'<{num_samples}H', data[:num_samples*2]))
                            # Interpret raw samples as cumulative or monotonic sensor
                            # readings mapped linearly: raw 0 -> 0 mL, raw 1200 -> 1000 mL
                            # Compute instantaneous flow (mL/s) using the formula
                            # requested: (previous_raw - current_raw) / dt, then
                            # convert raw-units/s -> mL/s via raw_per_ml.
                            raw_zero = 0
                            raw_per_ml = 1.2  # raw units per mL
                            dt = float(getattr(self, 'sample_interval', 0.3))

                            flows = []
                            if not raw_vals:
                                flows = []
                            elif len(raw_vals) == 1:
                                flows = [0.0]
                            else:
                                # For first point, append zero flow (no previous sample)
                                flows = [0.0]
                                for i in range(1, len(raw_vals)):
                                    prev_raw = float(raw_vals[i-1])
                                    curr_raw = float(raw_vals[i])
                                    # compute raw difference as current minus previous
                                    diff_raw = curr_raw - prev_raw
                                    # convert raw difference to mL: diff_raw / raw_per_ml
                                    diff_ml = diff_raw / raw_per_ml
                                    # divide by dt to get mL/s
                                    flow = diff_ml / dt if dt > 0 else 0.0
                                    # negative flow is not meaningful here; clamp
                                    if flow < 0:
                                        flow = 0.0
                                    flows.append(float(flow))
                            print(f"[TCP PARSE] Parsed {num_samples} 16-bit samples -> computed {len(flows)} flow samples (example: {flows[:10]}...) ")
                        except Exception as e:
                            print(f"[TCP PARSE] 16-bit parse failed: {e}")
                            flows = []
                    
                    # Fallback: try text-based parsing
                    if not flows:
                        text = data.decode(errors='ignore').strip()
                        # try JSON first
                        try:
                            obj = json.loads(text)
                            if isinstance(obj, list):
                                flows = [float(x) for x in obj]
                            elif isinstance(obj, dict):
                                # try common keys
                                for k in ('samples', 'flow_rates', 'flows', 'data'):
                                    if k in obj and isinstance(obj[k], list):
                                        flows = [float(x) for x in obj[k]]
                                        break
                                if not flows:
                                    # single value
                                    for k in ('flow_rate', 'flow', 'value'):
                                        if k in obj:
                                            flows = [float(obj[k])]
                                            break
                        except Exception:
                            # fallback: extract numeric substrings (handles formats
                            # like Python set repr '{5, 7, 8, ...}' as well as CSV/newlines)
                            nums = re.findall(r'[-+]?\d*\.\d+(?:[eE][-+]?\d+)?|[-+]?\d+', text)
                        for p in nums:
                            try:
                                flows.append(float(p))
                            except Exception:
                                continue

                    if flows:
                        # Clamp flows to configured bounds, map into samples spaced by
                        # sample_interval (0.3s), and trim to fit graph_total_duration.
                        clamped = []
                        for v in flows:
                            try:
                                fv = float(v)
                            except Exception:
                                continue
                            fv = max(self.flowrate_min, min(self.flowrate_max, fv))
                            clamped.append(fv)

                        n = len(clamped)
                        if n == 0:
                            samples = []
                        elif n == 1:
                            # Single sample recorded at first sample interval
                            samples = [(float(self.sample_interval), float(clamped[0]))]
                        else:
                            # Timestamp samples at 1*dt, 2*dt, ..., n*dt so that
                            # 15 samples at 0.3s interval end at 4.5s (15*0.3)
                            samples = [((i + 1) * self.sample_interval, float(clamped[i])) for i in range(n)]

                        # Trim to fit total duration
                        # maximum number of samples that fit in the total duration
                        max_samples = max(1, int(self.graph_total_duration / self.sample_interval))
                        if len(samples) > max_samples:
                            # keep the most recent samples to show the tail within duration
                            samples = samples[-max_samples:]

                        self.live_samples = samples
                        try:
                            self.plot_live_samples()
                        except Exception:
                            pass

                if hasattr(self, 'connect_btn'):
                    self.connect_btn.config(text='Device Connected')
                if hasattr(self, 'device_status'):
                    self.device_status.config(text='Device: Connected')
            except Exception as e:
                messagebox.showerror('Connection Error', f'Failed to fetch data: {e}')
                # ensure UI reflects disconnected state
                self.device_connected = False
                if hasattr(self, 'connect_btn'):
                    self.connect_btn.config(text='Connect Device')
                if hasattr(self, 'device_status'):
                    self.device_status.config(text='Device: Disconnected')
        else:
            # user toggled to disconnect — clear samples and update UI
            self.live_samples = []
            try:
                self.plot_live_samples()
            except Exception:
                pass
            if hasattr(self, 'connect_btn'):
                self.connect_btn.config(text='Connect Device')
            if hasattr(self, 'device_status'):
                self.device_status.config(text='Device: Disconnected')

    # internal TCP server removed — if you need a test server, run
    # `server.py` or re-add a dedicated component to push JSON samples into
    # `app.live_samples` or `app.server_queue` (if re-enabled).
    
    def generate_pdf(self):
        # Generate a PDF report from the current live samples only (no DB/patient data).
        if not self.live_samples:
            messagebox.showerror('Error', 'No live samples available to include in PDF')
            return

        # Generate default filename with current date and time (HR_MM format)
        default_filename = datetime.now().strftime('%Y-%m-%d_%H_%M') + '.pdf'
        default_dir = '/home/prashantk39/work/picow/'
        
        # Ensure directory exists
        os.makedirs(default_dir, exist_ok=True)
        
        # Auto-save to default location
        file_path = os.path.join(default_dir, default_filename)

        try:
            self._generate_pdf_from_live(file_path)
            messagebox.showinfo('Success', f'PDF Report auto-saved: {file_path}')
            
            # Print the PDF using lp command
            try:
                subprocess.run(['lp', '-d', 'DCPT220', file_path], check=True, capture_output=True)
                messagebox.showinfo('Print', f'PDF sent to printer DCPT220')
            except subprocess.CalledProcessError as pe:
                messagebox.showwarning('Print Warning', f'Failed to print PDF: {pe}')
            except Exception as pe:
                messagebox.showwarning('Print Warning', f'Print command error: {pe}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to generate PDF: {e}')
    def _generate_pdf_from_live(self, file_path):
        """Build a simple PDF containing stats and a graph from live_samples."""
        samples = list(self.live_samples)
        if not samples:
            raise ValueError('No live samples')

        xs = [s[0] for s in samples]
        ys = [s[1] for s in samples]

        # compute simple statistics
        duration = xs[-1] - xs[0] if len(xs) > 1 else 0.0
        avg_flow = float(sum(ys) / len(ys)) if ys else 0.0
        # approximate volume by trapezoidal integration
        total_vol = 0.0
        for i in range(len(xs) - 1):
            dt = xs[i+1] - xs[i]
            total_vol += 0.5 * (ys[i] + ys[i+1]) * dt

        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, textColor='#003366')
        elements.append(Paragraph('Live Uroflowmetry Report', title_style))
        elements.append(Spacer(1, 0.2 * inch))

        meta_table = Table([
            ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Duration (s):', f"{duration:.2f}"],
            ['Average Flow (mL/s):', f"{avg_flow:.2f}"],
            ['Estimated Volume (mL):', f"{total_vol:.2f}"]
        ], colWidths=[2.5*inch, 3.5*inch])
        meta_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, '#444444')]))
        elements.append(meta_table)
        elements.append(Spacer(1, 0.2 * inch))

        # create plot image from samples
        fig = Figure(figsize=(6, 3), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(xs, ys, color='#2a9df4', linewidth=1.5)
        ax.fill_between(xs, ys, alpha=0.15, color='#2a9df4')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Flow Rate (mL/s)')
        ax.set_title('Live Flow (stream)')
        ax.grid(True, alpha=0.3)
        try:
            ax.set_xlim(0.0, float(self.graph_total_duration))
        except Exception:
            pass
        try:
            ax.set_ylim(float(self.flowrate_min), float(self.flowrate_max))
        except Exception:
            pass

        tmpf = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        tmpf.close()
        canvas = FigureCanvasAgg(fig)
        canvas.print_png(tmpf.name)

        elements.append(Image(tmpf.name, width=6 * inch))

        doc.build(elements)

        try:
            os.remove(tmpf.name)
        except Exception:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = UroflowmetryApp(root)
    root.mainloop()
