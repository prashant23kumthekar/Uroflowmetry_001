import socket
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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
        self.server_port = 5000
        self.device_connected = False
        self.live_samples = []
        self.sample_interval = 0.3
        self._last_live_len = 0
        # Note: connector thread removed — connect_device will read one batch
        # of samples and populate `self.live_samples` for a single-shot plot.
        # Total graph duration (seconds)
        self.graph_total_duration = 40.0
        # Flowrate limits (mL/s)
        self.flowrate_min = 0.0
        self.flowrate_max = 50.0
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
        host = '127.0.0.1'  # Server IP address
        port = 65432        # Server port

        # For this build we perform a single-shot fetch of data from the device
        # and render the plot for that batch only. Toggling the button will
        # attempt to connect and read one block of samples.
        self.device_connected = not getattr(self, 'device_connected', False)
        if self.device_connected:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((host, port))
                    s.settimeout(2)
                    try:
                        data = s.recv(65536)
                        print(f"Received data: {data}")
                    except socket.timeout:
                        data = b''

                if data:
                    text = data.decode(errors='ignore').strip()
                    flows = []
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

        file_path = filedialog.asksaveasfilename(defaultextension='.pdf', filetypes=[('PDF files', '*.pdf')])
        if not file_path:
            return

        try:
            self._generate_pdf_from_live(file_path)
            messagebox.showinfo('Success', f'PDF Report saved: {file_path}')
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