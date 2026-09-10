# visualizer.py
"""
Ship Container Deck Visualizer - EDIDeck
Proper BAPLIE/SMDG container plan visualization

Structure:
- Bay Plan: Shows all bays with containers (colored by type)
- Bay Grid: Detailed grid for selected bay showing row × tier slots
- Container placement: row (01-14) × tier (02-90) with pyramid stacking

Colors:
- Yellow/Green: Normal (20ft/40ft)
- Red: DG (Dangerous Goods)
- Cyan/Blue: Reefer
- Purple: DG + Reefer
- White: Empty slot
"""
import tkinter as tk
from tkinter import ttk

DEFAULT_CELL = 18
MIN_CELL = 8
MAX_CELL = 40

def _color_for_container(c):
    """Container color based on type"""
    dg = c.get("dg", False)
    reef = c.get("reefer", False)
    
    if dg and reef:
        return "#9966FF"  # purple
    elif dg:
        return "#FF6B6B"  # red
    elif reef:
        return "#00BCD4"  # cyan
    else:
        # Check size for 20ft vs 40ft
        size = str(c.get("size", "")).strip()
        if size.startswith("20"):
            return "#FFC107"  # amber/yellow for 20ft
        else:
            return "#8BC34A"  # green for 40ft
    return "#FFFFFF"  # white


class BayOverviewPlan(tk.Canvas):
    """
    Overview of all bays on deck.
    Shows summary of each bay with color indicator.
    """
    def __init__(self, master, containers, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.containers = containers or []
        self.callback_bay_select = None
        
        self.offset_x = 20
        self.offset_y = 20
        self.bay_box_width = 35
        self.bay_box_height = 40
        self.gap = 3
        
        self.bind("<Button-1>", self._on_click)
        self.bind("<Configure>", lambda e: self.draw())
        self.draw()

    def _get_all_bays(self):
        """Get sorted bay numbers"""
        bays = set()
        for c in self.containers:
            try:
                b = int(str(c.get("bay") or "").strip())
                bays.add(b)
            except:
                pass
        return sorted(bays, reverse=True) if bays else []

    def _get_bay_summary(self, bay_num):
        """Get bay statistics"""
        containers = [c for c in self.containers if int(str(c.get("bay") or "0")) == bay_num]
        if not containers:
            return 0, 0, 0, "#F0F0F0"
        
        total = len(containers)
        dg_count = sum(1 for c in containers if c.get("dg"))
        reef_count = sum(1 for c in containers if c.get("reefer"))
        
        # Dominant color
        if dg_count > 0 and reef_count > 0:
            color = "#9966FF"
        elif dg_count > 0:
            color = "#FF6B6B"
        elif reef_count > 0:
            color = "#00BCD4"
        else:
            color = "#8BC34A"
        
        return total, dg_count, reef_count, color

    def draw(self):
        """Draw all bays overview"""
        self.delete("all")
        
        bays = self._get_all_bays()
        if not bays:
            return
        
        # Title
        self.create_text(
            self.offset_x, 5,
            text="DECK OVERVIEW - All Bays",
            font=("Arial", 11, "bold"),
            anchor="nw"
        )
        
        x = self.offset_x
        y = self.offset_y
        max_x = 0
        
        for bay_num in bays:
            total, dg_c, reef_c, color = self._get_bay_summary(bay_num)
            
            # Bay box
            x1, y1 = x, y
            x2, y2 = x + self.bay_box_width, y + self.bay_box_height
            
            rect = self.create_rectangle(
                x1, y1, x2, y2,
                fill=color, outline="#333", width=2
            )
            self.addtag_withtag(f"bay_{bay_num}", rect)
            
            # Bay number
            self.create_text(
                x + self.bay_box_width // 2, y + 5,
                text=f"{bay_num:02d}",
                font=("Arial", 8, "bold"),
                anchor="center"
            )
            
            # Container count
            info = f"{total}"
            if dg_c > 0:
                info += f"\nDG:{dg_c}"
            if reef_c > 0:
                info += f"\nRF:{reef_c}"
            
            self.create_text(
                x + self.bay_box_width // 2, y + self.bay_box_height // 2 + 2,
                text=info,
                font=("Arial", 7),
                anchor="center"
            )
            
            max_x = max(max_x, x2)
            x += self.bay_box_width + self.gap
            
            if x > self.winfo_width() - 100:
                x = self.offset_x
                y += self.bay_box_height + self.gap
        
        # Update scroll region
        self.config(scrollregion=(0, 0, max_x + 20, y + self.bay_box_height + 20))

    def _on_click(self, event):
        """Handle bay click"""
        items = self.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)
        if items:
            tags = self.gettags(items[0])
            for tag in tags:
                if tag.startswith("bay_"):
                    bay_num = int(tag.split("_")[1])
                    if self.callback_bay_select:
                        self.callback_bay_select(bay_num)
                    break

    def set_containers(self, containers):
        """Update containers"""
        self.containers = containers or []
        self.draw()


class BayDetailGrid(tk.Canvas):
    """
    Detailed grid view of selected bay.
    Shows row (01-14) × tier (02-90) with proper container positioning.
    
    Layout:
    - Horizontal: Row numbers (01-14)
    - Vertical: Tier numbers (02-90, bottom to top)
    - Pyramid stacking for realistic view
    """
    def __init__(self, master, containers, selected_bay=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.containers = containers or []
        self.selected_bay = selected_bay
        self.cell_size = DEFAULT_CELL
        self.highlight_set = set()
        self.callback_select = None
        
        self.offset_x = 50
        self.offset_y = 40
        
        # Standard dimensions for container ship
        self.max_row = 14
        self.max_tier = 90
        
        self.bind("<Button-1>", self._on_click)
        self.bind("<MouseWheel>", self._on_scroll)
        self.bind("<Button-4>", self._on_scroll)
        self.bind("<Button-5>", self._on_scroll)
        self.bind("<Configure>", lambda e: self.draw())
        
        self.draw()

    def _get_containers_in_bay(self):
        """Get containers in selected bay"""
        if not self.selected_bay:
            return []
        
        result = []
        for c in self.containers:
            try:
                b = int(str(c.get("bay") or "").strip())
                if b == self.selected_bay:
                    result.append(c)
            except:
                pass
        return result

    def _parse_row_tier(self, container):
        """Extract row and tier from container"""
        try:
            row = int(str(container.get("row") or "0").strip())
            tier = int(str(container.get("tier") or "0").strip())
            return row, tier
        except:
            return None, None

    def _is_in_pyramid(self, row, tier):
        """
        Check if position is in pyramid formation.
        Pyramid narrows from tier 02 up to tier 90.
        """
        if tier < 20:
            return True
        elif tier < 40:
            return 2 <= row <= 13
        elif tier < 60:
            return 3 <= row <= 12
        elif tier < 90:
            return 4 <= row <= 11
        else:
            return 5 <= row <= 10

    def draw(self):
        """Draw bay grid"""
        self.delete("all")
        
        containers_in_bay = self._get_containers_in_bay()
        
        # Canvas dimensions
        grid_width = self.max_row * self.cell_size
        grid_height = int(self.max_tier / 2) * self.cell_size  # compress tier scale
        
        width = self.offset_x + grid_width + 20
        height = self.offset_y + grid_height + 20
        
        self.config(scrollregion=(0, 0, width, height))
        
        # Title with bay number
        if self.selected_bay:
            self.create_text(
                self.offset_x + 10, 10,
                text=f"BAY {self.selected_bay:02d} - Row (01-14) × Tier (02-90)",
                font=("Arial", 11, "bold"),
                anchor="nw"
            )
        else:
            self.create_text(
                self.offset_x + 10, 10,
                text="Select a bay to view details",
                font=("Arial", 11, "bold"),
                anchor="nw",
                fill="#999"
            )
        
        if not self.selected_bay:
            return
        
        grid_x = self.offset_x
        grid_y = self.offset_y
        
        # Draw background grid
        for row in range(1, self.max_row + 1):
            for tier in range(2, self.max_tier + 1, 2):  # Step 2 for compression
                if not self._is_in_pyramid(row, tier):
                    continue
                
                x = grid_x + (row - 1) * self.cell_size
                y = grid_y + (self.max_tier - tier) // 2 * self.cell_size
                
                self.create_rectangle(
                    x, y, x + self.cell_size - 1, y + self.cell_size - 1,
                    fill="#F5F5F5", outline="#DDD", width=1
                )
        
        # Draw row labels (horizontal, top)
        for row in range(1, self.max_row + 1):
            x = grid_x + (row - 1) * self.cell_size + self.cell_size // 2
            self.create_text(
                x, self.offset_y - 15,
                text=f"{row:02d}",
                font=("Arial", 7, "bold"),
                anchor="center"
            )
        
        # Draw tier labels (vertical, left)
        for tier in range(2, self.max_tier + 1, 10):
            y = grid_y + (self.max_tier - tier) // 2 * self.cell_size
            self.create_text(
                self.offset_x - 15, y,
                text=f"{tier:02d}",
                font=("Arial", 7, "bold"),
                anchor="center"
            )
        
        # Draw containers
        for container in containers_in_bay:
            row, tier = self._parse_row_tier(container)
            if row is None or tier is None:
                continue
            
            if not self._is_in_pyramid(row, tier):
                continue
            
            x = grid_x + (row - 1) * self.cell_size
            y = grid_y + (self.max_tier - tier) // 2 * self.cell_size
            
            color = _color_for_container(container)
            
            # Container rectangle
            rect = self.create_rectangle(
                x + 1, y + 1, x + self.cell_size - 2, y + self.cell_size - 2,
                fill=color, outline="#333", width=2
            )
            
            # Container ID (last 4 chars)
            short_id = (container.get("container") or "")[-4:]
            txt = self.create_text(
                x + self.cell_size // 2, y + self.cell_size // 2,
                text=short_id,
                font=("Arial", 6, "bold"),
                anchor="center",
                fill="#000"
            )
            
            cid = container.get("container")
            if cid:
                self.addtag_withtag(cid, rect)
                self.addtag_withtag(cid, txt)
            
            # Highlight if needed
            if cid in self.highlight_set:
                self.create_rectangle(
                    x, y, x + self.cell_size - 1, y + self.cell_size - 1,
                    outline="#FFD700", width=3
                )

    def _on_click(self, event):
        """Handle container click"""
        items = self.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)
        if items and self.callback_select:
            tags = self.gettags(items[0])
            for tag in tags:
                if len(tag) > 4:  # Container ID
                    self.callback_select(tag)
                    break

    def _on_scroll(self, event):
        """Handle scroll zoom"""
        if event.num == 5 or event.delta < 0:
            self.zoom(0.85)
        elif event.num == 4 or event.delta > 0:
            self.zoom(1.15)

    def set_bay(self, bay_num):
        """Change selected bay"""
        self.selected_bay = bay_num
        self.draw()

    def set_highlight(self, container_ids):
        """Highlight containers"""
        self.highlight_set = set(container_ids or [])
        self.draw()

    def zoom(self, factor):
        """Zoom grid"""
        new_size = int(self.cell_size * factor)
        self.cell_size = max(MIN_CELL, min(MAX_CELL, new_size))
        self.draw()


class Deck3D(tk.Frame):
    """
    Main deck visualization frame.
    
    Layout:
    - TOP: Bay overview with all bays
    - BOTTOM-LEFT: Bay selector and controls
    - BOTTOM-CENTER: Detailed bay grid
    - BOTTOM-RIGHT: Tools and legend
    """
    def __init__(self, master, containers, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.containers = containers or []
        self.current_bay = None
        
        # Frames
        top_frame = tk.Frame(self, height=120)
        top_frame.grid(row=0, column=0, columnspan=3, sticky="nsew")
        top_frame.grid_propagate(False)
        
        left_frame = tk.Frame(self, width=140)
        left_frame.grid(row=1, column=0, sticky="nsew")
        left_frame.grid_propagate(False)
        
        center_frame = tk.Frame(self)
        center_frame.grid(row=1, column=1, sticky="nsew")
        
        right_frame = tk.Frame(self, width=180)
        right_frame.grid(row=1, column=2, sticky="nsew")
        right_frame.grid_propagate(False)
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # === TOP: Bay Overview ===
        ttk.Label(top_frame, text="DECK OVERVIEW - Click bay to view details", font=("Arial", 10, "bold")).pack(anchor="w", padx=6, pady=4)
        self.bay_overview = BayOverviewPlan(top_frame, self.containers, height=100, bg="#FAFAFA")
        self.bay_overview.pack(fill="both", expand=True, padx=4, pady=4)
        self.bay_overview.callback_bay_select = self._on_bay_select
        
        # === LEFT: Bay Selector ===
        tk.Label(left_frame, text="SELECT BAY", font=("Arial", 10, "bold")).pack(padx=6, pady=6)
        
        ttk.Label(left_frame, text="Current:").pack(anchor="w", padx=6, pady=2)
        self.bay_label = tk.Label(left_frame, text="---", font=("Arial", 12, "bold"), fg="blue")
        self.bay_label.pack(anchor="w", padx=6, pady=4)
        
        # Bay list
        ttk.Label(left_frame, text="Bays:", font=("Arial", 9)).pack(anchor="w", padx=6, pady=2)
        self.bay_listbox = tk.Listbox(left_frame, height=10, font=("Arial", 9))
        self.bay_listbox.pack(fill="both", expand=True, padx=6, pady=4)
        self.bay_listbox.bind("<<ListboxSelect>>", self._on_bay_listbox_select)
        
        ttk.Button(left_frame, text="Clear", command=self._clear_bay).pack(padx=6, pady=4, fill="x")
        
        # === CENTER: Bay Detail Grid ===
        self.bay_grid = BayDetailGrid(center_frame, self.containers, selected_bay=None, bg="white")
        self.bay_grid.pack(fill="both", expand=True)
        self.bay_grid.callback_select = self._on_container_select
        
        # === RIGHT: Controls ===
        tk.Label(right_frame, text="TOOLS", font=("Arial", 10, "bold")).pack(padx=6, pady=6)
        
        ttk.Button(right_frame, text="Zoom In", command=self._zoom_in).pack(padx=6, pady=4, fill="x")
        ttk.Button(right_frame, text="Zoom Out", command=self._zoom_out).pack(padx=6, pady=4, fill="x")
        
        ttk.Separator(right_frame, orient="horizontal").pack(fill="x", padx=6, pady=6)
        
        ttk.Button(right_frame, text="Highlight DG", command=self._highlight_dg).pack(padx=6, pady=4, fill="x")
        ttk.Button(right_frame, text="Highlight Reefer", command=self._highlight_reefer).pack(padx=6, pady=4, fill="x")
        ttk.Button(right_frame, text="Clear HL", command=self._clear_highlight).pack(padx=6, pady=4, fill="x")
        
        ttk.Separator(right_frame, orient="horizontal").pack(fill="x", padx=6, pady=6)
        
        # Legend
        tk.Label(right_frame, text="LEGEND", font=("Arial", 9, "bold")).pack(padx=6, pady=4)
        self._draw_legend(right_frame)
        
        ttk.Separator(right_frame, orient="horizontal").pack(fill="x", padx=6, pady=6)
        ttk.Button(right_frame, text="Refresh", command=self.refresh).pack(padx=6, pady=4, fill="x")
        
        # Populate bay list
        self._populate_bay_list()

    def _populate_bay_list(self):
        """Populate bay listbox"""
        self.bay_listbox.delete(0, tk.END)
        bays = set()
        for c in self.containers:
            try:
                b = int(str(c.get("bay") or "").strip())
                bays.add(b)
            except:
                pass
        
        for bay in sorted(bays, reverse=True):
            self.bay_listbox.insert(tk.END, f"Bay {bay:02d}")

    def _draw_legend(self, parent):
        """Draw color legend"""
        frame = tk.Frame(parent)
        frame.pack(padx=6, pady=4, anchor="w")
        
        items = [
            ("20ft", "#FFC107"),
            ("40ft", "#8BC34A"),
            ("DG", "#FF6B6B"),
            ("Reefer", "#00BCD4"),
            ("DG+RF", "#9966FF"),
        ]
        
        for label, color in items:
            row = tk.Frame(frame)
            row.pack(anchor="w", pady=1)
            
            c = tk.Canvas(row, width=14, height=12, highlightthickness=0)
            c.create_rectangle(0, 0, 14, 12, fill=color, outline="#333")
            c.pack(side="left", padx=3)
            
            tk.Label(row, text=label, font=("Arial", 8)).pack(side="left")

    def _on_bay_select(self, bay_num):
        """Handle bay selection from overview"""
        self.current_bay = bay_num
        self.bay_label.config(text=f"Bay {bay_num:02d}")
        self.bay_grid.set_bay(bay_num)
        
        # Select in listbox
        self.bay_listbox.delete(0, tk.END)
        self._populate_bay_list()
        for i in range(self.bay_listbox.size()):
            if f"Bay {bay_num:02d}" in self.bay_listbox.get(i):
                self.bay_listbox.select_set(i)
                self.bay_listbox.see(i)
                break

    def _on_bay_listbox_select(self, event):
        """Handle bay selection from listbox"""
        sel = self.bay_listbox.curselection()
        if sel:
            text = self.bay_listbox.get(sel[0])
            try:
                bay_num = int(text.split()[-1])
                self._on_bay_select(bay_num)
            except:
                pass

    def _clear_bay(self):
        """Clear bay selection"""
        self.current_bay = None
        self.bay_label.config(text="---")
        self.bay_grid.set_bay(None)
        self.bay_listbox.selection_clear(0, tk.END)

    def _zoom_in(self):
        """Zoom in"""
        self.bay_grid.zoom(1.15)

    def _zoom_out(self):
        """Zoom out"""
        self.bay_grid.zoom(0.85)

    def _highlight_dg(self):
        """Highlight DG containers"""
        ids = [c.get("container") for c in self.containers if c.get("dg")]
        self.bay_grid.set_highlight(ids)

    def _highlight_reefer(self):
        """Highlight reefer containers"""
        ids = [c.get("container") for c in self.containers if c.get("reefer")]
        self.bay_grid.set_highlight(ids)

    def _clear_highlight(self):
        """Clear highlights"""
        self.bay_grid.set_highlight([])

    def _on_container_select(self, cont_id):
        """Handle container selection"""
        if hasattr(self.master, "on_visual_select"):
            try:
                self.master.on_visual_select(cont_id)
            except:
                pass

    def refresh(self, containers=None):
        """Refresh all views"""
        if containers is not None:
            self.containers = containers
        
        self.bay_overview.set_containers(self.containers)
        self.bay_grid.containers = self.containers
        self.bay_grid.draw()
        self._populate_bay_list()
