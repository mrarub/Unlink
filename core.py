import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import winreg


class RegistryCleaner:
    def __init__(self, root):
        self.root = root
        self.root.title("注册表打开方式删除工具")
        self.root.geometry("900x700")
        
        self.entries = []
        self.selected = set()  # 用set存储选中项
        
        self.setup_ui()
        self.load_entries()
        
    def setup_ui(self):
        main = ttk.Frame(self.root, padding=20)
        main.pack(fill=BOTH, expand=True)
        
        # 标题
        ttk.Label(main, text="注册表打开方式删除工具", 
                  font=("Microsoft YaHei", 18, "bold")).pack(pady=(0, 20))
        
        # 搜索栏
        search_frame = ttk.Frame(main)
        search_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Label(search_frame, text="搜索:").pack(side=LEFT, padx=(0, 10))
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *_: self.refresh())
        ttk.Entry(search_frame, textvariable=self.search_var, width=40).pack(
            side=LEFT, fill=X, expand=True, padx=(0, 10))
        ttk.Button(search_frame, text="刷新", command=self.load_entries, 
                   bootstyle=PRIMARY).pack(side=LEFT)
        
        # 操作栏
        action_frame = ttk.Frame(main)
        action_frame.pack(fill=X, pady=(0, 15))
        
        self.select_all_var = tk.BooleanVar()
        ttk.Checkbutton(action_frame, text="全选", variable=self.select_all_var,
                        command=self.toggle_all).pack(side=LEFT)
        ttk.Button(action_frame, text="删除选中", command=self.delete_selected,
                   bootstyle=DANGER).pack(side=RIGHT)
        
        # 列表
        list_frame = ttk.Frame(main)
        list_frame.pack(fill=BOTH, expand=True)
        
        cols = [("select", "选择", 60), ("ext", "后缀", 100), 
                ("progid", "程序ID", 200), ("path", "路径", 400)]
        
        self.tree = ttk.Treeview(list_frame, columns=[c[0] for c in cols], 
                                  show="headings", height=20)
        for col, text, width in cols:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=CENTER if col == "select" else W)
        
        self.tree.bind("<Button-1>", self.on_click)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 状态栏
        status_frame = ttk.Frame(main)
        status_frame.pack(fill=X, pady=(15, 0))
        self.status = ttk.Label(status_frame, text="就绪")
        self.status.pack(side=LEFT)
        self.count = ttk.Label(status_frame, text="共 0 项")
        self.count.pack(side=RIGHT)

    def load_entries(self):
        """加载注册表项"""
        self.entries.clear()
        self.selected.clear()
        
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Classes") as key:
                i = 0
                while True:
                    try:
                        name = winreg.EnumKey(key, i)
                        if name.startswith('.'):
                            self._load_progids(name)
                        i += 1
                    except OSError:
                        break
        except Exception as e:
            messagebox.showerror("错误", f"读取注册表失败: {e}")
        
        self.refresh()

    def _load_progids(self, ext):
        """加载扩展名的 OpenWithProgids"""
        try:
            path = fr"SOFTWARE\Classes\{ext}\OpenWithProgids"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
                i = 0
                while True:
                    try:
                        progid, *_ = winreg.EnumValue(key, i)
                        self.entries.append({
                            'ext': ext, 'progid': progid,
                            'path': f"HKCU\\...\\{ext}\\OpenWithProgids"
                        })
                        i += 1
                    except OSError:
                        break
        except OSError:
            pass

    def get_filtered(self):
        """获取过滤后的数据"""
        s = self.search_var.get().lower()
        return [e for e in self.entries 
                if s in e['ext'].lower() or s in e['progid'].lower()]

    def refresh(self):
        """刷新列表显示"""
        self.tree.delete(*self.tree.get_children())
        self.selected.clear()
        
        for e in self.get_filtered():
            self.tree.insert("", END, values=("☐", e['ext'], e['progid'], e['path']))
        
        self.count.config(text=f"共 {len(self.tree.get_children())} 项")
        self._update_select_all()

    def on_click(self, event):
        """处理点击事件"""
        if (self.tree.identify_region(event.x, event.y) == "cell" and
            self.tree.identify_column(event.x) == "#1"):
            if item := self.tree.identify_row(event.y):
                is_selected = item in self.selected
                self.selected.discard(item) if is_selected else self.selected.add(item)
                self.tree.set(item, "select", "☐" if is_selected else "☑")
                self._update_select_all()

    def _update_select_all(self):
        """更新全选状态"""
        items = self.tree.get_children()
        self.select_all_var.set(bool(items) and len(self.selected) == len(items))

    def toggle_all(self):
        """切换全选"""
        items = self.tree.get_children()
        select = self.select_all_var.get()
        self.selected = set(items) if select else set()
        for item in items:
            self.tree.set(item, "select", "☑" if select else "☐")

    def delete_selected(self):
        """删除选中项"""
        if not self.selected:
            messagebox.showwarning("警告", "请先选择要删除的项")
            return
        
        if not messagebox.askyesno("确认", f"删除 {len(self.selected)} 项？不可恢复！"):
            return
        
        filtered = self.get_filtered()
        ok = fail = 0
        
        for item in self.selected:
            idx = self.tree.index(item)
            if idx >= len(filtered):
                continue
            e = filtered[idx]
            try:
                path = fr"SOFTWARE\Classes\{e['ext']}\OpenWithProgids"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, 
                                    winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, e['progid'])
                ok += 1
            except Exception:
                fail += 1
        
        messagebox.showinfo("完成", f"成功: {ok}, 失败: {fail}")
        self.status.config(text=f"删除完成: 成功 {ok}, 失败 {fail}")
        self.load_entries()


if __name__ == "__main__":
    root = ttkb.Window(themename="flatly")
    RegistryCleaner(root)
    root.mainloop()