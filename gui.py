import customtkinter as ctk
import threading
import logging
import time
import os
import glob
from scraper import UniversalScraper, load_config

class TextboxHandler(logging.Handler):
    def __init__(self, textbox):
        super().__init__()
        self.textbox = textbox

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.textbox.configure(state="normal")
            self.textbox.insert("end", msg + "\n")
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
        self.textbox.after(0, append)

class ScraperGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Universal Configuration-Driven Scraper Engine")
        self.geometry("900x700")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.config = load_config("config.yaml")
        self.stop_event = threading.Event()
        
        self._build_sidebar()
        self._build_main_panel()
        self._setup_logging()
        
    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(16, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Engine Config", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Profile Selector
        self.profile_label = ctk.CTkLabel(self.sidebar_frame, text="Select Profile:")
        self.profile_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        
        profiles = glob.glob("profiles/*.yaml")
        profile_names = [os.path.basename(p) for p in profiles] if profiles else ["No profiles found"]
        
        self.profile_option = ctk.CTkOptionMenu(self.sidebar_frame, values=profile_names)
        self.profile_option.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Start URL Override
        self.url_label = ctk.CTkLabel(self.sidebar_frame, text="Start URL Override (Optional):")
        self.url_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.url_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Leave empty to use profile URL")
        self.url_entry.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Max Pages
        self.pages_label = ctk.CTkLabel(self.sidebar_frame, text="Max Pages (0 = All):")
        self.pages_label.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="w")
        self.pages_entry = ctk.CTkEntry(self.sidebar_frame)
        self.pages_entry.insert(0, "0")
        self.pages_entry.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Max Workers
        self.workers_label = ctk.CTkLabel(self.sidebar_frame, text="Max Workers:")
        self.workers_label.grid(row=7, column=0, padx=20, pady=(10, 0), sticky="w")
        self.workers_entry = ctk.CTkEntry(self.sidebar_frame)
        self.workers_entry.insert(0, str(self.config.get("max_workers", 5)))
        self.workers_entry.grid(row=8, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Delay
        self.delay_label = ctk.CTkLabel(self.sidebar_frame, text="Delay/Jitter (seconds):")
        self.delay_label.grid(row=9, column=0, padx=20, pady=(10, 0), sticky="w")
        self.delay_entry = ctk.CTkEntry(self.sidebar_frame)
        self.delay_entry.insert(0, str(self.config.get("delay", 1.0)))
        self.delay_entry.grid(row=10, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Output Format
        self.output_label = ctk.CTkLabel(self.sidebar_frame, text="Output Format:")
        self.output_label.grid(row=11, column=0, padx=20, pady=(10, 0), sticky="w")
        self.output_option = ctk.CTkOptionMenu(self.sidebar_frame, values=["data.csv", "data.json", "data.db"])
        self.output_option.grid(row=12, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Resume Toggle
        self.resume_switch = ctk.CTkSwitch(self.sidebar_frame, text="Resume Checkpoint")
        self.resume_switch.grid(row=13, column=0, padx=20, pady=20, sticky="w")
        if self.config.get("resume"):
            self.resume_switch.select()
            
        # Action Buttons
        self.start_button = ctk.CTkButton(self.sidebar_frame, text="Start Scraping", command=self.start_scraping)
        self.start_button.grid(row=14, column=0, padx=20, pady=(10, 5), sticky="ew")
        
        self.stop_button = ctk.CTkButton(self.sidebar_frame, text="Stop Scraping", command=self.stop_scraping, fg_color="#b22222", hover_color="#8b0000", state="disabled")
        self.stop_button.grid(row=15, column=0, padx=20, pady=(5, 20), sticky="ew")
        
    def _build_main_panel(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        self.log_textbox = ctk.CTkTextbox(self.main_frame, state="disabled", font=("Consolas", 12))
        self.log_textbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 10))
        self.progress_bar.set(0)
        
    def _setup_logging(self):
        handler = TextboxHandler(self.log_textbox)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"))
        logging.getLogger().handlers.clear()
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
        logging.info("Universal Scraper Engine initialized. Select a profile to begin.")
        
    def update_progress(self, pages_scraped, max_pages):
        if max_pages and max_pages > 0:
            val = pages_scraped / max_pages
            self.after(0, lambda: self.progress_bar.set(val))

    def stop_scraping(self):
        if not self.stop_event.is_set():
            logging.warning("Initiating graceful shutdown. Waiting for current requests to finish...")
            self.stop_button.configure(state="disabled", text="Stopping...")
            self.stop_event.set()

    def start_scraping(self):
        profile_file = self.profile_option.get()
        if profile_file == "No profiles found":
            logging.error("No YAML profiles found in the profiles/ directory!")
            return
            
        profile_path = os.path.join("profiles", profile_file)

        self.start_button.configure(state="disabled", text="Scraping...")
        self.stop_button.configure(state="normal", text="Stop Scraping")
        self.progress_bar.set(0)
        self.stop_event.clear()
        
        try:
            pages_val = int(self.pages_entry.get())
            max_pages = pages_val if pages_val > 0 else None
            max_workers = int(self.workers_entry.get())
            delay = float(self.delay_entry.get())
        except ValueError:
            logging.error("Invalid input! Please enter numbers for Pages, Workers, and Delay.")
            self.start_button.configure(state="normal", text="Start Scraping")
            self.stop_button.configure(state="disabled")
            return

        url_override = self.url_entry.get().strip() or None
        output = self.output_option.get()
        resume = bool(self.resume_switch.get())
        
        threading.Thread(target=self._run_scraper_thread, args=(profile_path, max_pages, max_workers, delay, output, resume, url_override), daemon=True).start()
        
    def _run_scraper_thread(self, profile_path, max_pages, max_workers, delay, output, resume, url_override):
        try:
            logging.info(f"Loading Profile: {profile_path} -> {output}")
            if url_override:
                logging.info(f"Overriding start URL with: {url_override}")
                
            scraper = UniversalScraper(
                profile_path=profile_path,
                delay=delay,
                max_workers=max_workers,
                resume=resume,
                start_url_override=url_override
            )
            
            start_time = time.time()
            valid_items, errors = scraper.scrape(
                max_pages=max_pages, 
                progress_callback=self.update_progress,
                stop_event=self.stop_event
            )
            
            if self.stop_event.is_set():
                logging.warning(f"Scrape stopped early! Saving {len(valid_items)} collected items...")
            
            if output.endswith(".json"):
                scraper.export_json(valid_items, output)
            elif output.endswith(".db"):
                scraper.export_sqlite(valid_items, output)
            else:
                scraper.export_csv(valid_items, output)
                
            if errors:
                scraper.export_errors(errors, "errors.csv")
                
            runtime = time.time() - start_time
            logging.info(f"Engine execution complete! Collected {len(valid_items)} items in {runtime:.2f}s.")
            
        except Exception as e:
            logging.error(f"Critical execution error: {e}")
            
        finally:
            self.after(0, lambda: self.start_button.configure(state="normal", text="Start Scraping"))
            self.after(0, lambda: self.stop_button.configure(state="disabled", text="Stop Scraping"))
            self.after(0, lambda: self.progress_bar.set(1.0))

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = ScraperGUI()
    app.mainloop()
