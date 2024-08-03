# __________                  __             __     ________             .___ 
# \______   \  ____    ____  |  | __  ____ _/  |_  /  _____/   ____    __| _/ 
#  |       _/ /  _ \ _/ ___\ |  |/ /_/ __ \\   __\/   \  ___  /  _ \  / __ |  
#  |    |   \(  <_> )\  \___ |    < \  ___/ |  |  \    \_\  \(  <_> )/ /_/ |  
#  |____|_  / \____/  \___  >|__|_ \ \___  >|__|   \______  / \____/ \____ |  
#         \/              \/      \/     \/               \/              \/  
#
# Ubertooth Bluetooth Spy
# by RocketGod
# https://RocketGod-git.GitHub.io


import subprocess
import re
import json
import requests
import logging
import time
import argparse
from datetime import datetime
from requests.exceptions import RequestException, HTTPError
import signal
import sys
import select
import usb.core
import usb.util
import threading

from colorama import init

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import importlib.util

def check_module(module_name):
    if importlib.util.find_spec(module_name) is None:
        return False
    return True

required_modules = ['requests', 'colorama', 'rich', 'usb']
missing_modules = [module for module in required_modules if not check_module(module)]

if missing_modules:
    print("The following required modules are missing:")
    print(", ".join(missing_modules))
    print("\nPlease install them using the following command:")
    print(f"pip install {' '.join(missing_modules)}")
    exit(1)

init(autoreset=True)
console = Console()

WEBHOOK_URL = ""
UBERTOOTH_COMMAND = ["ubertooth-btle", "-n"]
ADVERTISEMENTS_PER_BATCH = 10
ADVERTISEMENTS_PER_WEBHOOK = 5
COLLECTION_TIMEOUT = 30
RETRY_DELAY = 5
MAX_RETRIES = 3
RECONNECT_DELAY = 10
DEVICE_CHECK_INTERVAL = 60
RATE_LIMIT_DELAY = 60
MAX_RESTART_ATTEMPTS = 3

UBERTOOTH_VENDOR_ID = 0x1d50
UBERTOOTH_PRODUCT_ID = 0x6002

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
args = parser.parse_args()

if args.debug:
    logger.setLevel(logging.DEBUG)

def signal_handler(sig, frame):
    console.print("[bold red]🛑 Stopping the script...[/bold red]")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def decode_device_name(hex_string):
    try:
        byte_string = bytes.fromhex(hex_string)
        return byte_string.decode('utf-8', errors='replace').strip()
    except Exception as e:
        console.print(f"[bold red]Error decoding device name: {e}[/bold red]")
        return hex_string

def parse_advertisement(adv):
    parsed = {
        "timestamp": "",
        "frequency": "",
        "address": "",
        "rssi": "",
        "data": "",
        "type": "",
        "name": "",
        "details": ""
    }
    
    lines = adv.split('\n')
    for line in lines:
        if line.startswith("systime="):
            parts = line.split()
            parsed["timestamp"] = datetime.fromtimestamp(int(parts[0].split("=")[1])).strftime('%Y-%m-%d %H:%M:%S')
            parsed["frequency"] = f"{parts[1].split('=')[1]} MHz"
            parsed["address"] = parts[2].split("=")[1]
            parsed["rssi"] = parts[-1].split("=")[1]
        elif line.strip().startswith("Data:"):
            parsed["data"] = line.split(":", 1)[1].strip()
        elif "Type:" in line:
            parsed["type"] = line.strip()
        elif "ScanRspData:" in line:
            scan_rsp_data = line.split(":", 1)[1].strip()
            parsed["name"] = parse_scan_rsp_data(scan_rsp_data)
        
        parsed["details"] += line + "\n"
    
    if not parsed["name"]:
        name_match = re.search(r"(Complete Local Name|Shortened Local Name).*?\n(.*?)\n", parsed["details"], re.DOTALL)
        if name_match:
            parsed["name"] = name_match.group(2).strip()
    
    if args.debug:
        console.print(Panel(json.dumps(parsed, indent=2), title="Parsed Advertisement", expand=False))
    return parsed

def parse_scan_rsp_data(scan_rsp_data):
    parts = scan_rsp_data.split()
    i = 0
    while i < len(parts):
        length = int(parts[i], 16)
        type_code = parts[i+1]
        if type_code == '09':
            name_hex = ''.join(parts[i+2:i+2+length-1])
            return decode_device_name(name_hex)
        i += length + 1
    return ""

def collect_advertisements(process):
    advertisements = []
    current_adv = ""
    start_time = time.time()
    last_data_time = start_time

    while time.time() - start_time < COLLECTION_TIMEOUT:
        try:
            ready, _, _ = select.select([process.stdout], [], [], 1)
            if ready:
                line = process.stdout.readline()
                if not line:
                    if time.time() - last_data_time > RECONNECT_DELAY:
                        console.print("[bold yellow]⚠️ No data received for a while. Reconnecting...[/bold yellow]")
                        return advertisements, True
                    continue
                
                last_data_time = time.time()
                
                if line.startswith("systime="):
                    if current_adv:
                        parsed_adv = parse_advertisement(current_adv)
                        if parsed_adv["name"] or len(advertisements) < ADVERTISEMENTS_PER_BATCH:
                            advertisements.append(parsed_adv)
                        if len(advertisements) >= ADVERTISEMENTS_PER_BATCH * 2:
                            return advertisements, False
                    current_adv = line
                else:
                    current_adv += line
            else:
                if time.time() - last_data_time > RECONNECT_DELAY:
                    console.print("[bold yellow]⚠️ No data received for a while. Reconnecting...[/bold yellow]")
                    return advertisements, True
        except Exception as e:
            console.print(f"[bold red]❌ Error while collecting advertisements: {e}[/bold red]")
            return advertisements, True

    if current_adv:
        parsed_adv = parse_advertisement(current_adv)
        if parsed_adv["name"] or len(advertisements) < ADVERTISEMENTS_PER_BATCH:
            advertisements.append(parsed_adv)

    if not advertisements:
        console.print("[bold yellow]⚠️ No advertisements collected[/bold yellow]")
        return advertisements, True

    console.print(f"[bold green]📊 Collected {len(advertisements)} advertisements[/bold green]")
    return advertisements, False

def send_webhook(data):
    for adv in data:
        has_device_name = bool(adv.get("name"))
        table = Table(title=f"🚨 {adv['name']} 🚨" if has_device_name else "📡 BLE Advertisement")
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        
        fields = [
            ("Device Name", adv.get("name", "N/A")),
            ("Timestamp", adv.get("timestamp", "N/A")),
            ("Frequency", adv.get("frequency", "N/A")),
            ("Address", adv.get("address", "N/A")),
            ("RSSI", adv.get("rssi", "N/A")),
            ("Data", adv.get("data", "N/A")[:1024]),
            ("Type", adv.get("type", "N/A")),
            ("Details", adv.get("details", "N/A")[:1024])
        ]
        
        for field, value in fields:
            table.add_row(field, value)
        
        console.print(table)
    
    if WEBHOOK_URL:
        for i in range(0, len(data), ADVERTISEMENTS_PER_WEBHOOK):
            batch = data[i:i+ADVERTISEMENTS_PER_WEBHOOK]
            payload = {
                "embeds": []
            }
            
            for adv in batch:
                has_device_name = bool(adv.get("name"))
                embed = {
                    "title": f"🚨 {adv['name']} 🚨" if has_device_name else "📡 BLE Advertisement",
                    "color": 5763719 if has_device_name else 3447003,
                    "fields": [
                        {"name": "Timestamp", "value": adv.get("timestamp", "N/A"), "inline": True},
                        {"name": "Frequency", "value": adv.get("frequency", "N/A"), "inline": True},
                        {"name": "Address", "value": adv.get("address", "N/A"), "inline": True},
                        {"name": "RSSI", "value": adv.get("rssi", "N/A"), "inline": True},
                        {"name": "Data", "value": adv.get("data", "N/A")[:1024], "inline": False},
                        {"name": "Type", "value": adv.get("type", "N/A"), "inline": False},
                    ]
                }
                
                if has_device_name:
                    embed["fields"].insert(0, {"name": "Device Name", "value": adv["name"], "inline": True})
                
                embed["fields"].append({"name": "Details", "value": adv["details"][:1024], "inline": False})
                
                payload["embeds"].append(embed)
            
            for attempt in range(MAX_RETRIES):
                try:
                    response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
                    response.raise_for_status()
                    console.print("[bold green]✅ Successfully sent webhook[/bold green]")
                    break
                except HTTPError as e:
                    if e.response.status_code == 429:
                        retry_after = int(e.response.headers.get('Retry-After', RATE_LIMIT_DELAY))
                        console.print(f"[bold yellow]⏳ Rate limited. Waiting for {retry_after} seconds before retry.[/bold yellow]")
                        time.sleep(retry_after)
                    else:
                        console.print(f"[bold red]❌ HTTP error occurred: {e}[/bold red]")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY)
                except RequestException as e:
                    console.print(f"[bold red]❌ Failed to send webhook (attempt {attempt + 1}/{MAX_RETRIES}): {e}[/bold red]")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
            else:
                console.print("[bold red]❌ Failed to send webhook after maximum retries[/bold red]")
            
            time.sleep(1)

def is_ubertooth_connected():
    device = usb.core.find(idVendor=UBERTOOTH_VENDOR_ID, idProduct=UBERTOOTH_PRODUCT_ID)
    return device is not None

def reset_usb_device():
    device = usb.core.find(idVendor=UBERTOOTH_VENDOR_ID, idProduct=UBERTOOTH_PRODUCT_ID)
    if device:
        try:
            device.reset()
            console.print("[bold green]USB device reset successfully[/bold green]")
            return True
        except usb.core.USBError as e:
            console.print(f"[bold red]Failed to reset USB device: {e}[/bold red]")
    return False

def restart_ubertooth_process(process):
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    
    reset_success = reset_usb_device()
    
    if not reset_success:
        console.print("[bold red]Failed to reset USB device. Waiting before retry...[/bold red]")
        time.sleep(5)
        reset_success = reset_usb_device()
    
    if not reset_success:
        console.print("[bold red]Failed to reset USB device after retry. Continuing anyway...[/bold red]")
    
    new_process = subprocess.Popen(UBERTOOTH_COMMAND, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
    console.print("[bold green]🚀 Restarted Ubertooth process[/bold green]")
    return new_process

def monitor_ubertooth_connection(process_ref):
    while True:
        if not is_ubertooth_connected():
            console.print("[bold yellow]Ubertooth device disconnected. Attempting to reconnect...[/bold yellow]")
            reset_usb_device()
            time.sleep(5)
            if is_ubertooth_connected():
                console.print("[bold green]Ubertooth device reconnected[/bold green]")
                process_ref[0] = restart_ubertooth_process(process_ref[0])
            else:
                console.print("[bold red]Failed to reconnect Ubertooth device[/bold red]")
        time.sleep(DEVICE_CHECK_INTERVAL)

def main():
    if args.debug:
        console.print("[bold blue]🐛 Debug mode enabled[/bold blue]")
    
    process_ref = [None]
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    monitor_thread = threading.Thread(target=monitor_ubertooth_connection, args=(process_ref,), daemon=True)
    monitor_thread.start()
    
    while True:
        try:
            if process_ref[0] is None or process_ref[0].poll() is not None:
                process_ref[0] = restart_ubertooth_process(process_ref[0])

            console.print("[bold cyan]📡 Collecting advertisements...[/bold cyan]")
            advertisements, need_reconnect = collect_advertisements(process_ref[0])
            
            if advertisements:
                console.print(f"[bold green]📊 Collected {len(advertisements)} advertisements[/bold green]")
                send_webhook(advertisements)
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                console.print(f"[bold yellow]⚠️ No advertisements collected. Consecutive failures: {consecutive_failures}[/bold yellow]")
            
            if need_reconnect or consecutive_failures >= max_consecutive_failures:
                console.print("[bold red]🔄 Forcing Ubertooth process restart...[/bold red]")
                process_ref[0] = restart_ubertooth_process(process_ref[0])
                consecutive_failures = 0
            
            console.print("[bold cyan]⏳ Waiting before next collection...[/bold cyan]")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            console.print(f"[bold red]🚨 Unexpected error occurred: {e}[/bold red]")
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                console.print("[bold red]🔄 Too many consecutive failures. Restarting Ubertooth process...[/bold red]")
                process_ref[0] = restart_ubertooth_process(process_ref[0])
                consecutive_failures = 0
            time.sleep(RETRY_DELAY)

if __name__ == "__main__":
    main()