# Carvow Car Service - Multi-Device Web Application

Carvow is a web application for booking car service appointments, managing service history, and handling admin approvals.

## 🚀 How to Run on Any Device

### 1. Same Local Wi-Fi / Network (Smartphones, Tablets, Laptops)
1. Double-click `run.bat` on the host PC.
2. The server will start and display your Local IP address in the console, for example:
   ```text
   Local Access (This PC):    http://127.0.0.1:5001/
   Any Device on Wi-Fi/LAN:   http://192.168.x.x:5001/
   ```
3. Open the browser on **ANY device** (iPhone, Android phone, iPad, tablet, or another laptop) connected to the same Wi-Fi network and navigate to:
   `http://<YOUR-LOCAL-IP>:5001/`

---

### 2. Remote Access (Any Device Anywhere over the Internet)
1. Double-click `run_with_tunnel.bat` on the host PC.
2. A public SSH tunnel will open and generate a public HTTPS URL (e.g., `https://xxxx.lhr.life`).
3. Open that link on **ANY mobile phone or computer anywhere in the world** (even using mobile 4G/5G data).

---

## 🛠 Prerequisites & Dependencies
- **Python 3.x** installed.
- Dependencies installed via terminal:
  ```bash
  pip install -r requirements.txt
  ```

---

## 📂 Project Features
- **User Authentication**: Sign up, Login, Password management.
- **Appointment Booking**: Service selection, date/time slot picker, instant email notifications.
- **Appointment History**: Track appointment status (Pending, Confirmed, Completed).
- **Admin Dashboard**: Review booking requests, approve/reject appointments, add admin notes.
