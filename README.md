# 📡 Ubertooth Bluetooth Spy 🕵️‍♂️

![Hacker Theme](https://img.shields.io/badge/Theme-Hacker-brightgreen)
![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![License](https://img.shields.io/badge/License-GPLv3-red)

## 🚀 Overview

Ubertooth Bluetooth Spy is a cutting-edge Bluetooth surveillance tool that leverages the power of Ubertooth One to intercept and analyze Bluetooth Low Energy (BLE) advertisements. With real-time monitoring capabilities and Discord webhook integration, it's the perfect tool for security researchers, penetration testers, and Bluetooth enthusiasts.

## 🔧 Features

- 🔍 Real-time BLE advertisement interception
- 📊 Detailed parsing of advertisement data
- 🚨 Automatic device name decoding
- 📡 Continuous monitoring with auto-reconnect
- 🔔 Discord webhook integration for remote notifications
- 🐛 Debug mode for in-depth analysis

## ☠️ Prerequisites!

You need an Ubertooth device and have all the drivers installed. Try this to be sure:

```
ubertooth-util -v
```

If not, you can order one here, 5% discount code "ROCKETGOD":
[Lab401](https://lab401.com/r?id=iop7bf)

More info at [Great Scott Gadgets](https://www.greatscottgadgets.com)

## 🛠 Installation

1. Clone this repository:
   ```
   git clone https://github.com/RocketGod-git/Ubertooth-Bluetooth-Spy.git
   ```

2. Navigate to the project directory:
   ```
   cd Ubertooth-Bluetooth-Spy
   ```

3. The script will detect missing dependencies and provide the suggested pip install line. This is what you'll need though.
   ```
   pip install requests colorama rich pyusb
   ```

## ⚙️ Configuration

### Discord Webhook (Optional)

To enable Discord notifications:

1. Open `ubertooth.py` in your favorite text editor.
2. Locate the following line near the top of the file:
   ```python
   WEBHOOK_URL = ""
   ```
3. Replace the empty string with your Discord webhook URL:
   ```python
   WEBHOOK_URL = "https://discord.com/api/webhooks/your/webhook/url/here"
   ```
![image](https://github.com/user-attachments/assets/8b84e32f-fe36-453f-ba40-67ef349bbd05)

## 🚀 Usage

Run the script with:

```
python3 ubertooth.py
```

For debug mode:

```
python3 ubertooth.py --debug
```

## 🎛 Controls

- Press `Ctrl+C` to gracefully stop the script.

## 🖼 Output

Ubertooth Bluetooth Spy provides rich, colorful console output for easy reading:

```
📡 Collecting advertisements...
📊 Collected 10 advertisements
╭──────────────────────── 🚨 FitBit Versa 3 🚨 ─────────────────────────╮
│ Field       │ Value                                                  │
│ Device Name │ FitBit Versa 3                                         │
│ Timestamp   │ 2024-08-02 15:30:45                                    │
│ Frequency   │ 2402 MHz                                               │
│ Address     │ 00:11:22:33:44:55                                      │
│ RSSI        │ -67                                                    │
│ Data        │ 02011A020A0C0AFF4C001005031B57F9C3                     │
│ Type        │ ADV_IND                                                │
│ Details     │ systime=1659456645 freq=2402 addr=00:11:22:33:44:55... │
╰────────────────────────────────────────────────────────────────────╯
```
![image](https://github.com/user-attachments/assets/c381c381-629f-4b1a-8302-07e824504552)

And to Discord:

![image](https://github.com/user-attachments/assets/7f0398f0-8db1-414c-9acc-ed476a99edeb)


## 🛡 Disclaimer

This tool is for educational and research purposes only. Always respect privacy laws and obtain necessary permissions before monitoring any Bluetooth traffic.

## 📜 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check [issues page](https://github.com/RocketGod-git/Ubertooth-Bluetooth-Spy/issues).

## 💖 Show your support

Give a ⭐️ if this project helped you!

## 📞 Contact

- GitHub:    [@RocketGod-git](https://github.com/RocketGod-git)
- GitHub.io  [ExtraFunStuff]{https://RocketGod-git.GitHub.io) 

![RocketGod](https://github.com/RocketGod-git/Flipper_Zero/assets/57732082/f5d67cfd-585d-4b23-905f-37151e3d6a7d)
