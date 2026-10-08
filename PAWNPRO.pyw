import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3, os, shutil
from datetime import datetime, timedelta

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(APP_DIR, "pawnpro.db")
BACKUP_DIR = os.path.join(APP_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.executescript("""
CREATE TABLE IF NOT EXISTS settings(
 key TEXT PRIMARY KEY, value TEXT
);
CREATE TABLE IF NOT EXISTS customers(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL, id_number TEXT, phone TEXT, address TEXT, notes TEXT,
 created TEXT
);
CREATE TABLE IF NOT EXISTS loans(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 ticket TEXT UNIQUE, customer_id INTEGER, item TEXT, category TEXT,
 brand TEXT, model TEXT, serial TEXT, condition TEXT, location TEXT,
 market_value REAL, loan_amount REAL, interest_rate REAL, fee REAL,
 start_date TEXT, due_date TEXT, status TEXT DEFAULT 'ACTIVE',
 notes TEXT
);
CREATE TABLE IF NOT EXISTS payments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 loan_id INTEGER, amount REAL, method TEXT, paid_at TEXT, cashier TEXT
);
CREATE TABLE IF NOT EXISTS sales(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 loan_id INTEGER, item TEXT, buyer TEXT, price REAL, sold_at TEXT, method TEXT
);
""")
defaults = {
    "shop_name":"PAWNPRO PAWN SHOP", "address":"", "phone":"",
    "email":"", "interest_rate":"20", "service_fee":"0", "loan_days":"30"
}
for k,v in defaults.items():
    cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
conn.commit()

def setting(k):
    return cur.execute("SELECT value FROM settings WHERE key=?",(k,)).fetchone()[0]

def money(x): return f"R{x:,.2f}"

def next_ticket():
    n = cur.execute("SELECT COUNT(*) FROM loans").fetchone()[0] + 1
    return f"PS-{n:06d}"

def customer_name(cid):
    r=cur.execute("SELECT name FROM customers WHERE id=?",(cid,)).fetchone()
    return r[0] if r else "Unknown"

def loan_balance(lid):
    r=cur.execute("""SELECT loan_amount, interest_rate, fee FROM loans WHERE id=?""",(lid,)).fetchone()
    if not r: return 0
    principal, rate, fee=r
    total=principal+(principal*rate/100)+fee
    paid=cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE loan_id=?",(lid,)).fetchone()[0]
    return max(0,total-paid)

def clear(frame):
    for w in frame.winfo_children(): w.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PAWNPRO v1 - Pawn Shop Management System")
        self.geometry("1200x720")
        self.minsize(1000,650)
        self.configure(bg="#eef1f5")
        self.build()
        self.show_dashboard()

    def build(self):
        self.sidebar=tk.Frame(self,bg="#17202a",width=210)
        self.sidebar.pack(side="left",fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar,text="PAWNPRO",font=("Segoe UI",22,"bold"),fg="white",bg="#17202a").pack(pady=(25,2))
        tk.Label(self.sidebar,text="Pawn Shop Management",font=("Segoe UI",9),fg="#b9c2cc",bg="#17202a").pack(pady=(0,25))
        items=[("🏠","Dashboard",self.show_dashboard),("👤","Customers",self.show_customers),
               ("🤝","New Pawn",self.new_pawn),("💵","Payments",self.show_payments),
               ("📦","Inventory",self.show_inventory),("🛒","Sales",self.show_sales),
               ("⚠","Overdue",self.show_overdue),("📊","Reports",self.show_reports),
               ("⚙","Settings",self.show_settings),("💾","Backup",self.backup)]
        for icon,text,cmd in items:
            b=tk.Button(self.sidebar,text=f"{icon}  {text}",command=cmd,anchor="w",
                        bg="#17202a",fg="white",activebackground="#263747",activeforeground="white",
                        relief="flat",font=("Segoe UI",10),padx=20,pady=9)
            b.pack(fill="x")
        self.main=tk.Frame(self,bg="#eef1f5")
        self.main.pack(side="right",fill="both",expand=True)

    def header(self,title):
        clear(self.main)
        top=tk.Frame(self.main,bg="white",height=65)
        top.pack(fill="x")
        tk.Label(top,text=title,font=("Segoe UI",20,"bold"),bg="white",fg="#17202a").pack(side="left",padx=25,pady=15)
        tk.Label(top,text=setting("shop_name"),font=("Segoe UI",10),bg="white",fg="#667").pack(side="right",padx=25)
        return tk.Frame(self.main,bg="#eef1f5")

    def card(self,parent,title,value):
        f=tk.Frame(parent,bg="white",bd=1,relief="solid",width=200,height=105)
        f.pack_propagate(False)
        tk.Label(f,text=title,bg="white",fg="#65717d",font=("Segoe UI",10)).pack(anchor="w",padx=15,pady=(14,2))
        tk.Label(f,text=value,bg="white",fg="#17202a",font=("Segoe UI",20,"bold")).pack(anchor="w",padx=15)
        return f

    def show_dashboard(self):
        body=self.header("Dashboard")
        body.pack(fill="both",expand=True,padx=20,pady=20)
        active=cur.execute("SELECT COUNT(*) FROM loans WHERE status='ACTIVE'").fetchone()[0]
        overdue=cur.execute("SELECT COUNT(*) FROM loans WHERE status='ACTIVE' AND due_date < ?",(datetime.now().date().isoformat(),)).fetchone()[0]
        items=cur.execute("SELECT COUNT(*) FROM loans WHERE status IN ('ACTIVE','FOR SALE')").fetchone()[0]
        today=datetime.now().date().isoformat()
        payments=cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE substr(paid_at,1,10)=?",(today,)).fetchone()[0]
        sales=cur.execute("SELECT COALESCE(SUM(price),0) FROM sales WHERE substr(sold_at,1,10)=?",(today,)).fetchone()[0]
        loans_today=cur.execute("SELECT COALESCE(SUM(loan_amount),0) FROM loans WHERE substr(start_date,1,10)=?",(today,)).fetchone()[0]
        row=tk.Frame(body,bg="#eef1f5"); row.pack(fill="x",pady=(0,20))
        for t,v in [("Active Loans",active),("Overdue",overdue),("Items in Pawn",items),("Today's Loans",money(loans_today)),("Today's Payments",money(payments)),("Today's Sales",money(sales))]:
            self.card(row,t,v).pack(side="left",fill="y",expand=True,padx=5)
        box=tk.Frame(body,bg="white"); box.pack(fill="both",expand=True)
        tk.Label(box,text="Recent Loans",font=("Segoe UI",14,"bold"),bg="white").pack(anchor="w",padx=18,pady=15)
        cols=("Ticket","Customer","Item","Loan","Due","Status")
        tv=ttk.Treeview(box,columns=cols,show="headings",height=15)
        for c in cols: tv.heading(c,text=c); tv.column(c,width=140)
        tv.pack(fill="both",expand=True,padx=15,pady=(0,15))
        for r in cur.execute("""SELECT l.ticket,c.name,l.item,l.loan_amount,l.due_date,l.status
                              FROM loans l LEFT JOIN customers c ON c.id=l.customer_id
                              ORDER BY l.id DESC LIMIT 15"""):
            tv.insert("", "end", values=(r[0],r[1],r[2],money(r[3]),r[4],r[5]))

    def show_customers(self):
        body=self.header("Customers"); body.pack(fill="both",expand=True,padx=20,pady=20)
        bar=tk.Frame(body,bg="#eef1f5"); bar.pack(fill="x",pady=(0,10))
        search=tk.StringVar()
        tk.Entry(bar,textvariable=search,font=("Segoe UI",11),width=35).pack(side="left")
        tk.Button(bar,text="+ New Customer",command=self.customer_form,bg="#1f6feb",fg="white",relief="flat",padx=15,pady=8).pack(side="right")
        cols=("ID","Name","ID Number","Phone","Address","Created")
        tv=ttk.Treeview(body,columns=cols,show="headings")
        for c in cols: tv.heading(c,text=c); tv.column(c,width=150)
        tv.pack(fill="both",expand=True)
        def refresh(*a):
            for x in tv.get_children(): tv.delete(x)
            q=f"%{search.get()}%"
            for r in cur.execute("SELECT id,name,id_number,phone,address,created FROM customers WHERE name LIKE ? OR phone LIKE ? OR id_number LIKE ? ORDER BY id DESC",(q,q,q)):
                tv.insert("", "end", values=r)
        search.trace_add("write",refresh); refresh()

    def customer_form(self):
        w=tk.Toplevel(self); w.title("New Customer"); w.geometry("480x420"); w.grab_set()
        fields={}
        for label in ["Full Name","ID / Passport Number","Phone","Address","Notes"]:
            tk.Label(w,text=label,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=25,pady=(12,3))
            e=tk.Entry(w,width=50); e.pack(padx=25); fields[label]=e
        def save():
            if not fields["Full Name"].get().strip(): return messagebox.showerror("Error","Customer name is required")
            cur.execute("INSERT INTO customers(name,id_number,phone,address,notes,created) VALUES(?,?,?,?,?,?)",
                        (fields["Full Name"].get(),fields["ID / Passport Number"].get(),fields["Phone"].get(),
                         fields["Address"].get(),fields["Notes"].get(),datetime.now().isoformat(timespec="seconds")))
            conn.commit(); w.destroy(); self.show_customers()
        tk.Button(w,text="SAVE CUSTOMER",command=save,bg="#1f6feb",fg="white",padx=20,pady=8).pack(pady=20)

    def new_pawn(self):
        body=self.header("New Pawn / Loan"); body.pack(fill="both",expand=True,padx=20,pady=20)
        form=tk.Frame(body,bg="white"); form.pack(fill="both",expand=True)
        fields={}
        labels=["Customer ID","Item","Category","Brand","Model","Serial / IMEI","Condition","Storage Location","Market Value","Loan Amount","Interest %","Service Fee","Loan Days"]
        for i,label in enumerate(labels):
            r,c=divmod(i,2)
            tk.Label(form,text=label,bg="white",font=("Segoe UI",9,"bold")).grid(row=r,column=c*2,sticky="w",padx=20,pady=(15,3))
            e=tk.Entry(form,width=32); e.grid(row=r,column=c*2+1,padx=(0,20),pady=(15,3)); fields[label]=e
        fields["Interest %"].insert(0,setting("interest_rate")); fields["Service Fee"].insert(0,setting("service_fee")); fields["Loan Days"].insert(0,setting("loan_days"))
        def save():
            try:
                cid=int(fields["Customer ID"].get())
                if not cur.execute("SELECT 1 FROM customers WHERE id=?",(cid,)).fetchone(): raise ValueError("Customer ID not found")
                loan=float(fields["Loan Amount"].get()); mv=float(fields["Market Value"].get())
                rate=float(fields["Interest %"].get()); fee=float(fields["Service Fee"].get()); days=int(fields["Loan Days"].get())
            except Exception as e:
                return messagebox.showerror("Check details",str(e))
            start=datetime.now(); due=(start+timedelta(days=days)).date().isoformat()
            ticket=next_ticket()
            cur.execute("""INSERT INTO loans(ticket,customer_id,item,category,brand,model,serial,condition,location,
                        market_value,loan_amount,interest_rate,fee,start_date,due_date,status)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (ticket,cid,fields["Item"].get(),fields["Category"].get(),fields["Brand"].get(),
                         fields["Model"].get(),fields["Serial / IMEI"].get(),fields["Condition"].get(),
                         fields["Storage Location"].get(),mv,loan,rate,fee,start.isoformat(timespec="seconds"),due,"ACTIVE"))
            conn.commit()
            messagebox.showinfo("Pawn Created",f"Pawn ticket {ticket} created.\nAmount lent: {money(loan)}\nDue: {due}")
            self.show_dashboard()
        tk.Button(form,text="CREATE PAWN TICKET",command=save,bg="#198754",fg="white",font=("Segoe UI",10,"bold"),padx=20,pady=10).grid(row=7,column=1,pady=25)

    def show_payments(self):
        body=self.header("Payments"); body.pack(fill="both",expand=True,padx=20,pady=20)
        top=tk.Frame(body,bg="#eef1f5"); top.pack(fill="x",pady=(0,15))
        tk.Label(top,text="Pawn Ticket:",bg="#eef1f5").pack(side="left")
        ent=tk.Entry(top,width=25); ent.pack(side="left",padx=8)
        def pay():
            r=cur.execute("SELECT id,ticket,loan_amount,interest_rate,fee FROM loans WHERE ticket=?",(ent.get().strip(),)).fetchone()
            if not r: return messagebox.showerror("Not found","Pawn ticket not found.")
            bal=loan_balance(r[0])
            amount=tk.simpledialog.askfloat("Payment",f"Balance: {money(bal)}\nEnter payment:")
            if amount is None or amount<=0: return
            if amount>bal: amount=bal
            method=tk.simpledialog.askstring("Payment Method","Cash / Card / EFT","initialvalue="Cash") or "Cash"
            cur.execute("INSERT INTO payments(loan_id,amount,method,paid_at,cashier) VALUES(?,?,?,?,?)",(r[0],amount,method,datetime.now().isoformat(timespec="seconds"),"Admin"))
            if amount>=bal-0.001: cur.execute("UPDATE loans SET status='REDEEMED' WHERE id=?",(r[0],))
            conn.commit()
            messagebox.showinfo("Payment Saved",f"Received {money(amount)}\nRemaining: {money(loan_balance(r[0]))}")
            self.show_payments()
        tk.Button(top,text="TAKE PAYMENT",command=pay,bg="#1f6feb",fg="white",padx=15,pady=7).pack(side="left")
        cols=("Ticket","Customer","Item","Balance","Due","Status")
        tv=ttk.Treeview(body,columns=cols,show="headings")
        for c in cols: tv.heading(c,text=c); tv.column(c,width=150)
        tv.pack(fill="both",expand=True)
        for r in cur.execute("""SELECT l.ticket,c.name,l.item,l.id,l.due_date,l.status FROM loans l
                                LEFT JOIN customers c ON c.id=l.customer_id WHERE l.status='ACTIVE' ORDER BY l.due_date"""):
            tv.insert("", "end", values=(r[0],r[1],r[2],money(loan_balance(r[3])),r[4],r[5]))

    def show_inventory(self):
        body=self.header("Pawn Inventory"); body.pack(fill="both",expand=True,padx=20,pady=20)
        cols=("Ticket","Item","Category","Customer","Location","Market Value","Loan","Due","Status")
        tv=ttk.Treeview(body,columns=cols,show="headings")
        for c in cols: tv.heading(c,text=c); tv.column(c,width=125)
        tv.pack(fill="both",expand=True)
        for r in cur.execute("""SELECT l.ticket,l.item,l.category,c.name,l.location,l.market_value,l.loan_amount,l.due_date,l.status
                                FROM loans l LEFT JOIN customers c ON c.id=l.customer_id
                                WHERE l.status IN ('ACTIVE','FOR SALE') ORDER BY l.id DESC"""):
            tv.insert("", "end", values=(r[0],r[1],r[2],r[3],r[4],money(r[5]),money(r[6]),r[7],r[8]))

    def show_sales(self):
        body=self.header("Sales"); body.pack(fill="both",expand=True,padx=20,pady=20)
        top=tk.Frame(body,bg="#eef1f5"); top.pack(fill="x",pady=(0,15))
        tk.Button(top,text="SELL PAWN ITEM",command=self.sell_item,bg="#198754",fg="white",padx=15,pady=8).pack(side="left")
        cols=("Sale","Ticket","Item","Buyer","Price","Date","Method")
        tv=ttk.Treeview(body,columns=cols,show="headings")
        for c in cols: tv.heading(c,text=c); tv.column(c,width=150)
        tv.pack(fill="both",expand=True)
        for r in cur.execute("SELECT id,loan_id,item,buyer,price,sold_at,method FROM sales ORDER BY id DESC"):
            ticket=cur.execute("SELECT ticket FROM loans WHERE id=?",(r[1],)).fetchone()
            tv.insert("", "end", values=(r[0],ticket[0] if ticket else "",r[2],r[3],money(r[4]),r[5],r[6]))

    def sell_item(self):
        ticket=tk.simpledialog.askstring("Sell Item","Pawn ticket number:")
        if not ticket:return
        r=cur.execute("SELECT id,item,status FROM loans WHERE ticket=?",(ticket,)).fetchone()
        if not r:return messagebox.showerror("Not found","Ticket not found.")
        if r[2] not in ("FOR SALE","ACTIVE"): return messagebox.showerror("Cannot sell","This item is not available for sale.")
        buyer=tk.simpledialog.askstring("Buyer","Buyer name:") or "Walk-in"
        price=tk.simpledialog.askfloat("Sale Price","Enter selling price:")
        if price is None:return
        method=tk.simpledialog.askstring("Payment","Cash / Card / EFT","initialvalue="Cash") or "Cash"
        cur.execute("INSERT INTO sales(loan_id,item,buyer,price,sold_at,method) VALUES(?,?,?,?,?,?)",(r[0],r[1],buyer,price,datetime.now().isoformat(timespec="seconds"),method))
        cur.execute("UPDATE loans SET status='SOLD' WHERE id=?",(r[0],))
        conn.commit(); messagebox.showinfo("Sold",f"{r[1]} sold for {money(price)}"); self.show_sales()

    def show_overdue(self):
        body=self.header("Overdue Loans"); body.pack(fill="both",expand=True,padx=20,pady=20)
        today=datetime.now().date().isoformat()
        cols=("Ticket","Customer","Item","Balance","Due Date","Days Overdue")
        tv=ttk.Treeview(body,columns=cols,show="headings")
        for c in cols: tv.heading(c,text=c); tv.column(c,width=180)
        tv.pack(fill="both",expand=True)
        for r in cur.execute("""SELECT l.ticket,c.name,l.item,l.id,l.due_date FROM loans l
                                LEFT JOIN customers c ON c.id=l.customer_id
                                WHERE l.status='ACTIVE' AND l.due_date < ? ORDER BY l.due_date""",(today,)):
            days=(datetime.now().date()-datetime.fromisoformat(r[4]).date()).days
            tv.insert("", "end", values=(r[0],r[1],r[2],money(loan_balance(r[3])),r[4],days))

    def show_reports(self):
        body=self.header("Reports"); body.pack(fill="both",expand=True,padx=20,pady=20)
        today=datetime.now().date().isoformat()
        loans=cur.execute("SELECT COUNT(*),COALESCE(SUM(loan_amount),0) FROM loans WHERE substr(start_date,1,10)=?",(today,)).fetchone()
        pays=cur.execute("SELECT COUNT(*),COALESCE(SUM(amount),0) FROM payments WHERE substr(paid_at,1,10)=?",(today,)).fetchone()
        sales=cur.execute("SELECT COUNT(*),COALESCE(SUM(price),0) FROM sales WHERE substr(sold_at,1,10)=?",(today,)).fetchone()
        overdue=cur.execute("SELECT COUNT(*) FROM loans WHERE status='ACTIVE' AND due_date<?",(today,)).fetchone()[0]
        lines=[("Today's Loans",f"{loans[0]} / {money(loans[1])}"),("Today's Payments",f"{pays[0]} / {money(pays[1])}"),
               ("Today's Sales",f"{sales[0]} / {money(sales[1])}"),("Overdue Loans",str(overdue)),
               ("Active Loan Balance",money(sum(loan_balance(x[0]) for x in cur.execute("SELECT id FROM loans WHERE status='ACTIVE'"))))]
        for t,v in lines:
            f=tk.Frame(body,bg="white"); f.pack(fill="x",pady=5)
            tk.Label(f,text=t,font=("Segoe UI",11,"bold"),bg="white",width=25,anchor="w").pack(side="left",padx=15,pady=15)
            tk.Label(f,text=v,font=("Segoe UI",14),bg="white").pack(side="left")

    def show_settings(self):
        body=self.header("Settings"); body.pack(fill="both",expand=True,padx=20,pady=20)
        form=tk.Frame(body,bg="white"); form.pack(fill="both",expand=True)
        fields={}
        labels=[("shop_name","Shop Name"),("address","Address"),("phone","Telephone"),("email","Email"),
                ("interest_rate","Default Interest %"),("service_fee","Default Service Fee"),("loan_days","Default Loan Days")]
        for i,(key,label) in enumerate(labels):
            tk.Label(form,text=label,bg="white",font=("Segoe UI",10,"bold")).grid(row=i,column=0,sticky="w",padx=25,pady=12)
            e=tk.Entry(form,width=55); e.insert(0,setting(key)); e.grid(row=i,column=1,padx=15,pady=12); fields[key]=e
        def save():
            for k,e in fields.items(): cur.execute("UPDATE settings SET value=? WHERE key=?",(e.get(),k))
            conn.commit(); messagebox.showinfo("Saved","Settings updated."); self.show_dashboard()
        tk.Button(form,text="SAVE SETTINGS",command=save,bg="#1f6feb",fg="white",padx=20,pady=9).grid(row=8,column=1,pady=20)

    def backup(self):
        stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        dest=os.path.join(BACKUP_DIR,f"pawnpro_backup_{stamp}.db")
        conn.commit(); shutil.copy2(DB,dest)
        messagebox.showinfo("Backup Complete",f"Backup saved to:\n{dest}")

if __name__=="__main__":
    # Import simpledialog late so startup remains clean.
    import tkinter.simpledialog
    App().mainloop()
