# gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from edi_parser import parse_edi
from exporter import generate_all_excel, export_csv, export_pdf
from analyzer import analyze
from filters import filter_dg, filter_reefer, filter_movement, combine_filters
from visualizer import Deck3D
import copy

class History:
    def __init__(self, limit=200):\n        self.stack = []
        self.pos = -1
        self.limit = limit
    
    def push(self, state):
        self.stack = self.stack[:self.pos+1]
        self.stack.append(copy.deepcopy(state))
        if len(self.stack) > self.limit:
            self.stack.pop(0)
            self.pos = len(self.stack) - 1
        else:
            self.pos += 1
    
    def undo(self):
        if self.pos > 0:
            self.pos -= 1
            return copy.deepcopy(self.stack[self.pos])
        return None
    
    def redo(self):
        if self.pos < len(self.stack)-1:
            self.pos += 1
            return copy.deepcopy(self.stack[self.pos])
        return None

def start_app():
    root = tk.Tk()
    root.title("EDIDeck — BAPLIE Viewer")
    root.geometry("1600x950")

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)

    frame_ctrl = ttk.Frame(nb)
    nb.add(frame_ctrl, text="Controls")

    frame_table = ttk.Frame(nb)
    nb.add(frame_table, text="All Containers")

    frame_visual = ttk.Frame(nb)
    nb.add(frame_visual, text="Visual Plan")

    frame_imdg = ttk.Frame(nb)
    nb.add(frame_imdg, text="IMDG")

    frame_reef = ttk.Frame(nb)
    nb.add(frame_reef, text="Reefer")

    btn_open = ttk.Button(frame_ctrl, text="Open EDI / BAPLIE file")
    btn_open.grid(row=0, column=0, padx=6, pady=6, sticky="w")

    search_var = tk.StringVar()
    ttk.Label(frame_ctrl, text="Search").grid(row=0, column=1, padx=6, pady=6)
    ent_search = ttk.Entry(frame_ctrl, textvariable=search_var, width=30)
    ent_search.grid(row=0, column=2, padx=6, pady=6)

    filter_var = tk.StringVar(value="ALL")
    ttk.Label(frame_ctrl, text="Quick Filter").grid(row=0, column=3, padx=6, pady=6)
    cmb_filter = ttk.Combobox(frame_ctrl, textvariable=filter_var, values=["ALL","DG","REEFER","LOAD","DISCHARGE","SIZE:20","SIZE:40"], width=14)
    cmb_filter.grid(row=0, column=4, padx=6, pady=6)

    btn_adv_filter = ttk.Button(frame_ctrl, text="Advanced Filter")
    btn_adv_filter.grid(row=0, column=5, padx=6, pady=6)

    btn_bulk = ttk.Button(frame_ctrl, text="Bulk Edit")
    btn_bulk.grid(row=0, column=6, padx=6, pady=6)

    btn_undo = ttk.Button(frame_ctrl, text="Undo")
    btn_undo.grid(row=0, column=7, padx=6, pady=6)
    btn_redo = ttk.Button(frame_ctrl, text="Redo")
    btn_redo.grid(row=0, column=8, padx=6, pady=6)

    btn_export_excel = ttk.Button(frame_ctrl, text="Export Excel")
    btn_export_excel.grid(row=0, column=9, padx=6, pady=6)
    btn_export_csv = ttk.Button(frame_ctrl, text="Export CSV")
    btn_export_csv.grid(row=0, column=10, padx=6, pady=6)
    btn_export_pdf = ttk.Button(frame_ctrl, text="Export PDF")
    btn_export_pdf.grid(row=0, column=11, padx=6, pady=6)

    btn_show_reefers_load = ttk.Button(frame_ctrl, text="Reefers for Load")
    btn_show_reefers_load.grid(row=1, column=0, padx=6, pady=6)
    btn_show_dg_load = ttk.Button(frame_ctrl, text="DG for Load")
    btn_show_dg_load.grid(row=1, column=1, padx=6, pady=6)
    btn_show_all_load = ttk.Button(frame_ctrl, text="All for Load")
    btn_show_all_load.grid(row=1, column=2, padx=6, pady=6)

    cols = ("container","size","bay","row","tier","pol","pod","weight","dg","reefer","temperature","psn","remark")
    tree = ttk.Treeview(frame_table, columns=cols, show="headings", selectmode="extended")
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=100, anchor="center")
    tree.pack(fill="both", expand=True, side="left")
    vsb = ttk.Scrollbar(frame_table, orient="vertical", command=tree.yview)
    vsb.pack(side="right", fill="y")
    tree.configure(yscrollcommand=vsb.set)

    txt_imdg = tk.Text(frame_imdg)
    txt_imdg.pack(fill="both", expand=True)
    txt_reef = tk.Text(frame_reef)
    txt_reef.pack(fill="both", expand=True)

    state = {"containers": []}
    history = History(limit=300)
    visual_widget = None

    def push_history():
        history.push(state["containers"])

    def refresh_table(filtered=None):
        tree.delete(*tree.get_children())
        data = filtered if filtered is not None else state["containers"]
        q = search_var.get().strip().lower()
        for c in data:
            if q:
                hay = " ".join([str(c.get(k,"")) for k in ("container","pol","pod","unno","psn","remark")]).lower()
                if q not in hay:
                    continue
            tree.insert("", "end", values=(
                c.get("container"), c.get("size"), c.get("bay"), c.get("row"), c.get("tier"),
                c.get("pol"), c.get("pod"), c.get("weight"), "Yes" if c.get("dg") else "",
                "Yes" if c.get("reefer") else "", c.get("temperature"), c.get("psn"), c.get("remark")
            ))
        txt_imdg.delete("1.0", tk.END)
        for c in state["containers"]:
            if c.get("dg"):
                txt_imdg.insert(tk.END, f"{c.get('container')}\tPoL:{c.get('pol')}\tPoD:{c.get('pod')}\tUN:{c.get('unno')}\tClass:{c.get('class')}\tW:{c.get('weight')}\n")
        txt_reef.delete("1.0", tk.END)
        for c in state["containers"]:
            if c.get("reefer"):
                txt_reef.insert(tk.END, f"{c.get('container')}\tPos:{c.get('bay')}/{c.get('row')}/{c.get('tier')}\tSize:{c.get('size')}\tTemp:{c.get('temperature')}\n")

    def refresh_visual(highlight_ids=None):
        nonlocal visual_widget
        for w in frame_visual.winfo_children():
            w.destroy()
        visual_widget = Deck3D(frame_visual, state["containers"])
        visual_widget.pack(fill="both", expand=True)
        def on_visual_select(cont_id):
            for c in state["containers"]:
                if c.get("container") == cont_id:
                    edit_container_dialog(c)
                    break
        visual_widget.master.on_visual_select = on_visual_select

    def edit_container_dialog(container):
        dlg = tk.Toplevel(root)
        dlg.title(f"Edit {container.get('container')}")
        entries = {}
        fields = ["container","size","bay","row","tier","pol","pod","weight","unno","class","psn","remark","temperature","ventilation"]
        for i, f in enumerate(fields):
            ttk.Label(dlg, text=f).grid(row=i, column=0, sticky="e", padx=6, pady=4)
            var = tk.StringVar(value=str(container.get(f,"")))
            ent = ttk.Entry(dlg, textvariable=var, width=40)
            ent.grid(row=i, column=1, sticky="w", padx=6, pady=4)
            entries[f] = var
        def on_ok():
            w = entries["weight"].get().strip()
            if w:
                try:
                    float(w)
                except:
                    messagebox.showerror("Validation", "Weight must be numeric")
                    return
            for k, v in entries.items():
                val = v.get().strip()
                container[k] = val
            if container.get("temperature"):
                if not str(container["temperature"]).endswith("°C"):
                    container["temperature"] = str(container["temperature"]) + "°C"
                container["reefer"] = True
            push_history()
            refresh_table()
            refresh_visual()
            dlg.destroy()
        ttk.Button(dlg, text="OK", command=on_ok).grid(row=len(fields), column=0, padx=6, pady=8)
        ttk.Button(dlg, text="Cancel", command=dlg.destroy).grid(row=len(fields), column=1, padx=6, pady=8)

    def bulk_edit_dialog(selected_items):
        dlg = tk.Toplevel(root)
        dlg.title("Bulk Edit")
        ttk.Label(dlg, text=f"Selected {len(selected_items)} containers").grid(row=0, column=0, columnspan=2, pady=6)
        ttk.Label(dlg, text="Add to weight (e.g. +100 or -50)").grid(row=1, column=0, sticky="e")
        weight_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=weight_var).grid(row=1, column=1, sticky="w")
        ttk.Label(dlg, text="Set bay").grid(row=2, column=0, sticky="e")
        bay_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=bay_var).grid(row=2, column=1, sticky="w")
        ttk.Label(dlg, text="Set row").grid(row=3, column=0, sticky="e")
        row_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=row_var).grid(row=3, column=1, sticky="w")
        ttk.Label(dlg, text="Set tier").grid(row=4, column=0, sticky="e")
        tier_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=tier_var).grid(row=4, column=1, sticky="w")
        ttk.Label(dlg, text="Set temperature (e.g. -18)").grid(row=5, column=0, sticky="e")
        temp_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=temp_var).grid(row=5, column=1, sticky="w")
        dg_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(dlg, text="Mark as DG", variable=dg_var).grid(row=6, column=0, sticky="w")
        reef_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(dlg, text="Mark as Reefer", variable=reef_var).grid(row=6, column=1, sticky="w")
        def on_apply():
            push_history()
            for iid in selected_items:
                vals = tree.item(iid, "values")
                cont_id = vals[0]
                for c in state["containers"]:
                    if c.get("container") == cont_id:
                        w = weight_var.get().strip()
                        if w:
                            try:
                                if w.startswith("+") or w.startswith("-"):
                                    c["weight"] = str(float(c.get("weight") or 0) + float(w))
                                else:
                                    c["weight"] = str(float(w))
                            except:
                                pass
                        if bay_var.get().strip():
                            c["bay"] = bay_var.get().strip()
                        if row_var.get().strip():
                            c["row"] = row_var.get().strip()
                        if tier_var.get().strip():
                            c["tier"] = tier_var.get().strip()
                        if temp_var.get().strip():
                            temp_val = temp_var.get().strip()
                            if not temp_val.endswith("°C"):
                                temp_val = temp_val + "°C"
                            c["temperature"] = temp_val
                            c["reefer"] = True
                        if dg_var.get():
                            c["dg"] = True
                        if reef_var.get():
                            c["reefer"] = True
                        break
            refresh_table()
            refresh_visual()
            dlg.destroy()
        ttk.Button(dlg, text="Apply", command=on_apply).grid(row=7, column=0, padx=6, pady=8)
        ttk.Button(dlg, text="Cancel", command=dlg.destroy).grid(row=7, column=1, padx=6, pady=8)

    def adv_filter_dialog():
        dlg = tk.Toplevel(root)
        dlg.title("Advanced Filter")
        entries = {}
        specs = [
            ("PoL", "pol"), ("PoD", "pod"), ("UN No", "unno"),
            ("Class", "class"), ("Min Weight", "minw"), ("Max Weight", "maxw"),
            ("Size contains", "size"), ("Text contains", "text")
        ]
        for i, (label, key) in enumerate(specs):
            ttk.Label(dlg, text=label).grid(row=i, column=0, sticky="e", padx=6, pady=4)
            var = tk.StringVar()
            ttk.Entry(dlg, textvariable=var, width=30).grid(row=i, column=1, sticky="w", padx=6, pady=4)
            entries[key] = var
        def on_apply():
            res = []
            for c in state["containers"]:
                ok = True
                if entries["pol"].get().strip() and entries["pol"].get().strip() not in (c.get("pol") or ""):
                    ok = False
                if entries["pod"].get().strip() and entries["pod"].get().strip() not in (c.get("pod") or ""):
                    ok = False
                if entries["unno"].get().strip() and entries["unno"].get().strip() not in (c.get("unno") or ""):
                    ok = False
                if entries["class"].get().strip() and entries["class"].get().strip() not in (c.get("class") or ""):
                    ok = False
                if entries["minw"].get().strip():
                    try:
                        if float(c.get("weight") or 0) < float(entries["minw"].get().strip()):
                            ok = False
                    except:
                        pass
                if entries["maxw"].get().strip():
                    try:
                        if float(c.get("weight") or 0) > float(entries["maxw"].get().strip()):
                            ok = False
                    except:
                        pass
                if entries["size"].get().strip() and entries["size"].get().strip() not in (c.get("size") or ""):
                    ok = False
                if entries["text"].get().strip():
                    hay = " ".join([str(c.get(k,"")) for k in ("container","psn","remark","rff")]).lower()
                    if entries["text"].get().strip().lower() not in hay:
                        ok = False
                if ok:
                    res.append(c)
            refresh_table(filtered=res)
            refresh_visual()
            dlg.destroy()
        ttk.Button(dlg, text="Apply", command=on_apply).grid(row=len(specs), column=0, padx=6, pady=8)
        ttk.Button(dlg, text="Cancel", command=dlg.destroy).grid(row=len(specs), column=1, padx=6, pady=8)

    def on_open():
        path = filedialog.askopenfilename(title="Select EDI/BAPLIE file", filetypes=[("EDI files","*.edi;*.txt"),("All files","*.*")])
        if not path:
            return
        try:
            containers = parse_edi(path)
            state["containers"] = containers
            push_history()
            refresh_table()
            refresh_visual()
            issues, summary = analyze(containers)
            msg = f"Loaded {summary['total']} containers. DG: {summary['dg_count']}, Reefers: {summary['reefer_count']}"
            if issues:
                messagebox.showwarning("Analysis issues", msg + "\n\nIssues:\n" + "\n".join(issues[:50]))
            else:
                messagebox.showinfo("Loaded", msg)
        except Exception as e:
            print("Parse error:", e)
            messagebox.showerror("Error", "Failed to parse file. See console for details.")

    def on_double_click(event):
        item = tree.identify_row(event.y)
        if not item:
            return
        vals = tree.item(item, "values")
        cont_id = vals[0]
        for c in state["containers"]:
            if c.get("container") == cont_id:
                edit_container_dialog(c)
                break

    def on_right_click(event):
        iid = tree.identify_row(event.y)
        if not iid:
            return
        menu = tk.Menu(root, tearoff=0)
        def do_edit():
            vals = tree.item(iid, "values")
            cont_id = vals[0]
            for c in state["containers"]:
                if c.get("container") == cont_id:
                    edit_container_dialog(c)
                    break
        def do_delete():
            if messagebox.askyesno("Delete", "Delete selected container?"):
                vals = tree.item(iid, "values")
                cont_id = vals[0]
                push_history()
                state["containers"] = [c for c in state["containers"] if c.get("container") != cont_id]
                refresh_table()
                refresh_visual()
        def do_mark_dg():
            vals = tree.item(iid, "values")
            cont_id = vals[0]
            push_history()
            for c in state["containers"]:
                if c.get("container") == cont_id:
                    c["dg"] = True
                    break
            refresh_table()
            refresh_visual()
        def do_copy_id():
            root.clipboard_clear()
            root.clipboard_append(tree.item(iid, "values")[0])
        menu.add_command(label="Edit", command=do_edit)
        menu.add_command(label="Delete", command=do_delete)
        menu.add_command(label="Mark as DG", command=do_mark_dg)
        menu.add_command(label="Copy ID", command=do_copy_id)
        menu.post(event.x_root, event.y_root)

    def on_delete_key(event=None):
        sel = tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Delete", f"Delete {len(sel)} selected containers?"):
            push_history()
            ids = [tree.item(iid, "values")[0] for iid in sel]
            state["containers"] = [c for c in state["containers"] if c.get("container") not in ids]
            refresh_table()
            refresh_visual()

    def on_bulk():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Bulk Edit", "Select rows in the table first.")
            return
        bulk_edit_dialog(sel)

    def on_undo():
        s = history.undo()
        if s is not None:
            state["containers"] = s
            refresh_table()
            refresh_visual()
    
    def on_redo():
        s = history.redo()
        if s is not None:
            state["containers"] = s
            refresh_table()
            refresh_visual()

    def on_export_excel():
        if not state["containers"]:
            messagebox.showwarning("No data", "Load an EDI file first.")
            return
        fname = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files","*.xlsx")], initialfile="BAPLIE_Report.xlsx")
        if not fname:
            return
        try:
            generate_all_excel(state["containers"], filename=fname)
            messagebox.showinfo("Saved", f"Excel saved: {fname}")
        except Exception as e:
            print("Export Excel error:", e)
            messagebox.showerror("Error", f"Failed to save Excel: {e}")

    def on_export_csv():
        if not state["containers"]:
            messagebox.showwarning("No data", "Load an EDI file first.")
            return
        fname = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")], initialfile="BAPLIE_Report.csv")
        if not fname:
            return
        try:
            export_csv(state["containers"], filename=fname)
            messagebox.showinfo("Saved", f"CSV saved: {fname}")
        except Exception as e:
            print("Export CSV error:", e)
            messagebox.showerror("Error", f"Failed to save CSV: {e}")

    def on_export_pdf():
        if not state["containers"]:
            messagebox.showwarning("No data", "Load an EDI file first.")
            return
        fname = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files","*.pdf")], initialfile="BAPLIE_Report.pdf")
        if not fname:
            return
        try:
            export_pdf(state["containers"], filename=fname)
            messagebox.showinfo("Saved", f"PDF saved: {fname}")
        except Exception as e:
            print("Export PDF error:", e)
            messagebox.showerror("Error", f"Failed to save PDF: {e}")

    def show_reefers_for_load():
        res = combine_filters(filter_reefer, lambda cs: filter_movement(cs, "load"))(state["containers"])
        refresh_table(filtered=res)
        refresh_visual()

    def show_dg_for_load():
        res = combine_filters(filter_dg, lambda cs: filter_movement(cs, "load"))(state["containers"])
        refresh_table(filtered=res)
        refresh_visual()

    def show_all_for_load():
        res = filter_movement(state["containers"], "load")
        refresh_table(filtered=res)
        refresh_visual()

    def apply_quick_filter():
        val = filter_var.get()
        if val == "ALL":
            refresh_table()
            refresh_visual()
            return
        if val == "DG":
            res = filter_dg(state["containers"])
        elif val == "REEFER":
            res = filter_reefer(state["containers"])
        elif val == "LOAD":
            res = filter_movement(state["containers"], "load")
        elif val == "DISCHARGE":
            res = filter_movement(state["containers"], "discharge")
        elif val.startswith("SIZE:"):
            size = val.split(":",1)[1]
            res = [c for c in state["containers"] if (c.get("size") or "").startswith(size)]
        else:
            res = state["containers"]
        refresh_table(filtered=res)
        refresh_visual()

    btn_open.config(command=on_open)
    tree.bind("<Double-1>", on_double_click)
    tree.bind("<Button-3>", on_right_click)
    btn_bulk.config(command=on_bulk)
    btn_adv_filter.config(command=adv_filter_dialog)
    btn_undo.config(command=on_undo)
    btn_redo.config(command=on_redo)
    btn_export_excel.config(command=on_export_excel)
    btn_export_csv.config(command=on_export_csv)
    btn_export_pdf.config(command=on_export_pdf)
    btn_show_reefers_load.config(command=show_reefers_for_load)
    btn_show_dg_load.config(command=show_dg_for_load)
    btn_show_all_load.config(command=show_all_for_load)
    cmb_filter.bind("<<ComboboxSelected>>", lambda e: apply_quick_filter())
    ent_search.bind("<Return>", lambda e: refresh_table())
    btn_open.focus_set()
    tree.bind("<Delete>", lambda e: on_delete_key())

    root.mainloop()
