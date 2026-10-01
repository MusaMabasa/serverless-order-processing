import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
import base64
import json
import sys
import urllib.parse

import boto3
import requests

# ============================================================
# BLUEIT TECHNOLOGY - SERVERLESS ORDER MANAGEMENT
# ============================================================

REGION = "af-south-1"
CLIENT_ID = "aa2neod1ua0lq8q5sa69ih2k1"
API_BASE = "https://1q545uor9j.execute-api.af-south-1.amazonaws.com/Prod"
API_URL = f"{API_BASE}/orders"

NAVY = "#071B33"
NAVY_LIGHT = "#102A4C"
BLUE = "#0878D1"
BLUE_HOVER = "#0668B6"
BACKGROUND = "#F4F7FA"
CARD = "#FFFFFF"
TEXT = "#172033"
MUTED = "#697586"
BORDER = "#DCE3EA"
SUCCESS = "#138A55"
WARNING = "#B7791F"
DANGER = "#C53030"
WHITE = "#FFFFFF"

auth_token = None
current_username = None
current_claims = {}
orders_cache = []
admin_users_cache = []

cognito = boto3.client("cognito-idp", region_name=REGION)


def resource_path(relative_path):
    try:
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path


def rand(value):
    try:
        number = float(value)
        return f"R {number:,.0f}" if number.is_integer() else f"R {number:,.2f}"
    except (TypeError, ValueError):
        return "R 0.00"


def auth_headers():
    return {"Authorization": auth_token or "", "Content-Type": "application/json"}


def api_request(method, path, **kwargs):
    url = f"{API_BASE}{path}"
    headers = kwargs.pop("headers", {})
    headers.update(auth_headers())
    response = requests.request(method, url, headers=headers, timeout=20, **kwargs)
    try:
        body = response.json()
    except ValueError:
        body = {"message": response.text or f"HTTP {response.status_code}"}
    return response, body


def decode_claims(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
    except Exception:
        return {}


def is_admin():
    groups = current_claims.get("cognito:groups", [])
    if isinstance(groups, str):
        groups = [g.strip() for g in groups.strip("[]").split(",") if g.strip()]
    return "Admins" in groups


def token_username():
    return current_claims.get("cognito:username") or current_claims.get("username") or current_username or ""


def set_status(message, kind="normal"):
    colours = {"normal": MUTED, "success": SUCCESS, "warning": WARNING, "error": DANGER}
    status_message.config(text=message, fg=colours.get(kind, MUTED))


def clear_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()


def show_page(page):
    login_page.pack_forget()
    app_page.pack_forget()
    if page == "login":
        login_page.pack(fill="both", expand=True)
    else:
        app_page.pack(fill="both", expand=True)


def set_active_nav(active_button):
    for button in nav_buttons:
        button.config(bg=NAVY, fg="#B8C6D9")
    if active_button:
        active_button.config(bg=NAVY_LIGHT, fg=WHITE)


def button(parent, text, command, danger=False):
    return tk.Button(
        parent, text=text, command=command, font=("Segoe UI", 9, "bold"),
        bg=DANGER if danger else BLUE, fg=WHITE,
        activebackground="#A82424" if danger else BLUE_HOVER,
        activeforeground=WHITE, relief="flat", cursor="hand2", padx=14, pady=8
    )


def secondary_button(parent, text, command):
    return tk.Button(
        parent, text=text, command=command, font=("Segoe UI", 9, "bold"),
        bg=WHITE, fg=BLUE, activebackground="#EAF4FC", activeforeground=BLUE,
        relief="solid", bd=1, cursor="hand2", padx=14, pady=7
    )


def make_tree(parent, columns):
    holder = tk.Frame(parent, bg=CARD)
    holder.pack(fill="both", expand=True, padx=15, pady=15)

    tree = ttk.Treeview(holder, columns=[c[0] for c in columns], show="headings", selectmode="browse")
    for key, title, width, anchor in columns:
        tree.heading(key, text=title)
        tree.column(key, width=width, anchor=anchor)

    scrollbar = ttk.Scrollbar(holder, orient="vertical", command=tree.yview, style="Win11.Vertical.TScrollbar")
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    return tree


# ============================================================
# LOGIN / FIRST PASSWORD CHANGE
# ============================================================

def complete_new_password(username, session):
    window = tk.Toplevel(root)
    window.title("Set New Password")
    window.geometry("430x330")
    window.configure(bg=BACKGROUND)
    window.transient(root)
    window.grab_set()

    tk.Label(window, text="Create your password", font=("Segoe UI", 20, "bold"),
             bg=BACKGROUND, fg=TEXT).pack(anchor="w", padx=35, pady=(30, 6))
    tk.Label(window, text="Your temporary password must be replaced before you continue.",
             font=("Segoe UI", 9), bg=BACKGROUND, fg=MUTED, wraplength=350,
             justify="left").pack(anchor="w", padx=35, pady=(0, 20))

    new_entry = tk.Entry(window, show="●", font=("Segoe UI", 11), relief="solid", bd=1)
    new_entry.pack(fill="x", padx=35, ipady=8, pady=(0, 12))
    confirm_entry = tk.Entry(window, show="●", font=("Segoe UI", 11), relief="solid", bd=1)
    confirm_entry.pack(fill="x", padx=35, ipady=8)

    result = {"auth": None}

    def submit():
        new_password = new_entry.get()
        confirm = confirm_entry.get()
        if not new_password or new_password != confirm:
            messagebox.showerror("Password", "Passwords must match and cannot be blank.", parent=window)
            return
        try:
            challenge = cognito.respond_to_auth_challenge(
                ClientId=CLIENT_ID,
                ChallengeName="NEW_PASSWORD_REQUIRED",
                Session=session,
                ChallengeResponses={"USERNAME": username, "NEW_PASSWORD": new_password},
            )
            result["auth"] = challenge.get("AuthenticationResult")
            window.destroy()
        except Exception as exc:
            messagebox.showerror("Password", str(exc), parent=window)

    button(window, "SET PASSWORD", submit).pack(fill="x", padx=35, pady=22)
    new_entry.focus_set()
    root.wait_window(window)
    return result["auth"]


def login(event=None):
    global auth_token, current_username, current_claims

    username = username_entry.get().strip()
    password = password_entry.get()
    if not username or not password:
        login_error.config(text="Please enter your username and password.")
        return

    login_button.config(text="SIGNING IN...", state="disabled")
    root.update_idletasks()

    try:
        result = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )

        if result.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            challenge_username = result.get("ChallengeParameters", {}).get("USER_ID_FOR_SRP", username)
            authentication = complete_new_password(challenge_username, result["Session"])
            if not authentication:
                raise RuntimeError("Password change was not completed.")
        else:
            authentication = result.get("AuthenticationResult")

        if not authentication or "IdToken" not in authentication:
            raise RuntimeError("Cognito did not return an ID token.")

        auth_token = authentication["IdToken"]
        current_claims = decode_claims(auth_token)
        current_username = current_claims.get("email") or username

        login_error.config(text="")
        user_label.config(text=current_username)
        configure_admin_navigation()
        set_status("Connected securely to AWS", "success")
        show_page("app")
        show_dashboard()

    except Exception as exc:
        auth_token = None
        current_claims = {}
        login_error.config(text="Authentication failed. Please check your credentials.")
        print(f"Login error: {exc}")
    finally:
        login_button.config(text="SIGN IN", state="normal")


def logout():
    global auth_token, current_username, current_claims, orders_cache, admin_users_cache
    auth_token = None
    current_username = None
    current_claims = {}
    orders_cache = []
    admin_users_cache = []
    password_entry.delete(0, tk.END)
    configure_admin_navigation()
    set_status("Not connected", "normal")
    show_page("login")


# ============================================================
# DASHBOARD
# ============================================================

def create_dashboard_card(parent, column, title, value, subtitle):
    card = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    card.grid(row=0, column=column, sticky="nsew", padx=7)
    tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), bg=CARD, fg=MUTED).pack(
        anchor="w", padx=20, pady=(18, 5))
    tk.Label(card, text=value, font=("Segoe UI", 18, "bold"), bg=CARD, fg=BLUE).pack(
        anchor="w", padx=20)
    tk.Label(card, text=subtitle, font=("Segoe UI", 9), bg=CARD, fg=MUTED).pack(
        anchor="w", padx=20, pady=(4, 18))


def show_dashboard():
    set_active_nav(dashboard_button)
    clear_frame(content_frame)

    header = tk.Frame(content_frame, bg=BACKGROUND)
    header.pack(fill="x", padx=32, pady=(30, 15))
    tk.Label(header, text="Dashboard", font=("Segoe UI", 24, "bold"),
             bg=BACKGROUND, fg=TEXT).pack(anchor="w")
    tk.Label(header, text="BlueIT Serverless Order Management",
             font=("Segoe UI", 10), bg=BACKGROUND, fg=MUTED).pack(anchor="w", pady=(4, 0))

    cards = tk.Frame(content_frame, bg=BACKGROUND)
    cards.pack(fill="x", padx=32, pady=10)
    for column in range(3):
        cards.grid_columnconfigure(column, weight=1)
    create_dashboard_card(cards, 0, "AWS REGION", "af-south-1", "Cape Town")
    create_dashboard_card(cards, 1, "ORDER PIPELINE", "ACTIVE", "Serverless processing")
    create_dashboard_card(cards, 2, "ACCESS", "ADMIN" if is_admin() else "USER",
                          "Cognito authenticated")

    architecture = tk.Frame(content_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    architecture.pack(fill="x", padx=32, pady=18)
    tk.Label(architecture, text="AWS Architecture", font=("Segoe UI", 14, "bold"),
             bg=CARD, fg=TEXT).pack(anchor="w", padx=22, pady=(20, 5))
    tk.Label(
        architecture,
        text="Desktop Client  →  Amazon Cognito  →  API Gateway  →  AWS Lambda  →  "
             "Amazon SQS  →  AWS Lambda  →  DynamoDB",
        font=("Segoe UI", 10), bg=CARD, fg=MUTED, wraplength=850, justify="left"
    ).pack(anchor="w", padx=22, pady=(5, 22))


# ============================================================
# CREATE ORDER
# ============================================================

def create_field(parent, label, row, column):
    container = tk.Frame(parent, bg=CARD)
    container.grid(row=row, column=column, sticky="ew", padx=8, pady=8)
    tk.Label(container, text=label, font=("Segoe UI", 9, "bold"),
             bg=CARD, fg=TEXT).pack(anchor="w", pady=(0, 6))
    entry = tk.Entry(container, font=("Segoe UI", 11), bg=WHITE, fg=TEXT,
                     insertbackground=TEXT, relief="solid", bd=1)
    entry.pack(fill="x", ipady=8)
    return entry


def update_total(event=None):
    try:
        total_label.config(text=rand(int(quantity_entry.get()) * float(price_entry.get())))
    except (ValueError, AttributeError):
        total_label.config(text="R 0.00")


def show_create_order():
    global customer_entry, email_entry, product_entry, quantity_entry, price_entry, total_label, order_result

    set_active_nav(create_button)
    clear_frame(content_frame)

    header = tk.Frame(content_frame, bg=BACKGROUND)
    header.pack(fill="x", padx=32, pady=(30, 15))
    tk.Label(header, text="Create New Order", font=("Segoe UI", 24, "bold"),
             bg=BACKGROUND, fg=TEXT).pack(anchor="w")
    tk.Label(header, text="Submit an order to the AWS serverless processing pipeline.",
             font=("Segoe UI", 10), bg=BACKGROUND, fg=MUTED).pack(anchor="w", pady=(4, 0))

    form_card = tk.Frame(content_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    form_card.pack(fill="both", expand=True, padx=32, pady=(5, 30))
    form = tk.Frame(form_card, bg=CARD)
    form.pack(fill="x", padx=30, pady=25)
    form.grid_columnconfigure(0, weight=1)
    form.grid_columnconfigure(1, weight=1)

    customer_entry = create_field(form, "Customer Name", 0, 0)
    email_entry = create_field(form, "Customer Email", 0, 1)
    product_entry = create_field(form, "Product / Service", 1, 0)
    quantity_entry = create_field(form, "Quantity", 1, 1)
    price_entry = create_field(form, "Unit Price (ZAR)", 2, 0)
    quantity_entry.insert(0, "1")
    quantity_entry.bind("<KeyRelease>", update_total)
    price_entry.bind("<KeyRelease>", update_total)

    total_box = tk.Frame(form, bg="#F5F9FD")
    total_box.grid(row=2, column=1, sticky="nsew", padx=8, pady=8)
    tk.Label(total_box, text="ORDER TOTAL", font=("Segoe UI", 9, "bold"),
             bg="#F5F9FD", fg=MUTED).pack(anchor="w", padx=18, pady=(14, 2))
    total_label = tk.Label(total_box, text="R 0.00", font=("Segoe UI", 20, "bold"),
                           bg="#F5F9FD", fg=BLUE)
    total_label.pack(anchor="w", padx=18, pady=(0, 14))

    actions = tk.Frame(form_card, bg=CARD)
    actions.pack(fill="x", padx=38, pady=(0, 15))
    button(actions, "CREATE ORDER", create_order).pack(side="left")
    order_result = tk.Label(actions, text="", font=("Segoe UI", 10), bg=CARD, fg=SUCCESS)
    order_result.pack(side="left", padx=18)


def create_order():
    customer = customer_entry.get().strip()
    email = email_entry.get().strip()
    product = product_entry.get().strip()

    if not customer or not email or not product:
        messagebox.showwarning("Missing Information", "Please complete all order fields.")
        return

    try:
        quantity = int(quantity_entry.get())
        price = float(price_entry.get())
        if quantity <= 0 or price < 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Invalid Order", "Quantity and price are invalid.")
        return

    payload = {
        "customer_name": customer,
        "customer_email": email,
        "items": [{"product": product, "quantity": quantity, "price": price}],
    }

    try:
        order_result.config(text="Submitting order...", fg=MUTED)
        root.update_idletasks()
        response, body = api_request("POST", "/orders", json=payload)
        if response.ok:
            order_id = body.get("order_id", "Unknown")
            order_result.config(text=f"✓ {order_id} accepted for processing", fg=SUCCESS)
            messagebox.showinfo("Order Created", f"Order {order_id} was successfully submitted to AWS.")
        else:
            message = body.get("message", "Unable to create order.")
            order_result.config(text=message, fg=DANGER)
            messagebox.showerror("Order Error", f"HTTP {response.status_code}\n\n{message}")
    except requests.RequestException as exc:
        order_result.config(text="Unable to connect to AWS", fg=DANGER)
        messagebox.showerror("Network Error", str(exc))


# ============================================================
# ORDERS
# ============================================================

def show_orders():
    global order_count_label, orders_tree
    set_active_nav(orders_button)
    clear_frame(content_frame)

    header = tk.Frame(content_frame, bg=BACKGROUND)
    header.pack(fill="x", padx=32, pady=(30, 15))
    title_area = tk.Frame(header, bg=BACKGROUND)
    title_area.pack(side="left")
    tk.Label(title_area, text="Orders", font=("Segoe UI", 24, "bold"),
             bg=BACKGROUND, fg=TEXT).pack(anchor="w")
    order_count_label = tk.Label(title_area, text="Loading orders...", font=("Segoe UI", 10),
                                 bg=BACKGROUND, fg=MUTED)
    order_count_label.pack(anchor="w", pady=(4, 0))
    secondary_button(header, "↻  REFRESH", load_orders).pack(side="right")

    table_card = tk.Frame(content_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    table_card.pack(fill="both", expand=True, padx=32, pady=(5, 30))
    columns = [
        ("order", "ORDER ID", 140, "w"), ("customer", "CUSTOMER", 190, "w"),
        ("product", "PRODUCT", 210, "w"), ("quantity", "QTY", 65, "center"),
        ("total", "TOTAL", 120, "e"), ("status", "STATUS", 110, "center"),
    ]
    orders_tree = make_tree(table_card, columns)
    orders_tree.bind("<Double-1>", show_order_details)
    load_orders()


def fetch_orders():
    response, body = api_request("GET", "/orders")
    if not response.ok:
        raise RuntimeError(body.get("message", "Unable to retrieve orders."))
    return body.get("orders", [])


def populate_order_tree(tree, orders):
    for row in tree.get_children():
        tree.delete(row)
    for order in orders:
        items = order.get("items", [])
        first = items[0] if items else {}
        product = first.get("product", "-")
        if len(items) > 1:
            product += f" +{len(items)-1} more"
        tree.insert("", "end", values=(
            order.get("order_id", "-"), order.get("customer_name", "-"),
            product, first.get("quantity", "-"), rand(order.get("total", 0)),
            order.get("status", "-")
        ))


def load_orders():
    global orders_cache
    try:
        order_count_label.config(text="Loading orders...")
        orders_cache = fetch_orders()
        populate_order_tree(orders_tree, orders_cache)
        order_count_label.config(text=f"{len(orders_cache)} orders retrieved from Amazon DynamoDB")
        set_status("AWS data synchronized", "success")
    except Exception as exc:
        order_count_label.config(text="Unable to load orders")
        set_status("AWS synchronization failed", "error")
        messagebox.showerror("Orders", str(exc))


def show_order_details(event=None):
    selection = orders_tree.selection()
    if not selection:
        return
    order_id = orders_tree.item(selection[0], "values")[0]
    order = next((x for x in orders_cache if x.get("order_id") == order_id), None)
    if not order:
        return

    window = tk.Toplevel(root)
    window.title(f"Order {order_id}")
    window.geometry("620x540")
    window.configure(bg=BACKGROUND)
    window.transient(root)

    tk.Label(window, text=order_id, font=("Segoe UI", 20, "bold"),
             bg=BACKGROUND, fg=TEXT).pack(anchor="w", padx=25, pady=(25, 5))
    tk.Label(window, text=order.get("status", "-"), font=("Segoe UI", 10, "bold"),
             bg=BACKGROUND, fg=SUCCESS).pack(anchor="w", padx=25)

    details = tk.Frame(window, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    details.pack(fill="both", expand=True, padx=25, pady=20)

    fields = [
        ("Customer", order.get("customer_name", "-")),
        ("Email", order.get("customer_email", "-")),
        ("Total", rand(order.get("total", 0))),
        ("Created", order.get("created_at", "-")),
        ("Processed", order.get("processed_at", "-")),
    ]
    for label, value in fields:
        row = tk.Frame(details, bg=CARD)
        row.pack(fill="x", padx=20, pady=7)
        tk.Label(row, text=label, width=12, anchor="w", font=("Segoe UI", 9, "bold"),
                 bg=CARD, fg=MUTED).pack(side="left")
        tk.Label(row, text=value, anchor="w", font=("Segoe UI", 10),
                 bg=CARD, fg=TEXT).pack(side="left")

    tk.Label(details, text="ITEMS", font=("Segoe UI", 9, "bold"),
             bg=CARD, fg=MUTED).pack(anchor="w", padx=20, pady=(15, 5))
    for item in order.get("items", []):
        item_text = f"{item.get('product','-')}   × {item.get('quantity','-')}   @ {rand(item.get('price',0))}"
        tk.Label(details, text=item_text, font=("Segoe UI", 10),
                 bg=CARD, fg=TEXT).pack(anchor="w", padx=20, pady=4)


# ============================================================
# ADMIN CONSOLE
# ============================================================

def require_admin_ui():
    if not is_admin():
        messagebox.showerror("Administrator", "Administrator access is required.")
        show_dashboard()
        return False
    return True


def selected_user():
    selection = admin_users_tree.selection()
    if not selection:
        messagebox.showwarning("User Management", "Select a user first.")
        return None
    values = admin_users_tree.item(selection[0], "values")
    username = values[1]
    return next((u for u in admin_users_cache if u.get("username") == username), None)


def load_admin_users():
    global admin_users_cache
    try:
        admin_user_count.config(text="Loading users...")
        response, body = api_request("GET", "/admin/users")
        if not response.ok:
            raise RuntimeError(body.get("message", "Unable to load users."))
        admin_users_cache = body.get("users", [])
        for row in admin_users_tree.get_children():
            admin_users_tree.delete(row)
        for user in admin_users_cache:
            admin_users_tree.insert("", "end", values=(
                user.get("email", "-"),
                user.get("username", "-"),
                "Enabled" if user.get("enabled") else "Disabled",
                user.get("status", "-"),
                "Admin" if user.get("is_admin") else "User",
            ))
        admin_user_count.config(text=f"{len(admin_users_cache)} Cognito users")
        set_status("Administrator data synchronized", "success")
    except Exception as exc:
        admin_user_count.config(text="Unable to load users")
        messagebox.showerror("Admin Console", str(exc))


def add_user_dialog():
    window = tk.Toplevel(root)
    window.title("Add User")
    window.geometry("480x410")
    window.configure(bg=BACKGROUND)
    window.transient(root)
    window.grab_set()

    tk.Label(window, text="Add Cognito User", font=("Segoe UI", 20, "bold"),
             bg=BACKGROUND, fg=TEXT).pack(anchor="w", padx=35, pady=(28, 5))
    tk.Label(window, text="The user will change the temporary password at first sign-in.",
             font=("Segoe UI", 9), bg=BACKGROUND, fg=MUTED).pack(anchor="w", padx=35, pady=(0, 18))

    tk.Label(window, text="EMAIL", font=("Segoe UI", 9, "bold"), bg=BACKGROUND, fg=TEXT).pack(anchor="w", padx=35)
    email = tk.Entry(window, font=("Segoe UI", 11), relief="solid", bd=1)
    email.pack(fill="x", padx=35, pady=(6, 15), ipady=8)

    tk.Label(window, text="TEMPORARY PASSWORD", font=("Segoe UI", 9, "bold"),
             bg=BACKGROUND, fg=TEXT).pack(anchor="w", padx=35)
    password = tk.Entry(window, font=("Segoe UI", 11), show="●", relief="solid", bd=1)
    password.pack(fill="x", padx=35, pady=(6, 12), ipady=8)

    admin_var = tk.BooleanVar(value=False)
    tk.Checkbutton(window, text="Grant administrator access", variable=admin_var,
                   font=("Segoe UI", 10), bg=BACKGROUND, fg=TEXT,
                   activebackground=BACKGROUND).pack(anchor="w", padx=31, pady=5)

    def submit():
        payload = {
            "email": email.get().strip(),
            "temporary_password": password.get(),
            "is_admin": admin_var.get(),
        }
        if not payload["email"] or not payload["temporary_password"]:
            messagebox.showwarning("Add User", "Email and temporary password are required.", parent=window)
            return
        try:
            response, body = api_request("POST", "/admin/users", json=payload)
            if not response.ok:
                raise RuntimeError(body.get("message", "Unable to create user."))
            messagebox.showinfo("Add User", "User created successfully.", parent=window)
            window.destroy()
            load_admin_users()
        except Exception as exc:
            messagebox.showerror("Add User", str(exc), parent=window)

    button(window, "CREATE USER", submit).pack(fill="x", padx=35, pady=20)
    email.focus_set()


def patch_selected_user(payload, confirmation, success):
    user = selected_user()
    if not user:
        return
    if not messagebox.askyesno("Confirm", confirmation.format(email=user.get("email") or user["username"])):
        return
    try:
        encoded = urllib.parse.quote(user["username"], safe="")
        response, body = api_request("PATCH", f"/admin/users/{encoded}", json=payload)
        if not response.ok:
            raise RuntimeError(body.get("message", "Unable to update user."))
        messagebox.showinfo("User Management", success)
        load_admin_users()
    except Exception as exc:
        messagebox.showerror("User Management", str(exc))


def toggle_user_enabled():
    user = selected_user()
    if not user:
        return
    enabled = not bool(user.get("enabled"))
    action = "enable" if enabled else "disable"
    patch_selected_user({"enabled": enabled}, f"Are you sure you want to {action} {{email}}?",
                        f"User {action}d successfully.")


def toggle_admin_access():
    user = selected_user()
    if not user:
        return
    grant = not bool(user.get("is_admin"))
    action = "grant administrator access to" if grant else "revoke administrator access from"
    patch_selected_user({"is_admin": grant}, f"Are you sure you want to {action} {{email}}?",
                        "Administrator access updated successfully.")


def delete_selected_user():
    user = selected_user()
    if not user:
        return
    label = user.get("email") or user["username"]
    if not messagebox.askyesno("Delete User", f"Permanently delete {label}?\n\nThis action cannot be undone."):
        return
    try:
        encoded = urllib.parse.quote(user["username"], safe="")
        response, body = api_request("DELETE", f"/admin/users/{encoded}")
        if not response.ok:
            raise RuntimeError(body.get("message", "Unable to delete user."))
        messagebox.showinfo("Delete User", "User deleted successfully.")
        load_admin_users()
    except Exception as exc:
        messagebox.showerror("Delete User", str(exc))


def admin_orders_by_status(status):
    return [o for o in orders_cache if str(o.get("status", "")).upper() == status]


def load_admin_orders():
    global orders_cache
    try:
        admin_order_count.config(text="Loading orders...")
        orders_cache = fetch_orders()
        populate_order_tree(admin_pending_tree, admin_orders_by_status("QUEUED"))
        populate_order_tree(admin_accepted_tree, admin_orders_by_status("ACCEPTED"))
        populate_order_tree(admin_completed_tree, admin_orders_by_status("COMPLETED"))
        pending = len(admin_orders_by_status("QUEUED"))
        accepted = len(admin_orders_by_status("ACCEPTED"))
        completed = len(admin_orders_by_status("COMPLETED"))
        admin_order_count.config(
            text=f"{len(orders_cache)} orders  •  {pending} pending  •  {accepted} accepted  •  {completed} completed"
        )
    except Exception as exc:
        admin_order_count.config(text="Unable to load orders")
        messagebox.showerror("Order Administration", str(exc))


def selected_admin_order(tree, title):
    selection = tree.selection()
    if not selection:
        messagebox.showwarning("Order Administration", f"Select an order from {title} first.")
        return None
    return tree.item(selection[0], "values")[0]


def change_admin_order_status(tree, current_status, new_status, action_label):
    order_id = selected_admin_order(tree, current_status.title() + " Orders")
    if not order_id:
        return
    if not messagebox.askyesno(
        action_label,
        f"{action_label} {order_id}?\n\nStatus: {current_status} → {new_status}"
    ):
        return
    try:
        encoded = urllib.parse.quote(str(order_id), safe="")
        response, body = api_request(
            "PATCH", f"/admin/orders/{encoded}", json={"status": new_status}
        )
        if not response.ok:
            raise RuntimeError(body.get("message", f"Unable to {action_label.lower()}."))
        messagebox.showinfo(action_label, body.get("message", f"{order_id} updated successfully."))
        load_admin_orders()
    except Exception as exc:
        messagebox.showerror(action_label, str(exc))


def accept_admin_order():
    change_admin_order_status(admin_pending_tree, "QUEUED", "ACCEPTED", "Accept Order")


def complete_admin_order():
    change_admin_order_status(admin_accepted_tree, "ACCEPTED", "COMPLETED", "Mark Complete")


def delete_admin_order(tree=None):
    tree = tree or admin_pending_tree
    order_id = selected_admin_order(tree, "selected list")
    if not order_id:
        return
    if not messagebox.askyesno(
        "Delete Order",
        f"Permanently delete {order_id} from DynamoDB?\n\nThis action cannot be undone."
    ):
        return
    try:
        encoded = urllib.parse.quote(str(order_id), safe="")
        response, body = api_request("DELETE", f"/admin/orders/{encoded}")
        if not response.ok:
            raise RuntimeError(body.get("message", "Unable to delete order."))
        messagebox.showinfo("Delete Order", f"{order_id} deleted successfully.")
        load_admin_orders()
    except Exception as exc:
        messagebox.showerror("Delete Order", str(exc))


def make_admin_order_tab(notebook, title, status, action_text=None, action_command=None):
    tab = tk.Frame(notebook, bg=BACKGROUND)
    notebook.add(tab, text=f"  {title}  ")

    actions = tk.Frame(tab, bg=BACKGROUND)
    actions.pack(fill="x", pady=(14, 8))
    tk.Label(actions, text=f"{title} ({status})", font=("Segoe UI", 13, "bold"),
             bg=BACKGROUND, fg=TEXT).pack(side="left")
    secondary_button(actions, "REFRESH", load_admin_orders).pack(side="right", padx=4)
    button(actions, "DELETE ORDER", lambda: delete_admin_order(tree), danger=True).pack(side="right", padx=4)
    if action_text and action_command:
        button(actions, action_text, action_command).pack(side="right", padx=4)

    card = tk.Frame(tab, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    card.pack(fill="both", expand=True)
    tree = make_tree(card, [
        ("order", "ORDER ID", 140, "w"), ("customer", "CUSTOMER", 190, "w"),
        ("product", "PRODUCT", 210, "w"), ("quantity", "QTY", 65, "center"),
        ("total", "TOTAL", 120, "e"), ("status", "STATUS", 110, "center"),
    ])
    return tree


def show_admin_console():
    global admin_users_tree, admin_user_count, admin_order_count
    global admin_pending_tree, admin_accepted_tree, admin_completed_tree
    if not require_admin_ui():
        return

    set_active_nav(admin_button)
    clear_frame(content_frame)

    header = tk.Frame(content_frame, bg=BACKGROUND)
    header.pack(fill="x", padx=32, pady=(25, 12))
    tk.Label(header, text="Admin Console", font=("Segoe UI", 24, "bold"),
             bg=BACKGROUND, fg=TEXT).pack(anchor="w")
    admin_order_count = tk.Label(
        header, text="Manage users and process orders from pending to completion.",
        font=("Segoe UI", 10), bg=BACKGROUND, fg=MUTED
    )
    admin_order_count.pack(anchor="w", pady=(4, 0))

    notebook = ttk.Notebook(content_frame)
    notebook.pack(fill="both", expand=True, padx=32, pady=(5, 25))

    users_tab = tk.Frame(notebook, bg=BACKGROUND)
    notebook.add(users_tab, text="  Users  ")

    user_header = tk.Frame(users_tab, bg=BACKGROUND)
    user_header.pack(fill="x", pady=(16, 10))
    left = tk.Frame(user_header, bg=BACKGROUND)
    left.pack(side="left")
    tk.Label(left, text="User Management", font=("Segoe UI", 15, "bold"),
             bg=BACKGROUND, fg=TEXT).pack(anchor="w")
    admin_user_count = tk.Label(left, text="Loading users...", font=("Segoe UI", 9),
                                bg=BACKGROUND, fg=MUTED)
    admin_user_count.pack(anchor="w")

    actions = tk.Frame(user_header, bg=BACKGROUND)
    actions.pack(side="right")
    secondary_button(actions, "REFRESH", load_admin_users).pack(side="left", padx=4)
    button(actions, "ADD USER", add_user_dialog).pack(side="left", padx=4)
    secondary_button(actions, "ENABLE / DISABLE", toggle_user_enabled).pack(side="left", padx=4)
    secondary_button(actions, "GRANT / REVOKE ADMIN", toggle_admin_access).pack(side="left", padx=4)
    button(actions, "DELETE USER", delete_selected_user, danger=True).pack(side="left", padx=4)

    users_card = tk.Frame(users_tab, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    users_card.pack(fill="both", expand=True)
    admin_users_tree = make_tree(users_card, [
        ("email", "EMAIL", 220, "w"), ("username", "USERNAME", 260, "w"),
        ("enabled", "ENABLED", 90, "center"), ("status", "STATUS", 130, "center"),
        ("role", "ROLE", 90, "center"),
    ])

    admin_pending_tree = make_admin_order_tab(
        notebook, "Pending Orders", "QUEUED", "ACCEPT ORDER", accept_admin_order
    )
    admin_accepted_tree = make_admin_order_tab(
        notebook, "Accepted Orders", "ACCEPTED", "MARK COMPLETE", complete_admin_order
    )
    admin_completed_tree = make_admin_order_tab(
        notebook, "Completed Orders", "COMPLETED"
    )

    load_admin_users()
    load_admin_orders()


# ============================================================
# ROOT / STYLE
# ============================================================

root = tk.Tk()
root.title("BlueIT Technology | Serverless Order Management")
root.geometry("1180x720")
root.minsize(1000, 650)
root.configure(bg=BACKGROUND)

try:
    root.iconbitmap(str(resource_path("assets/blueit.ico")))
except Exception as exc:
    print(f"Window icon warning: {exc}")

style = ttk.Style()
try:
    style.theme_use("clam")
except tk.TclError:
    pass

style.configure("Treeview", background=WHITE, fieldbackground=WHITE, foreground=TEXT,
                rowheight=38, font=("Segoe UI", 9), borderwidth=0)
style.configure("Treeview.Heading", background="#EEF3F8", foreground=MUTED,
                font=("Segoe UI", 9, "bold"), relief="flat")
style.map("Treeview", background=[("selected", "#DDEFFC")], foreground=[("selected", TEXT)])

# Slim Windows 11-inspired scrollbar. ttk cannot reproduce native Win11 overlay
# geometry exactly, but this keeps it narrow, neutral and unobtrusive.
style.configure(
    "Win11.Vertical.TScrollbar",
    gripcount=0,
    background="#C5CBD3",
    darkcolor="#C5CBD3",
    lightcolor="#C5CBD3",
    troughcolor="#F4F6F8",
    bordercolor="#F4F6F8",
    arrowcolor="#68727E",
    relief="flat",
    width=11,
)
style.map("Win11.Vertical.TScrollbar",
          background=[("active", "#9EA7B2"), ("pressed", "#7D8793")])

style.configure("TNotebook", background=BACKGROUND, borderwidth=0)
style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=(16, 9),
                background="#E8EDF3", foreground=MUTED)
style.map("TNotebook.Tab", background=[("selected", WHITE)], foreground=[("selected", BLUE)])


# ============================================================
# LOGIN PAGE
# ============================================================

login_page = tk.Frame(root, bg=BACKGROUND)
login_left = tk.Frame(login_page, bg=NAVY, width=470)
login_left.pack(side="left", fill="both")
login_left.pack_propagate(False)

login_brand = tk.Frame(login_left, bg=NAVY)
login_brand.pack(expand=True, fill="both", padx=55, pady=70)

logo_path = resource_path("assets/blueit-logo.png")
logo_image = None
try:
    logo_image = tk.PhotoImage(file=str(logo_path))
    max_width = 280
    if logo_image.width() > max_width:
        factor = max(1, round(logo_image.width() / max_width))
        logo_image = logo_image.subsample(factor, factor)
    tk.Label(login_brand, image=logo_image, bg=NAVY).pack(anchor="w", pady=(0, 30))
except Exception as exc:
    print(f"Logo load warning: {exc}")
    tk.Label(login_brand, text="BLUEIT", font=("Segoe UI", 30, "bold"),
             bg=NAVY, fg=WHITE).pack(anchor="w", pady=(0, 30))

tk.Label(login_brand, text="Serverless Order\nManagement", font=("Segoe UI", 27, "bold"),
         justify="left", bg=NAVY, fg=WHITE).pack(anchor="w")
tk.Label(login_brand, text="Secure cloud-native order processing powered by Amazon Web Services.",
         font=("Segoe UI", 11), justify="left", wraplength=330,
         bg=NAVY, fg="#B8C6D9").pack(anchor="w", pady=(18, 0))
tk.Label(login_brand, text="Cognito  •  API Gateway  •  Lambda\nSQS  •  DynamoDB  •  CloudWatch",
         font=("Segoe UI", 9), justify="left", bg=NAVY, fg="#6FADE0").pack(anchor="w", pady=(35, 0))

login_right = tk.Frame(login_page, bg=BACKGROUND)
login_right.pack(side="right", fill="both", expand=True)
login_form = tk.Frame(login_right, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
login_form.place(relx=0.5, rely=0.5, anchor="center", width=430, height=440)

tk.Label(login_form, text="Welcome back", font=("Segoe UI", 24, "bold"),
         bg=CARD, fg=TEXT).pack(anchor="w", padx=42, pady=(42, 5))
tk.Label(login_form, text="Sign in with your secure AWS Cognito account.",
         font=("Segoe UI", 10), bg=CARD, fg=MUTED).pack(anchor="w", padx=42, pady=(0, 25))
tk.Label(login_form, text="USERNAME", font=("Segoe UI", 9, "bold"),
         bg=CARD, fg=TEXT).pack(anchor="w", padx=42)
username_entry = tk.Entry(login_form, font=("Segoe UI", 11), relief="solid", bd=1)
username_entry.pack(fill="x", padx=42, pady=(7, 18), ipady=8)
tk.Label(login_form, text="PASSWORD", font=("Segoe UI", 9, "bold"),
         bg=CARD, fg=TEXT).pack(anchor="w", padx=42)
password_entry = tk.Entry(login_form, font=("Segoe UI", 11), show="●", relief="solid", bd=1)
password_entry.pack(fill="x", padx=42, pady=(7, 20), ipady=8)
password_entry.bind("<Return>", login)
login_button = tk.Button(login_form, text="SIGN IN", font=("Segoe UI", 10, "bold"),
                         bg=BLUE, fg=WHITE, activebackground=BLUE_HOVER,
                         activeforeground=WHITE, relief="flat", cursor="hand2",
                         pady=10, command=login)
login_button.pack(fill="x", padx=42)
login_error = tk.Label(login_form, text="", font=("Segoe UI", 9), bg=CARD,
                       fg=DANGER, wraplength=330)
login_error.pack(padx=42, pady=12)


# ============================================================
# MAIN APPLICATION
# ============================================================

app_page = tk.Frame(root, bg=BACKGROUND)
sidebar = tk.Frame(app_page, bg=NAVY, width=230)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

sidebar_logo_frame = tk.Frame(sidebar, bg=NAVY)
sidebar_logo_frame.pack(fill="x", padx=22, pady=(28, 35))
if logo_image:
    tk.Label(sidebar_logo_frame, image=logo_image, bg=NAVY).pack(anchor="w")
else:
    tk.Label(sidebar_logo_frame, text="BLUEIT", font=("Segoe UI", 20, "bold"),
             bg=NAVY, fg=WHITE).pack(anchor="w")

tk.Label(sidebar, text="ORDER MANAGEMENT", font=("Segoe UI", 8, "bold"),
         bg=NAVY, fg="#6F849E").pack(anchor="w", padx=25, pady=(0, 8))

nav_buttons = []


def make_nav_button(text, command):
    b = tk.Button(sidebar, text=text, font=("Segoe UI", 10), bg=NAVY, fg="#B8C6D9",
                  activebackground=NAVY_LIGHT, activeforeground=WHITE, relief="flat",
                  anchor="w", cursor="hand2", padx=25, pady=12, command=command)
    b.pack(fill="x")
    nav_buttons.append(b)
    return b


dashboard_button = make_nav_button("▣   Dashboard", show_dashboard)
create_button = make_nav_button("＋   Create Order", show_create_order)
orders_button = make_nav_button("≡   Orders", show_orders)

admin_section_label = tk.Label(sidebar, text="ADMINISTRATION", font=("Segoe UI", 8, "bold"),
                               bg=NAVY, fg="#6F849E")
admin_button = tk.Button(sidebar, text="⚙   Admin Console", font=("Segoe UI", 10),
                         bg=NAVY, fg="#B8C6D9", activebackground=NAVY_LIGHT,
                         activeforeground=WHITE, relief="flat", anchor="w",
                         cursor="hand2", padx=25, pady=12, command=show_admin_console)
nav_buttons.append(admin_button)


def configure_admin_navigation():
    admin_section_label.pack_forget()
    admin_button.pack_forget()
    if is_admin():
        admin_section_label.pack(fill="x", anchor="w", padx=25, pady=(22, 8))
        admin_button.pack(fill="x")


sidebar_bottom = tk.Frame(sidebar, bg=NAVY)
sidebar_bottom.pack(side="bottom", fill="x", padx=20, pady=20)
tk.Label(sidebar_bottom, text="SIGNED IN AS", font=("Segoe UI", 8, "bold"),
         bg=NAVY, fg="#6F849E").pack(anchor="w")
user_label = tk.Label(sidebar_bottom, text="", font=("Segoe UI", 9), bg=NAVY,
                      fg=WHITE, wraplength=180, justify="left")
user_label.pack(anchor="w", pady=(3, 10))
tk.Button(sidebar_bottom, text="SIGN OUT", font=("Segoe UI", 8, "bold"),
          bg=NAVY_LIGHT, fg=WHITE, activebackground="#183B64",
          activeforeground=WHITE, relief="flat", cursor="hand2",
          padx=12, pady=7, command=logout).pack(anchor="w")

main_area = tk.Frame(app_page, bg=BACKGROUND)
main_area.pack(side="right", fill="both", expand=True)

# Pack status bar before content so it remains pinned at the bottom.
status_bar = tk.Frame(main_area, bg=WHITE, height=32, highlightbackground=BORDER, highlightthickness=1)
status_bar.pack(side="bottom", fill="x")
status_message = tk.Label(status_bar, text="Not connected", font=("Segoe UI", 8), bg=WHITE, fg=MUTED)
status_message.pack(side="left", padx=15, pady=6)
tk.Label(status_bar, text="BlueIT Technology  •  AWS Serverless Platform",
         font=("Segoe UI", 8), bg=WHITE, fg=MUTED).pack(side="right", padx=15)

content_frame = tk.Frame(main_area, bg=BACKGROUND)
content_frame.pack(fill="both", expand=True)

configure_admin_navigation()
show_page("login")
username_entry.focus_set()
root.mainloop()
